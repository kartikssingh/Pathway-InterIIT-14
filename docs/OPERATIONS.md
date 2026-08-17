# Operations

Running, observing and troubleshooting the stack.

---

## Start-up order

Nothing hard-fails on a missing dependency, but this order gets everything
connected on the first attempt.

```bash
make up                              # Kafka, Postgres, Debezium, Redis + schema + topics
make doctor                          # confirm the environment before starting anything

# 1. models
make scorer                          # :9000

# 2. the KYC path
cd services/pipeline
python -m fraudguard kyc-enrichment
python -m fraudguard db-sink
python -m fraudguard kyc-ocr         # only with AWS + Document AI credentials

# 3. the transaction path
python -m fraudguard rps-features
python -m fraudguard rps-explain
python -m fraudguard mcp-server      # needs PW_LICENSE
python -m fraudguard mcp-agent       # needs GEMINI_API_KEY

# 4. re-screening
python -m fraudguard rag-server
python -m fraudguard scheduler

# 5. the console
make api                             # :8001
make web                             # :3000
```

Each flow is an independent process. Stopping one stops that stage; the others
keep running and the topic buffers the backlog.

---

## Health

| Check | Command |
| --- | --- |
| Environment | `make doctor` |
| API liveness | `curl localhost:8001/health/live` |
| API readiness | `curl localhost:8001/health/ready` |
| Scorer | `curl localhost:9000/healthz` |
| Model provenance | `curl localhost:9000/model` |
| Kafka topics | `make topics` |
| Debezium | `curl localhost:8083/connectors/fraudguard-postgres/status` |
| Container health | `docker compose -f infra/docker-compose.yml ps` |

`make doctor` is the first thing to run when something will not start. It reports
configuration, credentials, model artefacts, Kafka and Postgres connectivity,
schema completeness and which optional integrations are installed — and exits
non-zero only on a real failure.

---

## Logs

Every service logs in the same structured format. Set `LOG_JSON=true` for
newline-delimited JSON suitable for a log shipper.

```bash
LOG_JSON=true python -m fraudguard kyc-enrichment | jq 'select(.level=="WARNING")'
```

Pipeline logs also go to `services/pipeline/logs/<flow>.log` (rotated, 16 MB × 5).

Every log line inside a flow carries the bound context — `entity_id`, `user_id`,
`subject`, `operation` — so a single customer can be traced across stages:

```bash
jq 'select(.entity_id=="204871336112")' services/pipeline/logs/*.log
```

The API stamps every response with `X-Request-ID` and puts the same id on every
log line for that request. Send your own to correlate across services:

```bash
curl -H 'X-Request-ID: investigate-42' localhost:8001/users/42
```

---

## The audit trail

`services/pipeline/out/` is append-only and per-stage:

| File | Contents |
| --- | --- |
| `raw_ingest.jsonl` | Applicants exactly as received |
| `opensanctions_results.jsonl` | Every screening, including failures |
| `web_analysis_debug.jsonl` | Every article considered, with its reputation signals |
| `llm_debug.jsonl` | The raw completion, the deterministic reference and their divergence |
| `reports.jsonl` | The final enriched report |
| `latest.jsonl` | Latest snapshot per entity |
| `rps_features.jsonl` | Feature vectors as scored |
| `rps_output.jsonl` | Scores and explanations |
| `agent_validations.jsonl` | Agent tool decisions and verdicts |
| `watchdog_report.jsonl` | Per-entity re-screening deltas |
| `rescreen_audit.jsonl` | Score changes the watchdog applied |

Database-side, `ToxicityHistory` records every score change and `audit_logs`
records every admin action.

---

## Troubleshooting

**A flow exits immediately with a configuration error.**
Run `make doctor`. It lists every missing key at once rather than failing on the
first.

**`kyc-enrichment` runs but nothing reaches the database.**
Check `db-sink` is running and that `db_updates` has messages:

```bash
docker exec broker kafka-console-consumer \
  --topic db_updates --bootstrap-server broker:29092 --from-beginning --max-messages 1
```

