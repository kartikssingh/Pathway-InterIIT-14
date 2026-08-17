#!/usr/bin/env python3
"""Drive the pipeline with synthetic traffic, without any external credentials.

Replaces four ad-hoc scripts that were scattered around the old repository
(`simulate_kafka_stream.py`, `bash.sh`, `update_csv.sh`, `update_csv_known.sh`).
All of them appended to a CSV whose four-column schema no longer matched
anything the pipeline reads, so none of them worked.

Everything here goes through the same paths the real system uses:

* ``users``        inserts customers straight into Postgres;
* ``transactions`` inserts ledger rows, which Debezium picks up and which flow
  through rps-features → rps-explain → mcp-agent;
* ``entity``       publishes a KYC applicant to the ``entities`` topic, which is
  where the OCR flow would put it — so the enrichment path can be exercised
  without AWS or Google Document AI;
* ``burst``        a deliberately structured sequence (many small transfers, then
  one large one) that trips the ``structuring_small_then_large_24h`` rule.

Usage
-----
    python tools/simulate.py users --count 20
    python tools/simulate.py transactions --user-id 1001 --count 50
    python tools/simulate.py burst --user-id 1001
    python tools/simulate.py entity --file services/pipeline/samples/entity.json

Only `psycopg2` is required; Kafka publishing shells out to the broker container.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

FIRST_NAMES = [
    "Aarav", "Diya", "Kabir", "Meera", "Rohan", "Ananya", "Vikram", "Priya",
    "Arjun", "Isha", "Nikhil", "Sneha", "Rahul", "Kavya", "Aditya", "Riya",
]
LAST_NAMES = [
    "Sharma", "Patel", "Reddy", "Iyer", "Menon", "Gupta", "Nair", "Desai",
    "Kulkarni", "Chatterjee", "Bose", "Kapoor", "Malhotra", "Joshi",
]
OCCUPATIONS = [
    "software engineer", "chartered accountant", "trader", "consultant",
    "business owner", "doctor", "teacher", "logistics manager",
]
CURRENCIES = ["INR", "USD", "EUR", "GBP"]
TXN_TYPES = ["TRANSFER", "PURCHASE", "WITHDRAWAL", "DEPOSIT", "REFUND"]
RISK_BANDS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


# --------------------------------------------------------------------------- #
# Environment
# --------------------------------------------------------------------------- #


def load_env() -> dict[str, str]:
    """Read the repository .env without depending on python-dotenv."""
    values: dict[str, str] = {}
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.split("#")[0].strip().strip('"').strip("'")
    values.update({k: v for k, v in os.environ.items() if k in values or k.startswith(("POSTGRES_", "KAFKA_"))})
    return values


def connect(env: dict[str, str]):
    try:
        import psycopg2
    except ImportError:
        sys.exit("psycopg2 is required: pip install psycopg2-binary")

    password = env.get("POSTGRES_PASSWORD")
    if not password:
        sys.exit("POSTGRES_PASSWORD is not set (check .env)")

    return psycopg2.connect(
        host=env.get("POSTGRES_HOST", "localhost"),
        port=env.get("POSTGRES_PORT", "5432"),
        dbname=env.get("POSTGRES_DBNAME") or env.get("POSTGRES_DB", "values_db"),
        user=env.get("POSTGRES_USER", "user"),
        password=password,
    )


# --------------------------------------------------------------------------- #
# Generators
# --------------------------------------------------------------------------- #


def make_user(user_id: int, rng: random.Random) -> dict[str, Any]:
    first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    band = rng.choices(RISK_BANDS, weights=[60, 25, 12, 3])[0]
    score = {"LOW": (0.0, 0.25), "MEDIUM": (0.25, 0.5), "HIGH": (0.5, 0.75), "CRITICAL": (0.75, 1.0)}[band]
    return {
        "user_id": user_id,
        "username": f"{first} {last}",
        "email": f"{first.lower()}.{last.lower()}{user_id}@example.com",
        "phone": f"9{rng.randint(100000000, 999999999)}",
        "date_of_birth": datetime.now() - timedelta(days=rng.randint(20 * 365, 60 * 365)),
        "address": f"{rng.randint(1, 400)} {rng.choice(['MG Road', 'Marine Drive', 'Park Street'])}, India",
        "occupation": rng.choice(OCCUPATIONS),
        "annual_income": round(rng.uniform(300_000, 9_000_000), 2),
        "kyc_status": rng.choice(["VERIFIED", "PENDING_VERIFICATION", "REJECTED"]),
        "credit_score": rng.randint(300, 900),
        "current_rps_not": round(rng.uniform(*score), 4),
        "current_rps_360": round(rng.uniform(0, 0.6), 4),
        "risk_category": band,
        "blacklisted": band == "CRITICAL" and rng.random() < 0.3,
    }


def make_transaction(txn_id: int, user_id: int, rng: random.Random, *, amount: float | None = None,
                     minutes_ago: int | None = None) -> dict[str, Any]:
    return {
        "transaction_id": txn_id,
        "user_id": user_id,
        "txn_timestamp": datetime.now() - timedelta(minutes=minutes_ago if minutes_ago is not None
                                                    else rng.randint(0, 60 * 24 * 30)),
        "amount": round(amount if amount is not None else rng.lognormvariate(6.5, 1.2), 2),
        "currency": rng.choices(CURRENCIES, weights=[70, 15, 10, 5])[0],
        "txn_type": rng.choice(TXN_TYPES),
        "counterparty_id": rng.randint(10_000, 99_999),
        "is_fraud": 1 if rng.random() < 0.02 else 0,
    }


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


USER_SQL = """
INSERT INTO Users (
    user_id, username, email, phone, date_of_birth, address, occupation,
    annual_income, kyc_status, credit_score, current_rps_not, current_rps_360,
    risk_category, blacklisted, last_rps_calculation
)
VALUES (%(user_id)s, %(username)s, %(email)s, %(phone)s, %(date_of_birth)s, %(address)s,
        %(occupation)s, %(annual_income)s, %(kyc_status)s, %(credit_score)s,
        %(current_rps_not)s, %(current_rps_360)s, %(risk_category)s, %(blacklisted)s, NOW())
