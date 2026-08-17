# FraudGuard Pipeline

The streaming half of the system: KYC intake, sanctions and adverse-media
screening, transaction risk scoring, agentic validation and continuous
re-screening — built on [Pathway](https://pathway.com).

```
services/pipeline/
├── fraudguard/            the package (see "Layout" below)
├── ml/                    trained models + training code — UNTOUCHED by the refactor
├── samples/               example payloads for manual testing
├── tests/                 unit tests (no network, no Kafka, no Postgres)
├── out/                   append-only audit trails and debug streams
├── requirements.txt       direct dependencies
├── requirements-optional.txt  vision, guardrails, agents, OCR
└── requirements-lock.txt  the original full `pip freeze`, kept for reproduction
```

---

## Quick start

```bash
cd services/pipeline
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-optional.txt      # for OCR / agents / face matching

cp ../../.env.example .env                    # then fill it in
python -m fraudguard doctor                   # verify everything before starting
python -m fraudguard --list
```

`doctor` is the fastest way to find out why something will not start: it reports
configuration, credentials, model artefacts, Kafka and Postgres connectivity,
schema completeness and which optional integrations are installed.

---

## Flows

Each is started the same way: `python -m fraudguard <name>`.

| Flow             | In                          | Out                     | What it does                                                  |
| ---------------- | --------------------------- | ----------------------- | ------------------------------------------------------------- |
| `kyc-ocr`        | S3 `forms/pending/`         | `entities` topic        | Document AI field extraction, face cropping, reverse search    |
| `kyc-enrichment` | `entities`                  | `db_updates` topic      | Sanctions screening, adverse media, LLM risk verdict           |
| `db-sink`        | `db_updates`                | `Staging_Buffer` table  | Type coercion and persistence (a trigger fans out from there)  |
| `rps-features`   | Debezium `...transactions`  | `rps_processed_features`| Point-in-time windowed features per user                       |
| `rps-explain`    | `rps_processed_features`    | `possible_fraud` topic  | Model score + natural-language explanation                     |
| `mcp-agent`      | `possible_fraud`            | `compliance_alerts`     | Agent decides which checks to run, then raises an alert        |
| `mcp-server`     | —                           | MCP over HTTP :8123     | Serves `ofac_call`, `pep_call`, `news_call` as tools           |
| `scorer`         | —                           | HTTP :9000              | The RPS scoring service                                        |
| `rag-server`     | watchdog corpus             | HTTP :8000              | Answers delta re-assessment questions                          |
| `watchdog`       | Postgres `Users`            | `out/watchdog_report`   | One re-screening sweep                                         |
| `scheduler`      | —                           | Postgres + RAG          | Runs the watchdog on an adaptive interval                      |

### Typical startup order

```bash
# terminal 1 — models
python -m fraudguard scorer

# terminal 2..n — the KYC path
python -m fraudguard kyc-enrichment
python -m fraudguard db-sink
python -m fraudguard kyc-ocr           # only if you have GCP + AWS credentials

# the transaction path
python -m fraudguard rps-features
python -m fraudguard rps-explain
python -m fraudguard mcp-server
python -m fraudguard mcp-agent

# continuous re-screening
python -m fraudguard rag-server
python -m fraudguard scheduler
```

---

## Layout

```
fraudguard/
├── config.py         one validated settings object, loaded once
├── logging.py        structured logging (JSON with LOG_JSON=true) + context binding
├── errors.py         the exception hierarchy every layer raises
├── schemas.py        Pathway schemas shared by the flows
├── udfs.py           reusable Pathway UDFs (each wrapping a testable pure function)
├── scoring.py        the deterministic risk algorithm — mirrors the LLM prompt exactly
├── features.py       point-in-time transaction feature builder (SQL)
├── similarity.py     change detection for adverse-media coverage
├── risk_updates.py   folding a transaction score into a user's standing risk
├── doctor.py         environment diagnostics
├── io/               http (pooled + retrying), postgres (pooled), jsonl, state
├── llm/              client, guardrails, prompts
├── enrichment/       opensanctions, ofac, search, articles, reputation, web_analysis
├── rps/              registry (model provenance), engine (inference), service, cli
├── vision/           face matching and image search
├── flows/            the runnable dataflows
└── scheduler/        the adaptive watchdog loop
```

### Design rules

1. **Nothing happens at import time.** No `pw.run()`, no API clients, no database
   connections, no `os.environ[...]`. Importing any module is free.
2. **Every UDF wraps a pure function.** `_extract_json_and_summary` is testable;
   `extract_json_and_summary` is the Pathway wrapper around it.
3. **Optional dependencies degrade, they do not crash.** Guardrails, OTX,
   scikit-learn, DeepFace and the article extractors are all optional; `doctor`
   reports what is missing.
4. **The deterministic score is always computed.** The LLM verdict is preferred
   when available, but `score_audit` records how far the two diverged, so a
   drifting model is visible in the data.

---

## The ML model

`ml/` is deliberately untouched by this refactor: the training scripts, the
pickled models, the rule engine and the processed feature parquets are exactly
as they were.

```
ml/
├── models/            *.pkl artefacts + train_*.py  (training code — do not edit)
├── rules/             rule engine, likelihood ratios, prior, evidence
├── features/          feature generation
├── fusion/            fusion model training and scoring
├── preprocessing/     dataset loading and normalisation
├── data/processed/    the parquet files inference reads
├── datasets/          raw training data
└── train_pipeline.sh  the end-to-end retraining script
```

`fraudguard/rps/engine.py` puts `ml/` on `sys.path` and imports
`rules.rule_engine`, `rules.evidence` and `rules.compute_prior` exactly as the
training pipeline does, so serving and training can never diverge.

`fraudguard/rps/registry.py` hashes every artefact at start-up and reports the
digest on `GET /model` and on every score, which is what makes a decision
reproducible after the fact.

### Retraining

```bash
cd ml && bash train_pipeline.sh
```

---

## Configuration

Everything is read from `.env` (see `.env.example` at the repository root).
`config.py` documents each group; the essentials:

| Variable                                     | Needed by                     |
| -------------------------------------------- | ----------------------------- |
| `OS_API_KEY`                                  | sanctions screening           |
| `MISTRAL_KEY`                                 | every LLM call                |
| `POSTGRES_PASSWORD`                           | anything that writes to the DB |
| `BOOTSTRAP_SERVERS`                           | every streaming flow          |
| `GOOGLE_CLOUD_API_KEY_n` + `..._SEARCH_ENGINE_ID_n` | adverse-media search    |
| `PW_LICENSE`                                  | the MCP server                |
| `GEMINI_API_KEY`                              | the MCP agent                 |
| `PROCESSOR_NAME`, `GOOGLE_APPLICATION_CREDENTIALS`, `AWS_*` | KYC intake |

Useful knobs: `LOG_JSON=true` for machine-readable logs, `LOG_LEVEL=DEBUG`,
`GUARDRAILS_ENABLED=false` to skip content validation, `RPS_LEGACY_LOGIT=true`
to reproduce scores generated before the `logit()` fix.

---

## Testing

```bash
pytest                       # unit tests only: no network, no Kafka, no Postgres
pytest -m "not integration"  # the default
ruff check fraudguard        # lint (ml/ is excluded)
```

The tests cover the scoring contract, similarity, configuration parsing, the
JSONL and state stores, and search key rotation — the pieces where a regression
would silently change a compliance decision.
