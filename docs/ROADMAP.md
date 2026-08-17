# Roadmap — production readiness

Critical (P0) and high-priority (P1) work for taking the system to production.

> **Status after the 2.0 refactor.** Each item below needs external
> infrastructure (Vault, object storage, Elasticsearch), so none is implemented
> in full. The parts that deliver the same compliance value *without* new
> infrastructure are now in place, and are noted per item.
>
> | Item | Status |
> | --- | --- |
> | P0.1 Secrets management (Vault) | **Not implemented.** Mitigated: one `.env` at the repository root instead of files scattered across the tree; validated at start-up; the API refuses to run in production with the committed placeholder `SECRET_KEY`; no credential remains in source (the hard-coded Pathway licence key is gone). |
> | P0.2 Model versioning (DVC) | **Partly done.** `fraudguard/rps/registry.py` hashes every artefact at start-up, `GET /model` reports the digests, and every score carries the model version — so a decision is reproducible. Remote artefact storage and rollback still need DVC. Models and processed data are now tracked in git rather than ignored. |
> | P0.3 Centralised logging (ELK) | **Partly done.** Every service emits newline-delimited JSON with bound per-record context under `LOG_JSON=true`, ready for any shipper. Elasticsearch, Logstash and Kibana are not deployed. |
> | P1.1 Migrations (Alembic) | **Partly done.** The schema is versioned in `infra/postgres/migrations/`, applied in order, idempotent and re-runnable. Alembic's autogeneration and downgrade paths are not wired up. |
> | **P0.4 Endpoint authentication** | **Open — new, found during the refactor audit.** 38 of the API's 69 operations declare no auth dependency; 5 are public by design, leaving 33 that should not be — including `POST /export/users`, `POST /export/transactions` and every transaction mutation. Not fixed here because it changes the behaviour of 33 routes and cannot be verified without a running stack. See the audit procedure in [OPERATIONS.md](OPERATIONS.md#auditing-endpoint-authentication). |
> | P1.2 Persistent state | **Done, locally.** `fraudguard/io/state.py` provides versioned, compressed, per-key snapshots with retention and pruning; the watchdog uses it in place of copying directories. The S3 mirror is a `uploader=` hook, not yet wired to a bucket. |
>
> See [REFACTOR_NOTES.md](REFACTOR_NOTES.md) for everything else that changed.

The original plan follows, unchanged.

---

## 🔴 P0 - Critical Priority Fixes

### P0.1: Implement Secrets Management with HashiCorp Vault

**Issue:**
- Multiple `.env` files scattered across the codebase (root `.env`, `backend/.env`, `backend/.env.*`)
- `.pypirc` file contains package repository credentials
- High risk of accidentally committing secrets to version control
- No secrets rotation strategy
- Violates security best practices for financial/compliance systems
- Secrets are hardcoded and not centrally managed

**Impact:**
- **Security Risk**: Credential leaks could expose database, APIs, and third-party services
- **Compliance Violation**: Financial systems require secure credential management
- **Operational Risk**: No way to rotate compromised credentials quickly

**Fix:**

#### Step 1: Add HashiCorp Vault to Docker Compose

```yaml
# Add to docker-compose.yml
services:
  vault:
    image: vault:latest
    container_name: fraud_vault
    ports:
      - "8200:8200"
    environment:
      VAULT_DEV_ROOT_TOKEN_ID: "${VAULT_ROOT_TOKEN}"
      VAULT_DEV_LISTEN_ADDRESS: "0.0.0.0:8200"
    cap_add:
      - IPC_LOCK
    volumes:
      - ./vault/config:/vault/config
      - ./vault/data:/vault/data
    command: server -dev

  backend:
    environment:
      - VAULT_ADDR=http://vault:8200
      - VAULT_TOKEN=${VAULT_TOKEN}
    depends_on:
      - vault
```

#### Step 2: Create Secrets Manager Module

```python
# backend/app/config/secrets.py
import hvac
import os
from functools import lru_cache
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SecretsManager:
    """Centralized secrets management using HashiCorp Vault"""
    
    def __init__(self):
        vault_addr = os.getenv('VAULT_ADDR', 'http://localhost:8200')
        vault_token = os.getenv('VAULT_TOKEN')
        
        if not vault_token:
            raise RuntimeError("VAULT_TOKEN environment variable not set")
        
        self.client = hvac.Client(url=vault_addr, token=vault_token)
        
        if not self.client.is_authenticated():
            raise RuntimeError("Failed to authenticate with Vault")
        
        logger.info(f"Connected to Vault at {vault_addr}")
    
    @lru_cache(maxsize=128)
    def get_secret(self, path: str, key: str) -> str:
        """
        Fetch secret from Vault with caching
        
        Args:
            path: Secret path in Vault (e.g., 'database', 'api/mistral')
            key: Key within the secret (e.g., 'password', 'api_key')
        
        Returns:
            Secret value as string
        """
        try:
            secret = self.client.secrets.kv.v2.read_secret_version(path=path)
            return secret['data']['data'][key]
        except Exception as e:
            logger.error(f"Failed to fetch secret from {path}/{key}: {e}")
            raise RuntimeError(f"Failed to fetch secret: {e}")
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get PostgreSQL database credentials"""
        return {
            'host': self.get_secret('database', 'host'),
            'port': int(self.get_secret('database', 'port')),
            'user': self.get_secret('database', 'user'),
            'password': self.get_secret('database', 'password'),
            'database': self.get_secret('database', 'dbname'),
        }
    
    def get_mistral_api_key(self) -> str:
        """Get Mistral AI API key"""
        return self.get_secret('api/mistral', 'api_key')
    
    def get_kafka_config(self) -> Dict[str, Any]:
        """Get Kafka connection configuration"""
        return {
            'bootstrap_servers': self.get_secret('kafka', 'bootstrap_servers'),
            'sasl_username': self.get_secret('kafka', 'sasl_username'),
            'sasl_password': self.get_secret('kafka', 'sasl_password'),
        }
    
    def refresh_cache(self):
        """Clear cached secrets to force refresh"""
        self.get_secret.cache_clear()

# Global instance
secrets_manager = SecretsManager()
```