ON CONFLICT (user_id) DO NOTHING
"""

TXN_SQL = """
INSERT INTO Transactions (
    transaction_id, user_id, txn_timestamp, amount, currency, txn_type,
    counterparty_id, is_fraud
)
VALUES (%(transaction_id)s, %(user_id)s, %(txn_timestamp)s, %(amount)s, %(currency)s,
        %(txn_type)s, %(counterparty_id)s, %(is_fraud)s)
ON CONFLICT (transaction_id) DO NOTHING
"""


def cmd_users(args: argparse.Namespace, env: dict[str, str]) -> int:
    rng = random.Random(args.seed)
    rows = [make_user(args.start_id + i, rng) for i in range(args.count)]
    with connect(env) as conn, conn.cursor() as cur:
        cur.executemany(USER_SQL, rows)
        conn.commit()
    print(f"Inserted {len(rows)} users (ids {args.start_id}..{args.start_id + args.count - 1})")
    for row in rows[:5]:
        print(f"  {row['user_id']:>7}  {row['username']:<22} {row['risk_category']}")
    if len(rows) > 5:
        print(f"  ... and {len(rows) - 5} more")
    return 0


def _next_transaction_id(cur) -> int:
    cur.execute("SELECT COALESCE(MAX(transaction_id), 100000) + 1 FROM Transactions")
    return int(cur.fetchone()[0])


def cmd_transactions(args: argparse.Namespace, env: dict[str, str]) -> int:
    rng = random.Random(args.seed)
    with connect(env) as conn, conn.cursor() as cur:
        if args.user_id:
            user_ids = [args.user_id]
        else:
            cur.execute("SELECT user_id FROM Users ORDER BY random() LIMIT 20")
            user_ids = [row[0] for row in cur.fetchall()]
        if not user_ids:
            print("No users found. Run `simulate.py users` first.", file=sys.stderr)
            return 1

        next_id = _next_transaction_id(cur)
        rows = [
            make_transaction(next_id + i, rng.choice(user_ids), rng)
            for i in range(args.count)
        ]
        cur.executemany(TXN_SQL, rows)
        conn.commit()

    total = sum(row["amount"] for row in rows)
    print(f"Inserted {len(rows)} transactions across {len(set(r['user_id'] for r in rows))} users")
    print(f"  total volume: {total:,.2f}")
    print("  Debezium should now be publishing to postgres.public.transactions")
    return 0


def cmd_burst(args: argparse.Namespace, env: dict[str, str]) -> int:
    """A structuring pattern: many small transfers, then one large one.

    Trips `structuring_small_then_large_24h` and `high_velocity_1h` in the rule
    engine, so the whole scoring → explanation → agent path lights up.
    """
    rng = random.Random(args.seed)
    with connect(env) as conn, conn.cursor() as cur:
        cur.execute("SELECT user_id FROM Users WHERE user_id = %s", (args.user_id,))
        if not cur.fetchone():
            print(f"User {args.user_id} does not exist.", file=sys.stderr)
            return 1

        next_id = _next_transaction_id(cur)
        rows = [
            make_transaction(next_id + i, args.user_id, rng,
                             amount=rng.uniform(200, 750), minutes_ago=60 - i * 5)
            for i in range(args.small_count)
        ]
        rows.append(
            make_transaction(next_id + args.small_count, args.user_id, rng,
                             amount=args.large_amount, minutes_ago=0)
        )
        cur.executemany(TXN_SQL, rows)
        conn.commit()

    print(f"Injected a structuring burst for user {args.user_id}:")
    print(f"  {args.small_count} transfers under 750, then one of {args.large_amount:,.2f}")
    print("  expect: high_velocity_1h + structuring_small_then_large_24h to fire")
    return 0


def cmd_entity(args: argparse.Namespace, env: dict[str, str]) -> int:
    """Publish a KYC applicant to the entities topic, bypassing OCR."""
    payload_path = Path(args.file)
    if not payload_path.is_file():
        print(f"{payload_path} not found", file=sys.stderr)
        return 1

    payload = json.loads(payload_path.read_text())
    if args.entity_id:
        payload["entity_id"] = str(args.entity_id)
    line = json.dumps(payload, ensure_ascii=False)

    topic = env.get("MAIN_BACKEND_TOPIC", "entities")
    container = os.environ.get("BROKER_CONTAINER", "broker")
    bootstrap = os.environ.get("KAFKA_INTERNAL_BOOTSTRAP", "broker:29092")

    command = [
        "docker", "exec", "-i", container,
        "kafka-console-producer", "--topic", topic, "--bootstrap-server", bootstrap,
    ]
    try:
        subprocess.run(command, input=line + "\n", text=True, check=True, capture_output=True)
    except FileNotFoundError:
        print("docker not found on PATH", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"kafka-console-producer failed: {exc.stderr}", file=sys.stderr)
        return 1

    print(f"Published entity {payload.get('entity_id')} ({payload.get('applicant_name')}) to '{topic}'")
    print("  the kyc-enrichment flow should pick it up within a second")
    return 0


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--seed", type=int, default=None, help="Seed for reproducible data.")
    sub = parser.add_subparsers(dest="command", required=True)

    users = sub.add_parser("users", help="Insert synthetic customers.")
    users.add_argument("--count", type=int, default=20)
    users.add_argument("--start-id", type=int, default=1001)
    users.set_defaults(func=cmd_users)

    txns = sub.add_parser("transactions", help="Insert ledger rows (drives CDC).")
    txns.add_argument("--count", type=int, default=50)
    txns.add_argument("--user-id", type=int, default=None, help="Restrict to one user.")
    txns.set_defaults(func=cmd_transactions)

    burst = sub.add_parser("burst", help="Inject a structuring pattern for one user.")
    burst.add_argument("--user-id", type=int, required=True)
    burst.add_argument("--small-count", type=int, default=8)
    burst.add_argument("--large-amount", type=float, default=9500.0)
    burst.set_defaults(func=cmd_burst)

    entity = sub.add_parser("entity", help="Publish a KYC applicant to Kafka.")
    entity.add_argument(
        "--file",
        default=str(REPO_ROOT / "services/pipeline/samples/entity.json"),
    )
    entity.add_argument("--entity-id", type=int, default=None, help="Override the id in the file.")
    entity.set_defaults(func=cmd_entity)

    args = parser.parse_args(argv)
    return int(args.func(args, load_env()) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
