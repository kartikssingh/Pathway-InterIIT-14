#!/usr/bin/env bash
# One command to stand up the whole local environment.
#
# Replaces setup/docker-init.sh, which was ~700 lines of `docker exec ... psql -c "..."`
# heredocs: unversioned, non-idempotent (every table was DROPped first, so a
# re-run destroyed the data), and it dropped a table whose CREATE later failed
# on a bad index, leaving the database half-built with no error surfaced.
#
# Schema now lives in versioned files under infra/postgres/migrations/, applied
# in order and safe to re-run.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
COMPOSE="docker compose -f ${HERE}/docker-compose.yml"

# shellcheck disable=SC1091
if [ -f "${REPO_ROOT}/.env" ]; then
  set -a; source "${REPO_ROOT}/.env"; set +a
else
  echo "ERROR: ${REPO_ROOT}/.env not found. Copy .env.example and fill it in." >&2
  exit 1
fi

: "${POSTGRES_USER:=user}"
: "${POSTGRES_DB:=values_db}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set in .env}"

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

step "Starting containers"
${COMPOSE} up -d

step "Waiting for Postgres and Kafka to report healthy"
for service in postgres broker; do
  printf '  %s' "${service}"
  for _ in $(seq 1 60); do
    state=$(${COMPOSE} ps --format json "${service}" 2>/dev/null \
            | python3 -c 'import json,sys
try:
    data=json.loads(sys.stdin.read() or "{}")
except json.JSONDecodeError:
    data={}
if isinstance(data, list):
    data = data[0] if data else {}
print(data.get("Health") or data.get("State") or "")' 2>/dev/null || echo "")
    if [ "${state}" = "healthy" ]; then break; fi
    printf '.'
    sleep 2
  done
  echo " ok"
done

step "Applying database migrations"
# The compose file also mounts these into docker-entrypoint-initdb.d, which runs
# only on a fresh volume. Applying them here as well makes an existing database
# converge — every file is idempotent.
for migration in "${HERE}"/postgres/migrations/*.sql; do
  echo "  $(basename "${migration}")"
  ${COMPOSE} exec -T postgres \
    psql -v ON_ERROR_STOP=1 -q -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" < "${migration}"
done

step "Creating Kafka topics"
bash "${HERE}/kafka/create-topics.sh"

step "Registering the Debezium connector"
bash "${HERE}/debezium/register-connector.sh"

step "Done"
cat <<EOF

  Postgres   localhost:${POSTGRES_PORT:-5432}   db=${POSTGRES_DB} user=${POSTGRES_USER}
  Kafka      localhost:${KAFKA_EXTERNAL_PORT:-9092}
  Debezium   http://localhost:${DEBEZIUM_PORT:-8083}
  Redis      localhost:${REDIS_PORT:-6379}

  Default console logins (change them):
    superadmin / superadmin123
    admin      / admin123

  Next:
    cd services/pipeline && python -m fraudguard doctor
    cd services/api      && python -m uvicorn app.main:app --reload --port 8001
    cd services/web      && pnpm dev
EOF