#### Step 3: Update Database Connection

```python
# backend/app/db.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config.secrets import secrets_manager

# Get credentials from Vault
db_config = secrets_manager.get_database_config()

DATABASE_URL = (
    f"postgresql://{db_config['user']}:{db_config['password']}"
    f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

#### Step 4: Migration Script

```bash
#!/bin/bash
# scripts/migrate_secrets_to_vault.sh

set -e

echo "Migrating secrets to Vault..."

# Source existing .env file
if [ -f backend/.env ]; then
    source backend/.env
    
    # Write database secrets
    vault kv put secret/database \
        host="${DB_HOST}" \
        port="${DB_PORT}" \
        user="${DB_USER}" \
        password="${DB_PASSWORD}" \
        dbname="${DB_NAME}"
    
    # Write API keys
    vault kv put secret/api/mistral \
        api_key="${MISTRAL_API_KEY}"
    
    # Write Kafka config
    vault kv put secret/kafka \
        bootstrap_servers="${KAFKA_BOOTSTRAP_SERVERS}" \
        sasl_username="${KAFKA_SASL_USERNAME}" \
        sasl_password="${KAFKA_SASL_PASSWORD}"
    
    echo "✅ Secrets migrated successfully"
    echo "⚠️  Please remove backend/.env after verification"
else
    echo "❌ backend/.env not found"
    exit 1
fi
```

#### Step 5: Update .gitignore

Remove `.env` files from tracking and add Vault data:

```gitignore
# Secrets Management
vault/data/
vault/logs/
.vault-token

# Keep .env.example for reference
backend/.env
backend/.env.*
.env
.env.*
```

**Timeline**: 2-3 days  
**Priority**: P0 - Must fix before production deployment

---

### P0.2: Add ML Model Versioning with DVC

**Issue:**
- ML models, training data, and processed datasets are completely ignored in `.gitignore`:
  ```
  rps/src/datasets/rps_training
  rps/src/data/processed
  rps/src/models
  ```
- No way to reproduce model predictions
- Cannot rollback to previous model versions
- No tracking of which model was used for which predictions
- Training data changes are untracked
- Violates ML compliance and audit requirements

**Impact:**
- **Reproducibility Crisis**: Cannot explain fraud detection decisions to regulators
- **Model Drift**: No baseline to compare against when model performance degrades
- **Compliance Risk**: Financial regulations require explainable AI and audit trails
- **Operational Risk**: Cannot rollback broken model deployments

**Fix:**

#### Step 1: Install DVC with Cloud Storage

```bash
# Choose your cloud provider
pip install dvc[s3]      # For AWS S3
# OR
pip install dvc[gs]      # For Google Cloud Storage
# OR
pip install dvc[azure]   # For Azure Blob Storage

# Add to requirements.txt
echo "dvc[s3]>=3.0.0" >> rps/requirements.txt
```

#### Step 2: Initialize DVC in RPS Directory

```bash
cd rps
dvc init

# Configure remote storage (example with S3)
dvc remote add -d storage s3://your-fraud-ml-bucket/dvc-store
dvc remote modify storage region us-east-1

# For other providers:
# GCS: dvc remote add -d storage gs://your-bucket/dvc-store
# Azure: dvc remote add -d storage azure://your-container/dvc-store
```

#### Step 3: Track Models and Data

```bash
# Track training datasets
dvc add src/datasets/rps_training

# Track processed data
dvc add src/data/processed

# Track trained models
dvc add src/models

# Commit DVC metadata files
git add src/datasets/rps_training.dvc \
        src/data/processed.dvc \
        src/models.dvc \
        .dvc/config
git commit -m "Add DVC tracking for ML artifacts"

# Push to remote storage
dvc push
```

#### Step 4: Create Model Registry Module

```python
# rps/src/model_registry.py
import dvc.api
from pathlib import Path
from typing import Optional, Dict, Any
import json
from datetime import datetime
import hashlib

