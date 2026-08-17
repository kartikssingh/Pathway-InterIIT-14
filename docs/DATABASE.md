# Database

PostgreSQL 16 is the system of record. Both the pipeline and the API read and
write it; they do not talk to each other.

The schema lives in `infra/postgres/migrations/` as numbered, idempotent SQL
files applied in filename order. `make up` applies them; re-running is safe.

> The schema was previously defined in three incompatible places: a 700-line
> `docker-init.sh` of inline `psql -c` heredocs, a directory of numbered `.sql`
> files that had drifted from it, and `Base.metadata.create_all()` on API
> start-up, which produced a *fourth* variant without CHECK constraints or
> triggers. There is now one source of truth.

---

## Tables

### `Users` — the customer record

| Column | Type | Notes |
| --- | --- | --- |
| `user_id` | BIGINT PK | Derived from the KYC identity fields, so re-processing a form updates rather than duplicates |
| `uin`, `uin_hash` | CHAR | Identification number and its SHA-256 |
| `username`, `email`, `phone`, `date_of_birth`, `address` | | |
| `occupation`, `annual_income` | | |
| `kyc_status`, `kyc_verified_at`, `signature_hash` | | |
| `credit_score` | INT | 300–900, enforced |
| `current_rps_not` | FLOAT | Standing identity risk, 0–1, enforced |
| `current_rps_360` | FLOAT | Latest behavioural risk, 0–1, enforced |
| `last_rps_calculation` | TIMESTAMP | Drives the watchdog's least-recently-checked ordering |
| `risk_category` | VARCHAR | LOW / MEDIUM / HIGH / CRITICAL |
| `blacklisted`, `blacklisted_at` | | |
| `version`, `time`, `diff` | | Pathway connector bookkeeping |

### `Transactions` — the ledger

Debezium streams this table's write-ahead log. `txn_timestamp` is the event
time; the index on `(user_id, txn_timestamp DESC)` is what makes the feature
query fast.

> The original index was declared on a column named `timestamp`, which does not
> exist — so the statement failed and every feature lookup was a sequential scan.

### `ToxicityHistory` — the score audit trail

Append-only. Every score change writes a row with its `calculation_trigger`
(`register`, `transaction_monitoring`, `watchdog_rescreen`, ...). This is what
answers "why did this customer's risk change on the 14th?".

### `UserSanctionMatches` — screening outcomes

One row per screening that actually ran. The trigger used to write a row for
every applicant regardless, which made "how many customers have been screened?"
unanswerable.

### `Staging_Buffer` — the pipeline's landing table

The `db-sink` flow writes one flat row per enriched applicant. An
`AFTER INSERT` trigger (`distribute_staging_data`) fans it out to `Users`,
`ToxicityHistory` and `UserSanctionMatches` inside a single transaction. Rows
here are transient — `SELECT cleanup_staging_buffer(24)` clears them.

### `compliance_alerts` — the review queue

Written by the `mcp-agent` flow and by admins. `is_true_positive` /
`reviewed_at` / `reviewed_by` capture the review outcome and feed the alert
hit-rate metric.

CHECK constraints restrict `alert_type`, `severity`, `status` and `priority`.
The pipeline emits `LOW`/`MEDIUM`/`HIGH`; those are lower-cased before insert —
they previously went in as-is and every insert was rejected.

### Administration and monitoring

`admins`, `audit_logs`, `system_metrics`, `system_health`, `system_alerts`.
`audit_logs.action_metadata` is JSONB with a GIN index, so before/after states
are queryable.

---

## Views

| View | Purpose |
| --- | --- |
| `v_audit_logs_with_admin` | Audit log joined with the acting administrator |
| `v_active_system_issues` | Unresolved health checks and active system alerts, unified |
| `v_metrics_last_24h` | Rolling metric summary |
| `v_user_risk_overview` | Per-user snapshot: open alerts, 30-day volume, latest sanction match |

## Functions

| Function | Purpose |
| --- | --- |
| `calculate_alert_hit_rate(from, to)` | Percentage of reviewed alerts that were genuine |
| `get_system_health_status()` | `healthy` / `degraded` / `critical` |
| `archive_old_audit_logs(days)` | Retention, default 365 days |
| `cleanup_old_health_checks(days)` | Retention, default 30 days |
| `cleanup_staging_buffer(hours)` | Clears the landing table |

---

## Change data capture

Debezium (`pgoutput`) streams `public.transactions` and `public.toxicityhistory`
into Kafka with the `postgres.` prefix.

> Postgres folds unquoted identifiers to lower case. The original connector
> listed `public.ToxicityHistory,public.Transactions`, which matched no table, so
> change capture never started — the transaction path could not have been
> receiving events.

Both tables carry an explicit `REPLICA IDENTITY DEFAULT`, stated in the migration
so a future schema change cannot silently break capture.

---

## Making a schema change

1. Add a new numbered file in `infra/postgres/migrations/`. Never edit an applied
   one.
2. Make it idempotent (`IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`,
   `CREATE OR REPLACE`).
3. Update the matching SQLAlchemy model in `services/api/app/models/`.
4. Update the Pathway schema in `services/pipeline/fraudguard/schemas.py` if the
   stream writes the column.
5. `make up` to apply, then `make doctor` to confirm the expected tables exist.

---

## Seed data

`infra/postgres/seed/` holds optional demo fixtures. `make up` does **not** apply
them; `make seed` applies the demo users and transactions. They are development
fixtures — never run them against real data.

Useful ad-hoc queries live in `docs/USEFUL_QUERIES.sql`.
