# FraudGuard Compliance API

The REST layer between the operator console and the compliance database. It
serves users, transactions, alerts, dashboards, exports and the superadmin
monitoring views; the streaming pipeline writes to the same database directly.

```
services/api/
├── app/
│   ├── main.py         application factory, lifespan, router registration
│   ├── db.py           lazy engine, session factory, request-scoped session
│   ├── core/           settings, logging, security, errors, middleware, cache, pagination
│   ├── models/         SQLAlchemy tables
│   ├── schemas/        Pydantic request/response models
│   ├── routes/         HTTP endpoints
│   └── services/       business logic
├── scripts/            seeding, migrations, inspection
├── tests/              unit / integration / load
└── docs/               endpoint references
```

---

## Quick start

```bash
cd services/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

cp ../../.env.example .env        # fill in DATABASE_URL and SECRET_KEY
python -m uvicorn app.main:app --reload --port 8001
```

Then:

* Swagger UI — <http://localhost:8001/docs>
* ReDoc — <http://localhost:8001/redoc>
* Health — <http://localhost:8001/health>

The database schema is **not** created by the API. It is owned by
`infra/postgres`; run `bash infra/bootstrap.sh` once. (`AUTO_CREATE_TABLES=true`
will build an approximate schema from the ORM for throwaway local databases —
it omits the CHECK constraints and the `Staging_Buffer` trigger the pipeline
depends on, so never use it against anything real.)

---

## Configuration

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | assembled from `POSTGRES_*` | Required (directly or via the parts). |
| `SECRET_KEY` | generated in dev | **Required in production.** `openssl rand -hex 32`. |
| `APP_ENV` | `development` | `production` turns on strict validation. |
| `CORS_ORIGINS` | `http://localhost:3000` | JSON array or comma-separated. `*` is refused in production. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | |
| `BCRYPT_ROUNDS` | `12` | |
| `RATE_LIMIT_PER_MINUTE` | `300` | Per client, per worker. `0` disables. |
| `DEFAULT_PAGE_SIZE` / `MAX_PAGE_SIZE` | `50` / `500` | |
| `REDIS_ENABLED` | `false` | Optional dashboard cache. |
| `AWS_S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | — | KYC form uploads. |
| `TRUST_PROXY_HEADERS` | `false` | Only enable behind a proxy you control. |
| `LOG_JSON` | `true` in production | Newline-delimited JSON logs. |

Starting with an unsafe configuration fails loudly at boot rather than silently
running with a publicly-known signing key.

---

## API conventions

**Errors.** Every failure — validation, business rule, database, unhandled —
returns the same envelope:

```json
{
  "error": { "code": "not_found", "message": "User 42 was not found", "details": {} },
  "request_id": "9f2c1ab4e7d0"
}
```

**Correlation.** Every response carries `X-Request-ID` and `X-Response-Time-ms`.
Send your own `X-Request-ID` and it is echoed back and stamped on every log line
for that request.

**Pagination.** List endpoints accept `offset` and `limit` (`skip` is a
deprecated alias) and return:

```json
{ "items": [...], "total": 1043, "offset": 0, "limit": 50, "has_more": true }
```

**Auth.** `POST /api/auth/login` (OAuth2 password form) returns a bearer token;
send it as `Authorization: Bearer <token>`. Tokens carry `typ`, so a refresh
token cannot be replayed as an access token.

---

## Endpoints

| Group | Prefix | Auth |
| --- | --- | --- |
| Health | `/health`, `/health/live`, `/health/ready`, `/version` | none |
| Auth | `/api/auth` | login is open, the rest need a token |
| Users | `/user`, `/users` | writes need `admin` |
| Transactions | `/transactions` | |
| Compliance alerts | `/compliance` | writes need `admin` |
| Dashboard | `/dashboard` | |
| Export | `/export` | `admin` |
| Superadmin | `/superadmin` | `superadmin` |

`docs/FRONTEND_API_REFERENCE.md` has the full request/response reference.

---

## Scripts

```bash
python scripts/seed_database.py       # demo users, transactions and alerts
python scripts/populate_all_tables.py # a larger dataset for the dashboards
python scripts/show_all_data.py       # dump what is currently in the database
```

---

## Testing

```bash
pytest tests/unit                 # no database needed
pytest tests/integration          # needs a live database and a running API
locust -f tests/load/locustfile.py
ruff check app
```

---

## What changed in the refactor

* **Configuration** — one validated settings object. The service can no longer
  start with the committed placeholder `SECRET_KEY`, and a missing
  `DATABASE_URL` is a readable message instead of an import-time `KeyError`.
* **Errors** — one response shape everywhere, with database, validation and
  unhandled exceptions all mapped. The frontend previously carried three
  different error parsers to cope.
* **Observability** — request ids, structured logs, access logging, timing
  headers, and real `/health/live` + `/health/ready` probes. The console's
  health check was previously probing `/` and reporting green while the database
  was down.
* **Security** — timing-safe login (an unknown username no longer answers
  faster than a wrong password), timezone-aware token expiry, typed tokens,
  security headers, per-client rate limiting, `X-Forwarded-For` only trusted
  behind a proxy, and a CORS policy that browsers actually accept
  (`allow_origins=["*"]` with credentials never worked).
* **Lifecycle** — lazy engine creation, so importing a model no longer opens a
  socket; `create_all()` off by default; sessions rolled back on error rather
  than leaking a failed transaction to the next request.
* **Bugs fixed** — `GET /compliance/alerts/top` was shadowed by
  `/compliance/alerts/{alert_id}` and returned 422; the S3 client was built at
  import from unset variables; a Redis client was constructed from `None` host
  and port and never used; a failed audit write rolled back the action it was
  recording.
* **Removed** — the `legacy/` tree, `.backup` files, `nohup.out` and five
  one-off scripts at the repository root. SQL moved to `infra/postgres`, which
  is now the single source of truth for the schema.
