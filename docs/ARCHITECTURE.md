# Architecture

FraudGuard is a streaming KYC/AML compliance platform. It answers two questions
continuously:

1. **Is this customer who they claim to be, and are they on any list?**
2. **Does this transaction pattern look like financial crime?**

Both answers are recomputed whenever new evidence arrives — a new form, a new
transaction, a new news article — rather than on a nightly batch.

---

## The three services

```
┌────────────────────┐     ┌────────────────────┐     ┌────────────────────┐
│  services/web      │────▶│  services/api      │────▶│                    │
│  Next.js console   │◀────│  FastAPI           │◀────│    PostgreSQL      │
└────────────────────┘     └────────────────────┘     │                    │
                                                      │  system of record  │
┌──────────────────────────────────────────────┐      │                    │
│  services/pipeline                           │─────▶│                    │
│  Pathway streaming flows + the RPS model     │◀─────│                    │
└──────────────────────────────────────────────┘      └────────────────────┘
              │                    ▲                            │
              ▼                    │                            ▼ (WAL)
        ┌───────────┐        ┌──────────┐               ┌──────────────┐
        │  Kafka    │◀───────│ external │               │   Debezium   │
        │  topics   │        │   APIs   │               │     CDC      │
        └───────────┘        └──────────┘               └──────────────┘
```

* **`services/pipeline`** — everything streaming. Nine Pathway flows plus the
  model-serving HTTP service. Writes to Postgres, never to the API.
* **`services/api`** — the read/write REST layer for the console. Reads the same
  database the pipeline writes.
* **`services/web`** — the operator console.
* **`infra`** — Kafka, Postgres, Debezium, Redis, and the versioned schema.

The pipeline and the API share a database and nothing else. Neither calls the
other, so either can be restarted without affecting the other.

---

## The two paths

### 1. Onboarding — "who is this?"

```
S3 (KYC PDF)
   │  kyc-ocr
   │    Document AI field extraction · face cropping · reverse image search
   ▼
entities (Kafka)
   │  kyc-enrichment
   │    OpenSanctions screening
   │    adverse-media search → fetch → source reputation → per-article rating
   │    compliance LLM verdict, audited against the deterministic score
   ▼
db_updates (Kafka)
   │  db-sink
   ▼
Staging_Buffer ──trigger──▶ Users · ToxicityHistory · UserSanctionMatches
```

The verdict is a `risk_score` in [0, 1], a band, and a paragraph explaining the
arithmetic. Every stage appends to a JSONL audit trail under
`services/pipeline/out/`.

### 2. Monitoring — "does this behaviour look wrong?"

```
Transactions (Postgres)
   │  Debezium CDC on the write-ahead log
   ▼
postgres.public.transactions (Kafka)
   │  rps-features    point-in-time windowed aggregates per user (1h/24h/7d/30d)
   ▼
rps_processed_features (Kafka)
   │  rps-explain     scorer call + LLM interpretation
   ▼
possible_fraud (Kafka)
   │  mcp-agent       (rps > 0.4) agent decides which checks to run
   │                  ├── ofac_call ─┐
   │                  └── pep_call  ─┤ MCP tools served by mcp-server
   ▼                                 ┘
compliance_alerts ──────▶ the review queue in the console
```

### 3. Re-screening — "has anything changed since?"

```
watchdog (scheduled sweep)
   │  re-screens every customer, least-recently-checked first
   │  compares this run's adverse-media evidence with the previous snapshot
   ▼  (coverage changed?)
rag-server  → delta re-assessment → Users.current_rps_not
```

The sweep interval is adaptive: it halves when changes are found and grows after
several quiet sweeps, bounded between 10 minutes and 2 hours.

---

## Risk scoring

Two independent scores per customer, deliberately kept apart:

| Score | Source | Meaning |
| --- | --- | --- |
| `current_rps_not` | KYC + sanctions + adverse media | Standing, identity-derived risk |
| `current_rps_360` | Transaction behaviour | Latest behavioural risk |