**No transactions flow after an insert.**
Debezium is probably not capturing. Check the connector status; a `FAILED` task
usually means the replication slot was dropped:

```bash
curl -s localhost:8083/connectors/fraudguard-postgres/status | jq
docker exec db_tuto_postgres psql -U user -d values_db \
  -c "SELECT slot_name, active FROM pg_replication_slots;"
```

**Scores are all zero.**
`/healthz` on the scorer will say whether the model artefacts loaded. If the
feature vector is all zeros, `rps-features` could not reach Postgres — the flow
logs `Feature query failed` in that case.

**The LLM verdict disagrees badly with the deterministic score.**
That is what `score_audit` is for. Anything outside ±0.15 is logged as a warning:

```bash
jq 'select(.score_audit.within_tolerance == false)' services/pipeline/out/llm_debug.jsonl
```

**Adverse-media search returns nothing.**
Google quotas. The key pool cools an exhausted key for 15 minutes and rotates;
with only one pair configured, everything waits. Add more numbered pairs.

**The console shows "server unavailable" but the API responds.**
It probes `/health/live`, which fails when the API cannot reach the database.
`curl localhost:8001/health/ready` will say which check failed.

**A flow will not resume after a crash.**
Pathway persistence lives in `services/pipeline/state/<flow>/`. Deleting that
directory forces a replay from the topic's start.

---

## Routine maintenance

```sql
-- Retention (see infra/postgres/migrations/005_views_and_functions.sql)
SELECT archive_old_audit_logs(365);
SELECT cleanup_old_health_checks(30);
SELECT cleanup_staging_buffer(24);
```

The watchdog prunes its own state snapshots after each sweep (30 days, always
keeping the newest five per entity).

---

## Auditing endpoint authentication

Which routes are protected, and by what:

```bash
cd services/api && python3 - <<'EOF'
import re, pathlib
levels = {}
for f in sorted(pathlib.Path("app/routes").glob("*.py")):
    for part in re.split(r'\n(?=@(?:router|users_router)\.)', f.read_text())[1:]:
        m = re.match(r'@(?:router|users_router)\.(\w+)\("([^"]*)"', part)
        if not m:
            continue
        body = part.split("\n\n")[0]
        level = ("superadmin" if "require_superadmin" in body else
                 "admin"      if "require_admin" in body else
                 "token"      if "get_current" in body else "NONE")
        levels.setdefault(level, []).append(f"{m.group(1).upper():6} {f.stem}:{m.group(2)}")
for level in ("NONE", "token", "admin", "superadmin"):
    print(f"\n== {level} ({len(levels.get(level, []))}) ==")
    for row in levels.get(level, []):
        print("  ", row)
EOF
```

As of this writing that reports **38 unauthenticated operations**, five of which
are public by design (`/api/auth/login`, the three health probes, `/version`).
The remaining 33 — including both bulk export endpoints and every transaction
mutation — are a known gap, tracked as P0.4 in [ROADMAP.md](ROADMAP.md) and
described in the [README](../README.md#endpoints).

Re-run this after touching any route file; a new endpoint that lands in the
`NONE` bucket by accident is exactly the failure this catches.

---

## Security checklist before exposing anything

- [ ] `SECRET_KEY` set to a real random value (`openssl rand -hex 32`). The API
      refuses to start in production with the old committed placeholder.
- [ ] Default `admin` / `superadmin` passwords changed.
- [ ] `APP_ENV=production` — this enables strict configuration validation.
- [ ] `CORS_ORIGINS` set to the console's actual origin, not `*`.
- [ ] `TRUST_PROXY_HEADERS=true` **only** behind a proxy you control; otherwise
      any caller can forge the IP address recorded in the audit log.
- [ ] `.env` not committed; `git log --all -- .env` returns nothing.
- [ ] Postgres not exposed publicly; the Debezium REST port (8083) firewalled.
- [ ] `LOG_JSON=true` and logs shipped somewhere durable.
- [ ] **Endpoint authentication closed** — see the audit above. Until then the
      API must not be reachable from an untrusted network, because bulk customer
      exports and ledger writes are open.