class ModelRegistry:
    """Track and version ML models with metadata"""
    
    def __init__(self, models_path: str = "src/models"):
        self.models_path = Path(models_path)
        self.registry_file = self.models_path / "registry.json"
        self.registry = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load model registry metadata"""
        if self.registry_file.exists():
            with open(self.registry_file, 'r') as f:
                return json.load(f)
        return {"models": []}
    
    def _save_registry(self):
        """Save model registry metadata"""
        with open(self.registry_file, 'w') as f:
            json.dump(self.registry, f, indent=2)
    
    def register_model(
        self,
        model_path: str,
        model_name: str,
        version: str,
        metrics: Dict[str, float],
        training_data_version: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Register a new model version with metadata
        
        Args:
            model_path: Path to model file
            model_name: Name of the model (e.g., 'rps_scorer')
            version: Semantic version (e.g., '1.0.0')
            metrics: Model performance metrics
            training_data_version: Version of training data used
            metadata: Additional metadata (hyperparameters, etc.)
        """
        # Calculate model hash for integrity
        with open(model_path, 'rb') as f:
            model_hash = hashlib.sha256(f.read()).hexdigest()
        
        model_entry = {
            "name": model_name,
            "version": version,
            "path": str(model_path),
            "hash": model_hash,
            "metrics": metrics,
            "training_data_version": training_data_version,
            "registered_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.registry["models"].append(model_entry)
        self._save_registry()
        
        print(f"✅ Registered {model_name} v{version}")
        print(f"   Hash: {model_hash[:8]}...")
        print(f"   Metrics: {metrics}")
    
    def get_model(self, model_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Get model metadata by name and version
        
        Args:
            model_name: Name of the model
            version: Specific version, or None for latest
        
        Returns:
            Model metadata dictionary
        """
        models = [m for m in self.registry["models"] if m["name"] == model_name]
        
        if not models:
            raise ValueError(f"Model {model_name} not found in registry")
        
        if version:
            models = [m for m in models if m["version"] == version]
            if not models:
                raise ValueError(f"Version {version} not found for {model_name}")
        
        # Return latest version
        return sorted(models, key=lambda x: x["registered_at"], reverse=True)[0]
    
    def list_models(self) -> list:
        """List all registered models"""
        return self.registry["models"]

# Usage example
registry = ModelRegistry()

# After training
registry.register_model(
    model_path="src/models/rps_scorer_v2.pkl",
    model_name="rps_scorer",
    version="2.0.0",
    metrics={
        "accuracy": 0.94,
        "precision": 0.92,
        "recall": 0.89,
        "f1_score": 0.90,
        "auc_roc": 0.96
    },
    training_data_version="2024-12-01",
    metadata={
        "algorithm": "CatBoost",
        "hyperparameters": {
            "iterations": 1000,
            "learning_rate": 0.03,
            "depth": 6
        },
        "feature_count": 47,
        "training_samples": 150000
    }
)
```

#### Step 5: Update .gitignore

```gitignore
# Remove these lines that ignore everything:
# rps/src/datasets/rps_training
# rps/src/data/processed
# rps/src/models

# Instead, track DVC metadata and ignore only the actual data:
!rps/src/datasets/rps_training.dvc
!rps/src/data/processed.dvc
!rps/src/models.dvc
!rps/src/models/registry.json

# DVC internals
rps/.dvc/tmp/
rps/.dvc/cache/
```

#### Step 6: Model Loading with DVC

```python
# rps/src/inference.py
import dvc.api
import pickle
from pathlib import Path

def load_production_model(model_name: str = "rps_scorer", version: str = None):
    """
    Load model from DVC storage
    
    Args:
        model_name: Name of the model
        version: Git tag/commit for specific version, or None for latest
    """
    registry = ModelRegistry()
    model_info = registry.get_model(model_name, version)
    
    # DVC will fetch from remote if not in cache
    with dvc.api.open(
        model_info["path"],
        repo="/path/to/repo",
        rev=version  # Git revision
    ) as f:
        model = pickle.load(f)
    
    print(f"Loaded {model_name} v{model_info['version']}")
    print(f"Model hash: {model_info['hash'][:8]}...")
    print(f"Trained on: {model_info['training_data_version']}")
    
    return model, model_info
```

#### Step 7: CI/CD Integration

```yaml
# .github/workflows/model-validation.yml
name: Model Validation

on:
  pull_request:
    paths:
      - 'rps/src/models/**'
      - 'rps/src/datasets/**'

jobs:
  validate-model:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: iterative/setup-dvc@v1
      
      - name: Pull model artifacts
        run: |
          cd rps
          dvc pull
      
      - name: Validate model performance
        run: |
          python rps/scripts/validate_model.py \
            --min-accuracy 0.90 \
            --min-auc 0.92
      
      - name: Check model size
        run: |
          # Ensure model is under size limit
          find rps/src/models -name "*.pkl" -size +100M -exec false {} +
```

**Timeline**: 1-2 days  
**Priority**: P0 - Required for ML model governance and compliance

---

### P0.3: Setup Centralized Logging with ELK Stack

**Issue:**
- All log files are ignored in `.gitignore`:
  ```
  *.log
  backend/logs/
  backend/*.log
  ```
- No centralized log aggregation
- Cannot debug production issues or investigate fraud incidents
- No audit trail for compliance
- No alerting on critical errors
- Logs lost when containers restart

**Impact:**
- **Operational Blindness**: Cannot diagnose production issues
- **Compliance Violation**: Financial regulations require comprehensive audit logs
- **Security Risk**: Cannot detect or investigate security breaches
- **Customer Impact**: Cannot trace transaction issues or disputes

**Fix:**

#### Step 1: Add ELK Stack to Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: fraud_elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
    networks:
      - elk

  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    container_name: fraud_logstash
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
      - ./logstash/config/logstash.yml:/usr/share/logstash/config/logstash.yml
    ports:
      - "5000:5000"  # TCP input
      - "5044:5044"  # Beats input
    environment:
      - "LS_JAVA_OPTS=-Xmx256m -Xms256m"
    depends_on:
      - elasticsearch
    networks:
      - elk

  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    container_name: fraud_kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
    networks:
      - elk

  backend:
    environment:
      - LOGSTASH_HOST=logstash
      - LOGSTASH_PORT=5000
    depends_on:
      - logstash
    networks:
      - elk

volumes:
  elasticsearch_data:

networks:
  elk:
    driver: bridge
```

#### Step 2: Create Logstash Pipeline Configuration

```yaml
# logstash/pipeline/logstash.conf
input {
  tcp {
    port => 5000
    codec => json
  }
  
  beats {
    port => 5044
  }
}

filter {
  # Parse JSON logs
  if [type] == "fraud_detection" {
    json {
      source => "message"
    }
    
    # Add GeoIP for transaction locations
    if [ip_address] {
      geoip {
        source => "ip_address"
        target => "geo"
      }
    }
    
    # Parse risk scores
    if [risk_score] {
      mutate {
        convert => { "risk_score" => "float" }
      }
    }
    
    # Tag high-risk transactions
    if [risk_score] >= 0.8 {
      mutate {
        add_tag => ["high_risk"]
      }
    }
  }
  
  # Parse timestamp
  date {
    match => ["timestamp", "ISO8601"]
    target => "@timestamp"
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "fraud-logs-%{+YYYY.MM.dd}"
  }
  
  # For debugging
  stdout {
    codec => rubydebug
  }
}
```

```yaml
# logstash/config/logstash.yml
http.host: "0.0.0.0"
xpack.monitoring.elasticsearch.hosts: ["http://elasticsearch:9200"]
```

#### Step 3: Implement Structured Logging Module

```python
# backend/app/utils/logging.py
import logging
import structlog
from logging.handlers import SocketHandler
from pythonjsonlogger import jsonlogger
import os
from typing import Optional, Dict, Any
from datetime import datetime

def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    logstash_host: Optional[str] = None,
    logstash_port: int = 5000
):
    """
    Configure structured logging for ELK stack
    
    Args:
        service_name: Name of the service (e.g., 'backend', 'rps')
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        logstash_host: Logstash server hostname
        logstash_port: Logstash TCP port
    """
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Setup standard logging
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    json_formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s',
        timestamp=True
    )
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)
    
    # Logstash handler if configured
    if logstash_host:
        logstash_handler = SocketHandler(logstash_host, logstash_port)
        logstash_handler.setFormatter(json_formatter)
        logger.addHandler(logstash_handler)
        print(f"✅ Connected to Logstash at {logstash_host}:{logstash_port}")
    
    return structlog.get_logger(service=service_name)


class FraudLogger:
    """Specialized logger for fraud detection events"""
    
    def __init__(self, service_name: str):
        self.logger = structlog.get_logger(service=service_name)
    
    def log_transaction(
        self,
        transaction_id: str,
        user_id: str,
        amount: float,
        risk_score: float,
        decision: str,
        **kwargs
    ):
        """Log transaction processing"""
        self.logger.info(
            "transaction_processed",
            type="fraud_detection",
            transaction_id=transaction_id,
            user_id=user_id,
            amount=amount,
            risk_score=risk_score,
            decision=decision,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_alert(
        self,
        alert_id: str,
        alert_type: str,
        severity: str,
        user_id: str,
        reason: str,
        **kwargs
    ):
        """Log fraud alert generation"""
        self.logger.warning(
            "alert_generated",
            type="fraud_detection",
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            user_id=user_id,
            reason=reason,
            timestamp=datetime.utcnow().isoformat(),
            **kwargs
        )
    
    def log_model_prediction(
        self,
        model_name: str,
        model_version: str,
        features: Dict[str, Any],
        prediction: float,
        transaction_id: str
    ):
        """Log ML model predictions for auditability"""
        self.logger.info(
            "model_prediction",
            type="ml_inference",
            model_name=model_name,
            model_version=model_version,
            features=features,
            prediction=prediction,
            transaction_id=transaction_id,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def log_compliance_check(
        self,
        user_id: str,
        check_type: str,
        result: str,
        details: Dict[str, Any]
    ):
        """Log compliance screening results"""
        self.logger.info(
            "compliance_check",
            type="compliance",
            user_id=user_id,
            check_type=check_type,
            result=result,
            details=details,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def log_error(
        self,
        error_message: str,
        error_type: str,
        context: Dict[str, Any],
        exc_info: bool = True
    ):
        """Log errors with context"""
        self.logger.error(
            "error_occurred",
            error_message=error_message,
            error_type=error_type,
            context=context,
            timestamp=datetime.utcnow().isoformat(),
            exc_info=exc_info
        )
```

#### Step 4: Integrate Logging in Backend

```python
# backend/app/main.py
from fastapi import FastAPI, Request
from app.utils.logging import setup_logging, FraudLogger
import os
import time

# Initialize logging
logger = setup_logging(
    service_name="backend",
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    logstash_host=os.getenv("LOGSTASH_HOST"),
    logstash_port=int(os.getenv("LOGSTASH_PORT", "5000"))
)

fraud_logger = FraudLogger("backend")

app = FastAPI(title="Fraud Detection API")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    
    logger.info(
        "http_request",
        method=request.method,
        url=str(request.url),
        status_code=response.status_code,
        duration_ms=round(duration * 1000, 2),
        client_ip=request.client.host
    )
    
    return response

# Usage in routes
@app.post("/transactions/process")
async def process_transaction(transaction: TransactionCreate):
    # ... process transaction ...
    
    fraud_logger.log_transaction(
        transaction_id=result.transaction_id,
        user_id=transaction.user_id,
        amount=transaction.amount,
        risk_score=result.risk_score,
        decision=result.decision,
        payment_method=transaction.payment_method,
        merchant_id=transaction.merchant_id
    )
    
    return result
```

#### Step 5: Create Kibana Dashboards

```json
// kibana/dashboards/fraud_overview.json
{
  "title": "Fraud Detection Overview",
  "visualizations": [
    {
      "title": "High Risk Transactions",
      "type": "metric",
      "query": "risk_score >= 0.8 AND type:fraud_detection"
    },
    {
      "title": "Alerts by Severity",
      "type": "pie",
      "query": "type:fraud_detection AND alert_type:*"
    },
    {
      "title": "Transaction Volume",
      "type": "line",
      "query": "type:fraud_detection"
    },
    {
      "title": "Model Performance",
      "type": "table",
      "query": "type:ml_inference"
    }
  ]
}
```

#### Step 6: Setup Alerting

```python
# backend/app/utils/alerting.py
from elasticsearch import Elasticsearch
import requests

class LogAlertManager:
    """Send alerts based on log patterns"""
    
    def __init__(self, es_host: str = "localhost:9200"):
        self.es = Elasticsearch([es_host])
    
    def check_high_risk_volume(self, threshold: int = 100):
        """Alert if too many high-risk transactions"""
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"range": {"risk_score": {"gte": 0.8}}},
                        {"range": {"@timestamp": {"gte": "now-1h"}}}
                    ]
                }
            }
        }
        
        result = self.es.count(index="fraud-logs-*", body=query)
        
        if result["count"] > threshold:
            self.send_alert(
                f"High volume of risky transactions: {result['count']} in last hour",
                severity="critical"
            )
    
    def send_alert(self, message: str, severity: str):
        """Send alert to monitoring system"""
        # Integrate with PagerDuty, Slack, etc.
        pass
```

#### Step 7: Update .gitignore

```gitignore
# Keep log directory structure but ignore log files
!backend/logs/.gitkeep
backend/logs/*.log
backend/logs/*.gz

# Elasticsearch data
elasticsearch_data/

# Logstash temp files
logstash/data/

# Keep configuration
!logstash/pipeline/
!logstash/config/
!kibana/dashboards/
```

**Timeline**: 3-4 days  
**Priority**: P0 - Required for production operations and compliance

---

## 🟠 P1 - High Priority Fixes

### P1.1: Add Database Migration Management with Alembic

**Issue:**
- No visible database migration tracking system
- Schema changes are unversioned and untracked
- Cannot safely rollback database changes
- High risk of schema inconsistencies between environments
- No audit trail of database evolution
- PostgreSQL migration mentioned but no Alembic configuration found

**Impact:**
- **Data Corruption Risk**: Manual schema changes can corrupt production data
- **Deployment Failures**: Schema mismatches between code and database
- **Rollback Impossible**: Cannot revert problematic database changes
- **Team Coordination**: Multiple developers making conflicting schema changes

**Fix:**

#### Step 1: Install and Initialize Alembic

```bash
cd backend
pip install alembic psycopg2-binary

# Add to requirements.txt
echo "alembic>=1.13.0" >> requirements.txt
echo "psycopg2-binary>=2.9.9" >> requirements.txt

# Initialize Alembic
alembic init migrations
```

#### Step 2: Configure Alembic with Vault Integration

```python
# backend/migrations/env.py
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models import Base  # Import all models
from app.config.secrets import secrets_manager

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database credentials from Vault
db_config = secrets_manager.get_database_config()
database_url = (
    f"postgresql://{db_config['user']}:{db_config['password']}"
    f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
)
config.set_main_option("sqlalchemy.url", database_url)

# Set target metadata for autogenerate
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

#### Step 3: Create Initial Migration

```bash
# Generate initial schema migration
alembic revision --autogenerate -m "Initial schema - users, transactions, alerts"

# Review the generated migration file in migrations/versions/

# Apply migration
alembic upgrade head
```

#### Step 4: Create Migration Helper Scripts

```bash
#!/bin/bash
# scripts/db_migrate.sh

set -e

ACTION=$1
MESSAGE=$2

case $ACTION in
  create)
    if [ -z "$MESSAGE" ]; then
      echo "Usage: ./db_migrate.sh create 'migration message'"
      exit 1
    fi
    cd backend
    alembic revision --autogenerate -m "$MESSAGE"
    echo "✅ Migration created. Review file in backend/migrations/versions/"
    ;;
    
  upgrade)
    cd backend
    alembic upgrade head
    echo "✅ Database upgraded to latest version"
    ;;
    
  downgrade)
    cd backend
    STEPS=${MESSAGE:-1}
    alembic downgrade -$STEPS
    echo "✅ Database downgraded $STEPS step(s)"
    ;;
    
  history)
    cd backend
    alembic history --verbose
    ;;
    
  current)
    cd backend
    alembic current
    ;;
    
  *)
    echo "Usage: ./db_migrate.sh {create|upgrade|downgrade|history|current}"
    echo ""
    echo "Examples:"
    echo "  ./db_migrate.sh create 'Add transaction_type column'"
    echo "  ./db_migrate.sh upgrade"
    echo "  ./db_migrate.sh downgrade 2"
    echo "  ./db_migrate.sh history"
    exit 1
    ;;
esac
```

```bash
chmod +x scripts/db_migrate.sh
```

#### Step 5: Add Migration Testing

```python
# backend/tests/test_migrations.py
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from app.models import User, Transaction, Alert

def test_migrations_up_and_down():
    """Test that migrations can be applied and rolled back"""
    alembic_cfg = Config("alembic.ini")
    
    # Upgrade to head
    command.upgrade(alembic_cfg, "head")
    
    # Verify tables exist
    engine = create_engine(alembic_cfg.get_main_option("sqlalchemy.url"))
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    assert "users" in tables
    assert "transactions" in tables
    assert "alerts" in tables
    
    # Downgrade one step
    command.downgrade(alembic_cfg, "-1")
    
    # Upgrade again
    command.upgrade(alembic_cfg, "head")

def test_migration_data_preservation():
    """Test that migrations don't lose data"""
    # This would test specific migration scenarios
    pass
```

#### Step 6: CI/CD Integration

```yaml
# .github/workflows/db-migration-check.yml
name: Database Migration Check

on:
  pull_request:
    paths:
      - 'backend/app/models/**'
      - 'backend/migrations/**'

jobs:
  check-migrations:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: fraud_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      
      - name: Check for migration conflicts
        run: |
          cd backend
          alembic branches
          # Should have no output if no conflicts
      
      - name: Test migrations
        run: |
          cd backend
          alembic upgrade head
          alembic current
      
      - name: Rollback test
        run: |
          cd backend
          alembic downgrade -1
          alembic upgrade head
```

#### Step 7: Document Migration Workflow

```markdown
# backend/docs/MIGRATION_GUIDE.md

## Database Migration Workflow

### Creating a New Migration

1. Make changes to models in `app/models/`
2. Generate migration:
   ```bash
   ./scripts/db_migrate.sh create "Add new column to transactions"
   ```
3. Review the generated file in `migrations/versions/`
4. Test locally:
   ```bash
   ./scripts/db_migrate.sh upgrade
   ```

### Applying Migrations in Production

1. Backup database:
   ```bash
   pg_dump -h localhost -U user fraud_db > backup_$(date +%Y%m%d).sql
   ```

2. Apply migrations:
   ```bash
   ./scripts/db_migrate.sh upgrade
   ```

3. Verify:
   ```bash
   ./scripts/db_migrate.sh current
   ```

### Rolling Back

If something goes wrong:
```bash
./scripts/db_migrate.sh downgrade 1  # Roll back 1 migration
```

### Best Practices

- Always review auto-generated migrations
- Test migrations on staging first
- Never modify applied migrations
- Keep migrations small and focused
- Add data migrations separately from schema migrations
```

#### Step 8: Update .gitignore

```gitignore
# Track migrations directory structure
!backend/migrations/
!backend/migrations/versions/
backend/migrations/__pycache__/
backend/migrations/versions/__pycache__/

# Track all migration files
!backend/migrations/versions/*.py
```

**Timeline**: 1 day  
**Priority**: P1 - Critical for safe database changes

---

### P1.2: Implement Persistent State Management

**Issue:**
- Critical state directories completely ignored:
  ```
  persistence_test/
  PState/
  MCPPState/
  ```
- No backup or recovery strategy for state data
- State lost on container restarts
- No compliance-ready retention policy
- Audit trail disappears with ephemeral storage

**Impact:**
- **Data Loss**: Streaming state lost on pod/container restarts
- **Compliance Violation**: Cannot maintain required audit history
- **Recovery Impossible**: Cannot recover from failures
- **Investigation Blocked**: Historical state needed for fraud analysis

**Fix:**

#### Step 1: Create State Management Module

```python
# backend/app/utils/state_manager.py
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import boto3
from botocore.exceptions import ClientError
import logging
import pickle
import gzip

logger = logging.getLogger(__name__)

class StateManager:
    """
    Persistent state management with S3 backup for compliance
    Handles both local state and cloud backup for disaster recovery
    """
    
    def __init__(
        self,
        local_path: str = "PState",
        s3_bucket: Optional[str] = None,
        retention_days: int = 2555  # 7 years for compliance
    ):
        self.local_path = Path(local_path)
        self.local_path.mkdir(exist_ok=True, parents=True)
        
        self.s3_bucket = s3_bucket
        self.retention_days = retention_days
        self.s3_client = None
        
        if s3_bucket:
            self.s3_client = boto3.client('s3')
            logger.info(f"State manager initialized with S3 backup: {s3_bucket}")
        else:
            logger.warning("State manager running without S3 backup - not production ready!")
    
    def save_state(
        self,
        key: str,
        data: Dict[Any, Any],
        metadata: Optional[Dict[str, Any]] = None,
        compress: bool = True
    ):
        """
        Save state locally and backup to S3
        
        Args:
            key: State identifier (e.g., 'kafka_offset', 'model_state')
            data: State data to persist
            metadata: Additional metadata (user_id, transaction_id, etc.)
            compress: Whether to compress state files
        """
        timestamp = datetime.utcnow()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S_%f")
        
        # Prepare state object
        state_obj = {
            "key": key,
            "timestamp": timestamp.isoformat(),
            "data": data,
            "metadata": metadata or {},
            "version": "1.0"
        }
        
        # Local save
        state_file = self.local_path / f"{key}_{timestamp_str}.json"
        
        if compress:
            state_file = state_file.with_suffix('.json.gz')
            with gzip.open(state_file, 'wt', encoding='utf-8') as f:
                json.dump(state_obj, f, indent=2)
        else:
            with open(state_file, 'w') as f:
                json.dump(state_obj, f, indent=2)
        
        logger.debug(f"State saved locally: {state_file}")
        
        # S3 backup for compliance
        if self.s3_client:
            try:
                s3_key = f"state/{key}/{timestamp.year}/{timestamp.month:02d}/{timestamp_str}.json.gz"
                
                if compress:
                    self.s3_client.upload_file(
                        str(state_file),
                        self.s3_bucket,
                        s3_key
                    )
                else:
                    with open(state_file, 'rb') as f:
                        self.s3_client.put_object(
                            Bucket=self.s3_bucket,
                            Key=s3_key,
                            Body=f.read()
                        )
                
                logger.info(f"State backed up to S3: s3://{self.s3_bucket}/{s3_key}")
                
                # Set lifecycle policy for compliance retention
                self._ensure_lifecycle_policy()
                
            except ClientError as e:
                logger.error(f"Failed to backup state to S3: {e}")
                # Don't fail the operation, local state is still saved
    
    def load_latest_state(self, key: str) -> Dict[Any, Any]:
        """
        Load most recent state for given key
        
        Args:
            key: State identifier
        
        Returns:
            State data dictionary, or empty dict if not found
        """
        # Find all state files for this key
        pattern = f"{key}_*.json*"
        files = sorted(self.local_path.glob(pattern), reverse=True)
        
        if not files:
            logger.warning(f"No local state found for key: {key}")
            # Try to restore from S3
            return self._restore_from_s3(key)
        
        # Load most recent
        state_file = files[0]
        
        try:
            if state_file.suffix == '.gz':
                with gzip.open(state_file, 'rt', encoding='utf-8') as f:
                    state_obj = json.load(f)
            else:
                with open(state_file, 'r') as f:
                    state_obj = json.load(f)
            
            logger.debug(f"State loaded from: {state_file}")
            return state_obj.get("data", {})
            
        except Exception as e:
            logger.error(f"Failed to load state from {state_file}: {e}")
            return {}
    
    def _restore_from_s3(self, key: str) -> Dict[Any, Any]:
        """Restore state from S3 if local copy lost"""
        if not self.s3_client:
            return {}
        
        try:
            # List objects for this key
            response = self.s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=f"state/{key}/",
                MaxKeys=1
            )
            
            if 'Contents' not in response:
                return {}
            
            # Get most recent
            latest = sorted(response['Contents'], key=lambda x: x['LastModified'], reverse=True)[0]
            s3_key = latest['Key']
            
            # Download and parse
            obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            
            if s3_key.endswith('.gz'):
                content = gzip.decompress(obj['Body'].read()).decode('utf-8')
            else:
                content = obj['Body'].read().decode('utf-8')
            
            state_obj = json.loads(content)
            logger.info(f"State restored from S3: {s3_key}")
            
            return state_obj.get("data", {})
            
        except ClientError as e:
            logger.error(f"Failed to restore state from S3: {e}")
            return {}
    
    def list_states(self, key: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available states, optionally filtered by key"""
        pattern = f"{key}_*.json*" if key else "*.json*"
        files = sorted(self.local_path.glob(pattern), reverse=True)
        
        states = []
        for file in files:
            try:
                if file.suffix == '.gz':
                    with gzip.open(file, 'rt', encoding='utf-8') as f:
                        state_obj = json.load(f)
                else:
                    with open(file, 'r') as f:
                        state_obj = json.load(f)
                
                states.append({
                    "key": state_obj["key"],
                    "timestamp": state_obj["timestamp"],
                    "file": str(file),
                    "metadata": state_obj.get("metadata", {})
                })
            except Exception as e:
                logger.warning(f"Failed to parse state file {file}: {e}")
        
        return states
    
    def cleanup_old_states(self, days: int = 30):
        """Remove local state files older than specified days (S3 backup retained)"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        removed = 0
        
        for file in self.local_path.glob("*.json*"):
            if file.stat().st_mtime < cutoff.timestamp():
                file.unlink()
                removed += 1
                logger.debug(f"Removed old state: {file}")
        
        logger.info(f"Cleaned up {removed} old state files (older than {days} days)")
    
    def _ensure_lifecycle_policy(self):
        """Ensure S3 bucket has proper lifecycle policy for compliance retention"""
        if not self.s3_client:
            return
        
        try:
            lifecycle_config = {
                'Rules': [
                    {
                        'Id': 'fraud-state-retention',
                        'Status': 'Enabled',
                        'Prefix': 'state/',
                        'Transitions': [
                            {
                                'Days': 90,
                                'StorageClass': 'STANDARD_IA'  # Cheaper storage after 90 days
                            },
                            {
                                'Days': 365,
                                'StorageClass': 'GLACIER'  # Archive after 1 year
                            }
                        ],
                        'Expiration': {
                            'Days': self.retention_days  # Delete after 7 years
                        }
                    }
                ]
            }
            
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.s3_bucket,
                LifecycleConfiguration=lifecycle_config
            )
            
            logger.info(f"S3 lifecycle policy configured: {self.retention_days} days retention")
            
        except ClientError as e:
            logger.warning(f"Could not set lifecycle policy: {e}")


class KafkaStateManager(StateManager):
    """Specialized state manager for Kafka consumer offsets"""
    
    def save_offset(self, topic: str, partition: int, offset: int, metadata: Dict = None):
        """Save Kafka consumer offset"""
        key = f"kafka_offset_{topic}_p{partition}"
        data = {
            "topic": topic,
            "partition": partition,
            "offset": offset
        }
        self.save_state(key, data, metadata)
    
    def load_offset(self, topic: str, partition: int) -> Optional[int]:
        """Load last committed offset"""
        key = f"kafka_offset_{topic}_p{partition}"
        state = self.load_latest_state(key)
        return state.get("offset")
```

#### Step 2: Integrate with RPS Stream Processing

```python
# rps/src/state_manager.py (RPS-specific)
from pathlib import Path
import pathway as pw
from backend.app.utils.state_manager import StateManager

class RPSStateManager(StateManager):
    """State management for RPS real-time processing"""
    
    def __init__(self, local_path: str = "PState/rps", s3_bucket: str = None):
        super().__init__(local_path, s3_bucket)
        self.pathway_state_path = Path("MCPPState")
        self.pathway_state_path.mkdir(exist_ok=True, parents=True)
    
    def save_processing_checkpoint(
        self,
        stream_id: str,
        processed_count: int,
        last_transaction_id: str,
        risk_scores: Dict[str, float]
    ):
        """Save RPS processing checkpoint"""
        data = {
            "stream_id": stream_id,
            "processed_count": processed_count,
            "last_transaction_id": last_transaction_id,
            "risk_scores_summary": {
                "high_risk_count": sum(1 for s in risk_scores.values() if s >= 0.8),
                "medium_risk_count": sum(1 for s in risk_scores.values() if 0.5 <= s < 0.8),
                "low_risk_count": sum(1 for s in risk_scores.values() if s < 0.5),
            }
        }
        
        self.save_state(
            key=f"rps_checkpoint_{stream_id}",
            data=data,
            metadata={"service": "rps", "type": "checkpoint"}
        )
    
    def configure_pathway_persistence(self):
        """Configure Pathway's built-in persistence"""
        return pw.persistence.Config.simple_config(
            backend=pw.persistence.Backend.filesystem(str(self.pathway_state_path)),
            snapshot_interval_ms=60000,  # Snapshot every minute
        )
```

#### Step 3: Docker Compose Volume Configuration

```yaml
# docker-compose.yml
services:
  backend:
    volumes:
      - state_data:/app/PState
      - ./backend/logs:/app/logs
    environment:
      - STATE_S3_BUCKET=fraud-detection-state
      - STATE_RETENTION_DAYS=2555  # 7 years
  
  rps:
    volumes:
      - rps_state:/app/PState
      - mcp_state:/app/MCPPState
    environment:
      - STATE_S3_BUCKET=fraud-detection-state

volumes:
  state_data:
    driver: local
  rps_state:
    driver: local
  mcp_state:
    driver: local
```

#### Step 4: Create State Monitoring Script

```python
# scripts/monitor_state.py
#!/usr/bin/env python3
"""Monitor and report on state management health"""

from backend.app.utils.state_manager import StateManager
from datetime import datetime, timedelta
import sys

def check_state_health():
    """Check state management system health"""
    state_mgr = StateManager()
    
    # Check recent activity
    recent_states = [
        s for s in state_mgr.list_states()
        if datetime.fromisoformat(s["timestamp"]) > datetime.utcnow() - timedelta(hours=1)
    ]
    
    print(f"✅ State files in last hour: {len(recent_states)}")
    
    # Check S3 connectivity
    if state_mgr.s3_client:
        try:
            state_mgr.s3_client.head_bucket(Bucket=state_mgr.s3_bucket)
            print(f"✅ S3 backup accessible: {state_mgr.s3_bucket}")
        except Exception as e:
            print(f"❌ S3 backup failed: {e}")
            return 1
    else:
        print("⚠️  No S3 backup configured")
    
    # Check disk usage
    state_path = state_mgr.local_path
    total_size = sum(f.stat().st_size for f in state_path.glob("**/*") if f.is_file())
    print(f"📊 Local state size: {total_size / (1024**2):.2f} MB")
    
    return 0

if __name__ == "__main__":
    sys.exit(check_state_health())
```

#### Step 5: Update .gitignore

```gitignore
# Don't ignore state directories - keep structure
# persistence_test/  # REMOVE
# PState/            # REMOVE
# MCPPState/         # REMOVE

# Instead, ignore only data files while keeping structure
PState/**/*.json
PState/**/*.json.gz
MCPPState/**/*.json
MCPPState/**/*.json.gz
persistence_test/**/*.json

# Keep directory structure in git
!PState/.gitkeep
!PState/rps/.gitkeep
!MCPPState/.gitkeep
!persistence_test/.gitkeep

# Add example files for documentation
!PState/README.md
!MCPPState/README.md
```

#### Step 6: Create State Documentation

````markdown
# PState/README.md

## Persistent State Directory

This directory stores application state for disaster recovery and compliance.

### Structure

```
PState/
├── backend/              # Backend API state
│   ├── kafka_offset_*    # Kafka consumer offsets
│   └── session_*         # User session state
├── rps/                  # RPS streaming state
│   ├── rps_checkpoint_*  # Processing checkpoints
│   └── model_cache_*     # Model inference cache
└── compliance/           # Compliance data
    └── audit_trail_*     # Audit logs
```

### Retention

- **Local**: 30 days (configurable)
- **S3 Backup**: 7 years (compliance requirement)
- **Format**: Compressed JSON (.json.gz)

### Monitoring

Check state health:
```bash
python scripts/monitor_state.py
```
````

**Timeline**: 2 days  
**Priority**: P1 - Essential for production reliability

---

## 📋 Implementation Roadmap

### Week 1: Critical Security & Infrastructure
- **Days 1-2**: P0.1 - Secrets Management (Vault)
- **Days 3-4**: P0.2 - ML Model Versioning (DVC)

### Week 2: Observability & Database
- **Days 1-3**: P0.3 - Centralized Logging (ELK)
- **Day 4**: P1.1 - Database Migrations (Alembic)

### Week 3: State & Testing
- **Days 1-2**: P1.2 - State Management
- **Days 3-5**: Integration testing & documentation

---

## 🎯 Success Metrics

### P0 Fixes
- ✅ Zero hardcoded secrets in codebase
- ✅ All ML models versioned and reproducible
- ✅ 100% of production events logged to ELK
- ✅ Sub-500ms query times on Elasticsearch

### P1 Fixes
- ✅ Zero manual database changes in production
- ✅ State recovery time < 5 minutes
- ✅ 7-year compliance retention verified

---

## 📞 Support

For questions about these fixes:
- Security: Contact DevSecOps team
- ML Infrastructure: Contact ML Ops team
- Database: Contact DBA team

**Last Updated**: December 4, 2025
