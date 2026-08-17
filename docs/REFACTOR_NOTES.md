# Refactor notes

What changed, and why. The trained model, its training code and its artefacts
were deliberately left untouched — see [The ML model](#the-ml-model) below.

---

## Repository layout

**Before** — three zip archives that had to be unpacked side by side, two of
which contained near-duplicate copies of the same pipeline that had drifted
apart, plus a Next.js app nested two directories deep.

```
Pathway_InterIIT14.0_AgenticAI-main-new.zip   pipeline (older copy) + FastAPI backend
Pathway_InterIIT14.0_AgenticAI-mcp-kafka-psql.zip   pipeline (newer copy) + OCR + models
frontend.zip                                  frontend/frontend/...
```

Every one of `main.py`, `database_update.py`, `watchdog.py`, `scheduler.py`,
`utils.py`, `llm_output.py`, `open_sanctions.py`, `sus.py`,
`adverse_media_finder.py`, `scraping_test_new.py`, `mcp_server.py` and
`mcp_client.py` existed twice, with different contents.

**After** — one repository, three services, one place for infrastructure.

```
Pathway-InterIIT-14/
├── services/pipeline/    Pathway flows + the RPS model
├── services/api/         FastAPI
├── services/web/         Next.js console
├── infra/                compose, versioned schema, Kafka topics, Debezium
├── tools/                traffic simulator
├── docs/                 architecture, operations, database, roadmap
└── assets/               diagram, report, videos
```

---

## The pipeline

### Structure

Nine loose scripts, each launched with its own `python3 path/to/file.py`
incantation that only worked from one specific working directory, became one
package with one entry point:

```bash
python -m fraudguard --list
python -m fraudguard kyc-enrichment
python -m fraudguard doctor
```

| Layer | Modules |
| --- | --- |
| Foundation | `config`, `logging`, `errors` |
| I/O | `io/http`, `io/postgres`, `io/jsonl`, `io/state` |
| LLM | `llm/client`, `llm/guard`, `llm/prompts` |
| Enrichment | `enrichment/opensanctions`, `ofac`, `search`, `articles`, `reputation`, `web_analysis` |
| Domain | `scoring`, `features`, `similarity`, `risk_updates`, `schemas`, `udfs` |
| Model | `rps/registry`, `rps/engine`, `rps/service` |
| Flows | `flows/*`, `scheduler/*` |

Four rules the whole package now follows:

1. **Nothing happens at import time.** No `pw.run()`, no API clients, no database
   connections, no `os.environ[...]`. Importing any module is free. Previously
   `import database_update` started a streaming job, and `import mcp_server`
   raised `KeyError: 'PW_LICENSE'`.
2. **Every UDF wraps a pure function**, so the logic is testable without a
   Pathway runtime.
3. **Optional dependencies degrade rather than crash.** Guardrails, OTX,
   scikit-learn, DeepFace and the article extractors are all optional.
4. **The deterministic score is always computed**, so a decision is always
   explainable.

### Configuration

`os.environ["OS_API_KEY"]` at module scope in five files meant one missing key
crashed an unrelated flow with a bare `KeyError`. There is now one validated
settings object (`fraudguard/config.py`) that reports every missing key for the
flow you are actually running, and `python -m fraudguard doctor` to check an
environment before starting anything.

### Consumer groups

Every flow used `group.id = "0"`. Two flows reading the same topic therefore
joined the same consumer group and split its partitions between them — each
seeing roughly half the messages. Each flow now gets its own group.

---

## Bugs found and fixed

These are defects in behaviour, not style.

### Scoring

| | |
| --- | --- |
| **`logit()` divided by the wrong term** | `rps_engine.py` computed `log(x / (1 - eps))` instead of `log(x / (1 - x))`, so both fusion inputs were wrong for every request. Fixed; `RPS_LEGACY_LOGIT=true` reproduces the old values for comparison with historical scores. |
| **Two incompatible score scales** | The LLM path produced a `risk_score` in [0, 1]; the fallback produced a 0–100 integer. Whenever the fallback fired, the score was 100× too large — and it was written straight to `Users.current_rps_not`. |
| **The fallback was dead code** | `fallback_json` was computed for every row and never read (`# THIS IS NEVER USED`). An LLM outage produced an unparseable row that crashed the parse instead. |
| **`extract_json_and_summary` crashed on a malformed completion** | `jsonfile['summary'] = summary` on a `None` raised `TypeError` when the model omitted the fence, killing the flow. |

### Feature engineering

| | |
| --- | --- |
| **Windows were not partitioned by user** | `groupby(trx.user_id)` was assigned to an unused variable and `windowby` was given no `instance`, so every aggregate mixed all users in the window together. |
| **`unique_cp_*` was not a count** | `pw.reducers.any(counterparty_id)` returns *one arbitrary counterparty id*. That string was coerced to an integer and fed to the model as a feature. The four window tables were then joined on it. |
| **Eight features were always zero** | `feat_json` was built from only the 16 float columns, so every `txn_count_*` and `unique_cp_*` the model expects was imputed as 0. |

Features are now computed with one parameterised SQL statement per affected
user — correct distinct counts, correct partitioning, and matching how the
training snapshots were generated.

### Adverse media

| | |
| --- | --- |
| **Name matching was regex injection** | The subject's name went straight into `re.search`. Any name containing `.`, `(`, `+` or `?` either over-matched or raised `re.error` and silently dropped all of that person's evidence. |
| **Evidence leaked between entities** | The scraper appended to one shared `scraped_web_articles.jsonl` and the reader read the whole file — so every entity was scored against every other entity's articles. |
| **The scrape ran twice per entity** | `make_llm_prompt(...)` was called once for the system prompt and once for the user prompt. Each call re-ran the search, the fetch, the OTX lookups and the per-article LLM rating. |
| **Positional result indexing** | `output[1]['authenticity_score'].values()[0]` broke on any Pathway version returning a different tuple shape. Replaced with a structural search. |
| **The search retry loop was unbounded** | A persistent 5xx from Google retried every 5 seconds forever. One quota error also permanently disqualified a key for all remaining keywords. Now bounded, with round-robin rotation and cooldown. |
| **Search keys were mismatched** | The image search used `GOOGLE_CLOUD_API_KEY_2` with `PROGRAMMABLE_SEARCH_ENGINE_ID_1`. |
| **A numbering gap truncated the key pool** | The loop stopped at the first missing index, so a hole at 2 hid keys 3 and beyond. |

### Data flow

| | |
| --- | --- |
| **Debezium captured nothing** | `table.include.list` was `public.ToxicityHistory,public.Transactions`. Postgres folds unquoted identifiers to lower case, so neither name matched a real table. |
| **Every alert insert was rejected** | The pipeline wrote `severity: "MEDIUM"` into a column with `CHECK (severity IN ('low','medium','high','critical'))`. |
| **`risk_category` was stored with quotes** | `pw.apply(str, json_value)` renders the JSON representation, so the column contained `"HIGH"` including the quote characters. |
| **The alert `entity_id` was unrelated to the entity** | `make_uuid(user_id)` ignored its argument and returned `uuid4()`. Now a deterministic UUID5 of the user and the score. |
| **The KYC `entity_id` was `random.randint(1, 1000)`** | Two applicants collided about every 25 forms, and reprocessing the same form created a new record. Now a hash of the identity fields. |
| **`try`/`except` around graph construction** | `mcp_client.py` wrapped `table.with_columns(agent_udf(...))` in a try/except to provide a fallback. That only declares the graph — the fallback could never run, and a UDF failure at run time killed the flow. The same pattern wrapped `pw.io.postgres.write` in `database_update.py`. |
| **A `pics[0]` with no bounds check** | A KYC form with no detectable face raised `IndexError` and killed the OCR flow. |
| **The Document AI cache was write-only** | Fields were cached on every run and the read was commented out, so every reprocessing paid for Document AI again. |

### Watchdog and scheduler

| | |
| --- | --- |
| **Runs were compared by row position** | Four independently parsed lists of JSONL fields were `zip`ped together. Any run returning a different number of rows silently compared entity *n* against a different entity. Comparison is now keyed per entity. |
| **The interval never adjusted on an empty sweep** | `T` was only updated inside the per-entity loop. |
| **Dead configuration** | `CHECK_INTERVAL_SECONDS = 10` sat next to the `T = 10 * 60` it was meant to configure. |
| **A subprocess with a 10-minute kill** | The watchdog is now importable and called in-process. |
| **`EntitiesSchema` had drifted between copies** | The watchdog's copy was missing `profile_pic`, so it could not deserialise messages the OCR flow produced. |

### Resource handling

| | |
| --- | --- |
| **One global cursor shared across UDFs** | Four modules opened a single psycopg2 connection and cursor at import and used them from inside Pathway UDFs, which run on a worker pool. Cursors are not thread-safe, and one network hiccup poisoned the connection for the process's lifetime. Replaced with a pooled, context-managed accessor. |
| **A new TLS session per lookup** | `requests.Session()` was constructed inside the per-call function. Now one pooled, retrying session. |
| **No retry policy anywhere** | A single blip from OpenSanctions produced a permanently null enrichment, indistinguishable from "clean". |
| **`sys.exit(1)` inside a library constructor** | `gis_demo.py` killed the interpreter — and with it the Pathway worker — when credentials were missing. |
| **A hard-coded Pathway licence key** | `debezium_stream.py` contained a real licence key in source. That file is gone; the key comes from `PW_LICENSE`. **If that key was ever pushed, rotate it.** |

### API

| | |
| --- | --- |
| **`GET /compliance/alerts/top` always returned 422** | It was declared *after* `/alerts/{alert_id: int}`; FastAPI matches in declaration order, so `top` was parsed as an integer id. |
| **A publicly-known signing key as the default** | `SECRET_KEY` fell back to `"your-secret-key-change-this-in-production-..."`, committed in the repository. The API now refuses to start in production with any known placeholder. |
| **A username oracle** | `authenticate_admin` returned early for an unknown username, so it answered measurably faster than a wrong password. Both paths now perform a hash comparison. |
| **CORS that no browser accepts** | `allow_origins=["*"]` together with `allow_credentials=True` is rejected outright. |
| **A Redis client built from `None`** | `redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), db=os.getenv("REDIS_DB"))` ran at import with all three unset, and nothing used the result. |
| **The S3 client was built at import** | Importing a route module required boto3 and AWS credentials. |
| **A failed audit write rolled back the action** | `create_audit_log` committed with no error handling inside the same session as the action it was recording. |
| **Sessions leaked failed transactions** | `get_db` closed but never rolled back, so the next request on that connection failed with `InFailedSqlTransaction`. |
| **`create_all()` on every boot** | Produced a schema without CHECK constraints or the `Staging_Buffer` trigger — a silently different database from the one the pipeline writes to. Now opt-in via `AUTO_CREATE_TABLES`. |
| **`X-Forwarded-For` trusted unconditionally** | Any client could forge the IP address written into the audit log. Now gated behind `TRUST_PROXY_HEADERS`. |
| **Naive `datetime.utcnow()` for token expiry** | Compared against a timezone-aware clock; also deprecated in Python 3.12. |

### SQL

| | |
| --- | --- |
| **An index on a non-existent column** | `CREATE INDEX ... ON Transactions (user_id, timestamp DESC)` — the column is `txn_timestamp`. The statement failed and every transaction lookup was a sequential scan. |
| **A function that could not be created** | `calculate_alert_hit_rate` referenced `is_true_positive`, added only by a later ad-hoc migration. Running the setup script end to end never created the function. |
| **A seed that could never insert** | The admin seed set `is_active` (no such column) and `role = 'SUPERADMIN'` (the CHECK requires lower case). Both statements failed, leaving no way to log in. |
| **`DROP TABLE` on every run** | The setup script dropped and recreated every table, so re-running it destroyed all data. Migrations are now idempotent. |

### Console

| | |
| --- | --- |
| **Customer PII logged to the browser console** | `apiRequest` ran `console.log("[API] Success for", endpoint, data)` on every response, in production. |
| **The health check was meaningless** | It probed `/` and accepted 404 and 405 as healthy, so any process listening on the port counted as a working backend — including one whose database was down. |
| **The health hook restarted its own interval every render** | Its config object was rebuilt on each render, so the effect's dependency changed every time. The abort timer also leaked when `fetch` rejected. |
| **A transient error blanked populated tables** | `useApiState` reset `data` to `null` on failure. |
| **State set after unmount** | No mounted guard, and no request cancellation. |
| **`"undefined"` sent as a query value** | Several copies of the duplicated query-building block were missing the `value !== undefined` guard. |
| **Three different error parsers** | Because the API returned three different error shapes. Both ends now use one envelope. |
| **An expired token produced a dead page** | Nothing reacted to a 401; every panel just failed. The client now clears the session and redirects. |
| **The tab still said "Create Next App"** | Generated metadata was never replaced. |
| **Port mismatch** | `lib/api.ts` defaulted to `:8000`, `useHealthCheck` to `:8000`, `ApiDiagnostics` to `:8000`, while the API README documents `:8001`. Now one constant. |

---

## New capabilities

Things the system could not do before.

| | |
| --- | --- |
| **`python -m fraudguard doctor`** | Diagnoses configuration, credentials, model artefacts, Kafka, Postgres, schema completeness and optional integrations in one command. Previously the only way to validate an environment was to start all nine processes and see which died. |
| **Model registry** | Every artefact is hashed at start-up. `GET /model` reports the digests; every score carries the model version. This is the reproducibility half of roadmap item P0.2, without needing DVC or object storage. |
| **Deterministic scoring** | `fraudguard/scoring.py` implements the exact algorithm the prompt asks the LLM to follow. It is the fallback, the audit reference, and the drift detector (`score_audit`). |
| **Explainable scores** | `POST /score?explain=true` returns which rules fired, which features were imputed, and the model version. |
| **Structured logging with bound context** | JSON logs with `entity_id` / `user_id` / `operation` on every line, so one customer can be traced across every stage. |
| **Durable state store** | Versioned, compressed, per-entity snapshots with retention — replacing `shutil.copytree` between three directories. Roadmap item P1.2. |
| **API health probes** | `/health/live` and `/health/ready`, with the readiness probe reporting *which* dependency failed. |
| **Request correlation** | `X-Request-ID` on every response, echoed from the caller, stamped on every log line. |
| **Rate limiting, security headers, gzip** | On the API. |
| **Batch scoring** | `POST /score/batch` for up to 500 vectors. |
| **Traffic simulator** | `tools/simulate.py`, including a `burst` mode that deliberately trips the structuring rule, so the whole detection path can be exercised end to end without credentials. |
| **Test suites** | 116 unit tests (99 in the pipeline, 17 in the API) covering the scoring contract, similarity, configuration parsing, the JSONL and state stores, search key rotation, pagination, rate limiting and the error envelope. There were no unit tests for any of this. |
| **One-command bootstrap** | `make up` replaces a 700-line shell script of inline `psql` heredocs. |

---

## Deleted

| | Why |
| --- | --- |
| `backend/legacy/` (9 modules) | Every route was commented out of `main.py`. |
| `*.backup` files (3 in the console, 2 in the API) | Duplicates kept next to the modules they duplicated. |
| `simulate_kafka_stream.py`, `bash.sh`, `update_csv.sh`, `update_csv_known.sh`, `stream_works.py` | All wrote a four-column CSV that no longer matched anything the pipeline reads. Replaced by `tools/simulate.py`. |
| `debezium_stream.py` | A hello-world demo containing a hard-coded licence key. |
| `test_password.py`, `generate_correct_hashes.py`, `generate_password_hash.py`, `verify_quick.py`, `fix_rps_scores.py` | One-off scripts at the repository root. |
| `nohup.out`, `AUTH_FILES_TREE.txt`, `debug.txt`, `catboost_info/`, `RPSState/` | Committed run artefacts. |
| The older duplicate pipeline | Superseded by the newer copy in every file. |
| `requirements.txt` (400 pinned lines) | A `pip freeze` of a developer machine including CUDA wheels, Jupyter and three OCR engines. Kept as `requirements-lock.txt`; the new file lists what the code imports. |

---

## The ML model

`services/pipeline/ml/` is unchanged, as requested:

* `models/` — the four `.pkl` artefacts, `lr_dict.json`, `training_features.json`,
  `p_ml_thresholds.json`, and `train_supervised.py`, `train_supervised_ensembled.py`,
  `train_anomaly.py`;
* `rules/`, `features/`, `fusion/`, `preprocessing/` — the rule engine, evidence
  computation, prior, feature generation and dataset loading;
* `data/processed/` — the parquet files inference reads;
* `datasets/` — the raw training data;
* `train_pipeline.sh` — the retraining script.

Not one line of that code was edited, and no artefact was regenerated. The
serving layer adapts to it: `fraudguard/rps/engine.py` puts `ml/` on `sys.path`
and imports `rules.rule_engine`, `rules.evidence` and `rules.compute_prior`
exactly as `train_pipeline.sh` does, so training and serving cannot diverge.

The only change in model *behaviour* is the `logit()` fix described above, which
is in the serving code, not the model, and is reversible with
`RPS_LEGACY_LOGIT=true`.

---

## Not done

Stated plainly rather than left implied.

* **Nothing was executed.** No dependency was installed, no container started, no
  flow run, no migration applied. The unit tests that run without third-party
  packages were run and pass (116 of them); everything else is verified by
  reading, by `compileall`, by `bash -n`, and by static cross-checks that every
  import across the console resolves to something that exists.
* **The roadmap's infrastructure items** (Vault, DVC, the ELK stack, Alembic)
  are not implemented — each needs external services. `docs/ROADMAP.md` keeps
  them, and the dependency-free parts of P0.2, P0.3 and P1.2 are now in place:
  model provenance, structured JSON logging, and the durable state store.
* **The console's page components** were not rewritten. Their imports, data flow
  and formatting helpers were repointed, but the layout and markup of the
  dashboard, users, transactions and superadmin pages are as they were.
* **No integration or end-to-end tests were added.** The unit suites cover pure
  logic; anything needing Kafka or Postgres is marked and skipped.
