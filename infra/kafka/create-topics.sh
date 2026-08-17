#!/usr/bin/env bash
# Create every topic the pipeline uses.
#
# Auto-topic-creation is disabled on the broker, so a typo in a topic name fails
# loudly instead of silently creating an empty topic nobody reads.
set -euo pipefail

BROKER_CONTAINER="${BROKER_CONTAINER:-broker}"
BOOTSTRAP="${KAFKA_INTERNAL_BOOTSTRAP:-broker:29092}"
PARTITIONS="${KAFKA_PARTITIONS:-3}"
REPLICATION="${KAFKA_REPLICATION:-1}"

# Topic:retention_ms  — audit-bearing streams are kept for 7 days, the rest 1 day.
TOPICS=(
  "entities:604800000"                    # KYC applicants from the OCR flow
  "db_updates:604800000"                  # enriched reports for the DB sink
  "rps_processed_features:86400000"       # per-user transaction features
  "possible_fraud:604800000"              # scored + explained verdicts
  "postgres.public.transactions:86400000" # Debezium CDC
  "postgres.public.toxicityhistory:86400000"
)

echo "Creating Kafka topics on ${BOOTSTRAP}..."
for entry in "${TOPICS[@]}"; do
  topic="${entry%%:*}"
  retention="${entry##*:}"
  docker exec "${BROKER_CONTAINER}" kafka-topics \
    --create --if-not-exists \
    --topic "${topic}" \
    --partitions "${PARTITIONS}" \
    --replication-factor "${REPLICATION}" \
    --config "retention.ms=${retention}" \
    --bootstrap-server "${BOOTSTRAP}" >/dev/null
  echo "  ok  ${topic}  (retention ${retention} ms)"
done

echo
echo "Topics now present:"
docker exec "${BROKER_CONTAINER}" kafka-topics --list --bootstrap-server "${BOOTSTRAP}" | sed 's/^/  /'