They are combined only when a transaction verdict is applied, as a probabilistic
union — `1 − (1 − standing)(1 − incoming)` — unless the standing score is at or
below 0.2, in which case it is replaced outright so a near-clean profile is not
dragged upward by two small numbers.

### The transaction model (`services/pipeline/ml/`)

Four signals fused by logistic regression:

| Signal | Model | Input |
| --- | --- | --- |
| `p_ml` | CatBoost classifier | 25 windowed aggregates |
| `anomaly` | Isolation Forest, scaled | the same vector |
| `evidence` | Bayesian posterior | 11 deterministic rule hits × likelihood ratios × prior |
| `rps` | Logistic regression | `logit(p_ml)`, `logit(anomaly)`, `evidence` |

The training code and the artefacts are untouched by the refactor. Serving
imports `rules.rule_engine`, `rules.evidence` and `rules.compute_prior` from
`ml/` exactly as the training pipeline does, so the two cannot diverge.

Every score carries the model version — a digest over all seven artefacts,
computed at start-up — so a decision can be reproduced after the fact.

### The compliance score (`fraudguard/scoring.py`)

```
sanction_score      = min(N / 5, 1)
web_evidence_score  = 1 − Π(1 − authenticity_i × severity_i)
match_confidence    = OpenSanctions match score, in [0, 1]

risk_score = 0.60·sanction_score + 0.30·web_evidence_score + 0.10·match_confidence
```

`LOW < 0.25 ≤ MEDIUM < 0.50 ≤ HIGH < 0.75 ≤ CRITICAL`.

This is computed **twice**: once by the LLM, following the prompt, and once
deterministically in Python. The LLM's answer is used, and the divergence is
recorded as `score_audit`. When the LLM is unavailable the deterministic answer
is used and marked as such — so the pipeline never emits an unexplainable score.

---

## Design decisions

**Why a landing table and a trigger, not three writes?** `pw.io.postgres.write`
targets one table. Writing `Users`, `ToxicityHistory` and `UserSanctionMatches`
from the stream would be three non-transactional writes that could partially
fail. The trigger on `Staging_Buffer` fans out inside one transaction.

**Why CDC instead of the pipeline owning the ledger?** Transactions arrive from
whatever system already owns them. Reading the write-ahead log means the pipeline
never has to be in the write path, and it cannot lose an event by being down.

**Why compute features in SQL rather than in Pathway windows?** The model was
trained on point-in-time per-user snapshots. Reproducing that with streaming
windows requires partitioning by user and true distinct counts; the original
implementation did neither (see `fraudguard/features.py` for the specifics), so
the served features silently disagreed with the trained ones. One parameterised
query per affected user is both correct and simpler.

**Why is the watchdog not a Pathway flow?** It is static, one-shot work over a
list of entities — a streaming engine adds nothing. As plain Python it is
importable, so the scheduler calls it in-process instead of spawning a
subprocess with a ten-minute kill timer.

**Why a deterministic score next to the LLM one?** Because "the model said so"
is not an answer a regulator accepts, and because it makes LLM drift visible in
the data rather than only in a log line.

---

## Failure behaviour

| If this is down | What happens |
| --- | --- |
| OpenSanctions | The entity is scored on adverse media alone; the error is recorded in `os_error`, so "no match" and "not checked" stay distinguishable. |
| Adverse-media search | Scored on sanctions alone; the search key pool cools off exhausted keys and rotates. |
| The LLM | The deterministic score is used, with `verdict_source: "deterministic"`. |
| The scoring service | `rps-explain` falls back to scoring in-process. |
| Guardrails not installed | One warning, then content validation is skipped. |
| The MCP agent | The alert is still raised, carrying the model's own reasoning and `VERDICT: INCONCLUSIVE`. |
| Postgres | Flows fail loudly and restart; the API answers `/health/ready` with 503 and an explanation. |
| Kafka | Flows exit; nothing is lost — offsets and Pathway persistence resume where they stopped. |

Nothing silently degrades to a zero score.
