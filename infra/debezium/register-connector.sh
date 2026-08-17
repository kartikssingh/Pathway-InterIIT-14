#!/usr/bin/env bash
# Register (or update) the Postgres CDC connector.
#
# The original script POSTed in an unbounded `while true` loop, retrying every
# second forever with no ceiling and no way to tell "not ready yet" from
# "permanently misconfigured". This waits for readiness with a bounded timeout
# and uses PUT so re-running is idempotent instead of colliding with 409.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONNECT_URL="${CONNECT_URL:-http://localhost:8083}"
CONNECTOR_NAME="fraudguard-postgres"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"

# Credentials come from the environment, not from the committed config.
: "${POSTGRES_USER:=user}"
: "${POSTGRES_DB:=values_db}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"

echo "Waiting for Kafka Connect at ${CONNECT_URL} (up to ${TIMEOUT_SECONDS}s)..."
deadline=$(( $(date +%s) + TIMEOUT_SECONDS ))
until curl -sf "${CONNECT_URL}/connectors" >/dev/null 2>&1; do
  if [ "$(date +%s)" -ge "${deadline}" ]; then
    echo "ERROR: Kafka Connect did not become ready within ${TIMEOUT_SECONDS}s." >&2
    echo "       Check: docker compose -f infra/docker-compose.yml logs debezium" >&2
    exit 1
  fi
  sleep 2
done
echo "Kafka Connect is up."

# Substitute the credentials into the config, then PUT just the "config" object.
config=$(
  sed -e "s|\${POSTGRES_USER}|${POSTGRES_USER}|g" \
      -e "s|\${POSTGRES_PASSWORD}|${POSTGRES_PASSWORD}|g" \
      -e "s|\${POSTGRES_DB}|${POSTGRES_DB}|g" \
      "${HERE}/connector.json" \
  | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["config"]))'
)

status=$(
  curl -s -o /tmp/connector-response.json -w "%{http_code}" \
    -X PUT "${CONNECT_URL}/connectors/${CONNECTOR_NAME}/config" \
    -H 'Content-Type: application/json' \
    --data "${config}"
)

case "${status}" in
  200|201)
    echo "Connector '${CONNECTOR_NAME}' registered."
    ;;
  *)
    echo "ERROR: registration failed with HTTP ${status}:" >&2
    cat /tmp/connector-response.json >&2
    exit 1
    ;;
esac

echo
echo "Connector status:"
curl -sf "${CONNECT_URL}/connectors/${CONNECTOR_NAME}/status" \
  | python3 -m json.tool 2>/dev/null || true
