# Sample payloads

Small fixtures for exercising the pipeline by hand. None of them are read
automatically — the running system is fed by Kafka, S3 and Postgres CDC.

| File                 | What it is                                                    |
| -------------------- | ------------------------------------------------------------- |
| `score_request.json` | A `POST /score` body for the RPS service.                      |
| `entity.json`        | One message as published to the `entities` topic by `kyc-ocr`. |

## Score a feature vector

```bash
curl -s -X POST http://127.0.0.1:9000/score \
  -H 'Content-Type: application/json' \
  -d @samples/score_request.json | jq
```

## Inject a KYC applicant without running OCR

Skips the S3 → Document AI stage and feeds `kyc-enrichment` directly:

```bash
docker exec -i broker kafka-console-producer \
  --topic entities --bootstrap-server broker:29092 < samples/entity.json
```

## Trigger the transaction path

Any insert on `Transactions` is picked up by Debezium and flows into
`rps-features` → `rps-explain` → `mcp-agent`:

```bash
docker exec db_tuto_postgres psql -U user -d values_db -c "
INSERT INTO Transactions
    (transaction_id, user_id, txn_timestamp, amount, currency, txn_type, counterparty_id, is_fraud)
VALUES
    (900001, 829, NOW(), 7550.99, 'EUR', 'PURCHASE', 10012, 0);
"
```

The scored result appears in `out/rps_output.jsonl` and, above the escalation
threshold, as a row in `compliance_alerts`.
