# FraudGuard — task runner.
#
# `make help` lists everything. Targets are thin wrappers over the same commands
# the READMEs document, so there is only ever one way to do a thing.

SHELL := /bin/bash
.DEFAULT_GOAL := help

PIPELINE := services/pipeline
API      := services/api
WEB      := services/web
COMPOSE  := docker compose -f infra/docker-compose.yml

PY  ?= python3
PKG ?= pnpm

.PHONY: help
help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# --- Setup -------------------------------------------------------------------

.PHONY: env
env: ## Create .env from the template if it does not exist
	@test -f .env || (cp .env.example .env && echo "Created .env — fill it in before continuing")

.PHONY: install
install: install-pipeline install-api install-web ## Install every service's dependencies

.PHONY: install-pipeline
install-pipeline: ## Install the pipeline's dependencies
	cd $(PIPELINE) && $(PY) -m pip install -r requirements.txt

.PHONY: install-pipeline-full
install-pipeline-full: install-pipeline ## ...including OCR, agents and face matching
	cd $(PIPELINE) && $(PY) -m pip install -r requirements-optional.txt

.PHONY: install-api
install-api: ## Install the API's dependencies
	cd $(API) && $(PY) -m pip install -r requirements-dev.txt

.PHONY: install-web
install-web: ## Install the console's dependencies
	cd $(WEB) && $(PKG) install

# --- Infrastructure ----------------------------------------------------------

.PHONY: up
up: env ## Start Kafka, Postgres, Debezium and Redis; apply migrations; create topics
	bash infra/bootstrap.sh

.PHONY: down
down: ## Stop the containers (data volumes survive)
	$(COMPOSE) down

.PHONY: reset
reset: ## Stop and DELETE the data volumes, then start clean
	$(COMPOSE) down -v
	bash infra/bootstrap.sh

.PHONY: logs
logs: ## Tail the infrastructure logs
	$(COMPOSE) logs -f --tail=100

.PHONY: psql
psql: ## Open a psql shell against the database
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-user} -d $${POSTGRES_DB:-values_db}

.PHONY: topics
topics: ## List the Kafka topics
	docker exec broker kafka-topics --list --bootstrap-server broker:29092

# --- Running -----------------------------------------------------------------

.PHONY: doctor
doctor: ## Diagnose configuration, connectivity and model artefacts
	cd $(PIPELINE) && $(PY) -m fraudguard doctor

.PHONY: flows
flows: ## List the runnable pipeline flows
	cd $(PIPELINE) && $(PY) -m fraudguard --list

.PHONY: scorer
scorer: ## Run the RPS scoring service (port 9000)
	cd $(PIPELINE) && $(PY) -m fraudguard scorer

.PHONY: api
api: ## Run the compliance API (port 8001)
	cd $(API) && $(PY) -m uvicorn app.main:app --reload --port 8001

.PHONY: web
web: ## Run the console (port 3000)
	cd $(WEB) && $(PKG) dev

# --- Data --------------------------------------------------------------------

.PHONY: seed
seed: ## Insert demo users, transactions and alerts
	docker exec -i db_tuto_postgres psql -U $${POSTGRES_USER:-user} -d $${POSTGRES_DB:-values_db} \
	  < infra/postgres/seed/010_demo_users_and_transactions.sql

.PHONY: simulate
simulate: ## Generate synthetic users and transactions
	$(PY) tools/simulate.py users --count 20
	$(PY) tools/simulate.py transactions --count 100

# --- Quality -----------------------------------------------------------------

.PHONY: test
test: test-pipeline test-api ## Run every unit test suite

.PHONY: test-pipeline
test-pipeline: ## Pipeline unit tests (no network, no Kafka, no Postgres)
	cd $(PIPELINE) && $(PY) -m pytest

.PHONY: test-api
test-api: ## API unit tests
	cd $(API) && $(PY) -m pytest tests/unit

.PHONY: lint
lint: ## Lint every service
	cd $(PIPELINE) && ruff check fraudguard
	cd $(API) && ruff check app
	cd $(WEB) && $(PKG) lint

.PHONY: typecheck
typecheck: ## Type-check the console
	cd $(WEB) && $(PKG) typecheck

.PHONY: check
check: lint test ## Lint and test everything

.PHONY: clean
clean: ## Remove caches and regenerable outputs
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	find . -name '*.pyc' -delete
	rm -rf $(PIPELINE)/.pytest_cache $(API)/.pytest_cache .ruff_cache
	rm -rf $(WEB)/.next
