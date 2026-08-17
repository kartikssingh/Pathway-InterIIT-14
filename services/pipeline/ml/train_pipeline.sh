set -e

echo "==============================="
echo " STEP 0 — Activate Environment "
echo "==============================="
source ../venv/bin/activate

mkdir -p data/processed
mkdir -p models
mkdir -p logs

echo "==============================="
echo " STEP 1 — Load & Normalize Data"
echo "==============================="
python - << 'EOF'
from preprocessing.load_datasets import load_all_datasets
df = load_all_datasets("../datasets/rps_training")
df.to_parquet("data/processed/normalized.parquet", index=False)
print("Normalized dataset saved.")
EOF


echo "==============================="
echo " STEP 2 — Feature Engineering "
echo "==============================="
python - << 'EOF'
import pandas as pd
from features.generate_features import generate_rolling_features
df = pd.read_parquet("data/processed/unified.parquet")
features = generate_rolling_features(df, "data/processed/features.parquet")
print("Feature file saved.")
EOF


echo "==============================="
echo " STEP 3 — Train ML Model p_ml "
echo "==============================="
python - << 'EOF'
from models.train_supervised import train_supervised_model_best

model = train_supervised_model_best(
    "data/processed/features.parquet",
    "models/p_ml_model.pkl",
    "models/p_ml_thresholds.json"
)
print("Trained ML model saved.")
EOF


echo "==============================="
echo " STEP 4 — Train Anomaly Model "
echo "==============================="
python - << 'EOF'
from models.train_anomaly import train_anomaly_model

iso, scaler, anomaly_scores = train_anomaly_model(
    "data/processed/features.parquet",
    "models/anomaly_model.pkl",
    "models/anomaly_scaler.pkl"
)
#df_anom.to_parquet("data/processed/anomaly_scores.parquet", index=False)
print("Anomaly model saved.")
EOF


echo "==============================="
echo " STEP 5 — Rule Engine & Evidence"
echo "==============================="

python - << 'EOF'
from rules.compute_prior import compute_prior
pi = compute_prior("data/processed/features.parquet")
print("Prior:", pi)
EOF

python - << 'EOF'
import pandas as pd
from rules.rule_engine import evaluate_rules

df = pd.read_parquet("data/processed/features.parquet")

rows = []
for idx, row in df.iterrows():
    r = evaluate_rules(row)
    r["user_id"] = row["user_id"]
    r["snapshot_time"] = row["snapshot_time"]
    rows.append(r)

df_rules = pd.DataFrame(rows)
df_rules.to_parquet("data/processed/rule_hits.parquet", index=False)
print("Rule hits saved.")
EOF

# 5.3 Likelihood Ratios
python - << 'EOF'
from rules.compute_likelihood_ratios import compute_likelihood_ratios
import json

lr = compute_likelihood_ratios(
    "data/processed/rule_hits.parquet",
    "data/processed/features.parquet",
)
with open("models/lr_dict.json", "w") as f:
    json.dump(lr, f, indent=4)

print("Likelihood ratios saved.")
EOF

# 5.4 Evidence
python - << 'EOF'
import pandas as pd
import json
from rules.evidence import compute_evidence
from rules.compute_prior import compute_prior

pi = compute_prior("data/processed/features.parquet")

with open("models/lr_dict.json") as f:
    lr_dict = json.load(f)

df_rules = pd.read_parquet("data/processed/rule_hits.parquet")

rows = []
rule_cols = [c for c in df_rules.columns if c not in ("user_id","snapshot_time")]

for i, row in df_rules.iterrows():
    rule_hits = {col: float(row[col]) for col in rule_cols}
    e = compute_evidence(rule_hits, lr_dict, pi)
    rows.append({
        "user_id": row["user_id"],
        "snapshot_time": row["snapshot_time"],
        "evidence": e
    })

pd.DataFrame(rows).to_parquet("data/processed/rule_evidence.parquet", index=False)
print("Evidence saved.")
EOF



echo " STEP 6 — Train Fusion Layer (RPS)"

python - << 'EOF'
from fusion.fusion_model import train_fusion_model
train_fusion_model(
    "data/processed/features.parquet",
    "models/p_ml_predictions.parquet",
    "data/processed/anomaly_scores.parquet",
    "data/processed/rule_evidence.parquet",
    "models/fusion_model.pkl"
)
print("Fusion model saved.")
EOF



echo " STEP 6.5 — Save Training Feature List"

python - << 'EOF'
import joblib, json

model = joblib.load("models/p_ml_model.pkl")
features = list(model.feature_name_)

with open("models/training_features.json", "w") as f:
    json.dump(features, f, indent=4)

print("Saved training feature list.")
EOF



echo " STEP 7 — Start FastAPI Server"

echo "Run this command manually in a new terminal:"
echo "---------------------------------------------"
echo "python -m uvicorn service.api:app --reload --port 8000"
echo "---------------------------------------------"



echo " TEST CURL COMMAND"

echo ""
echo "curl -X POST \"http://127.0.0.1:8000/score\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"features\": { \"total_amount_1h\": 1200, \"txn_count_1h\": 3, \"unique_cp_1h\": 1, \"avg_amount_1h\": 400, \"max_amount_1h\": 900, \"min_amount_1h\": 100, \"total_amount_24h\": 4500, \"txn_count_24h\": 7, \"unique_cp_24h\": 4, \"avg_amount_24h\": 650, \"max_amount_24h\": 2000, \"min_amount_24h\": 50, \"total_amount_7d\": 15000, \"txn_count_7d\": 20, \"unique_cp_7d\": 5, \"avg_amount_7d\": 750, \"max_amount_7d\": 5000, \"min_amount_7d\": 50, \"total_amount_30d\": 42000, \"txn_count_30d\": 90, \"unique_cp_30d\": 15, \"avg_amount_30d\": 466, \"max_amount_30d\": 8000, \"min_amount_30d\": 20, \"incoming_outgoing_ratio_7d\": 1.2 }}'"
echo ""

