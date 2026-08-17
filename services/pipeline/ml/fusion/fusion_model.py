import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
import joblib

def logit(x, eps=1e-9):
    x = np.clip(x, eps, 1 - eps)
    return np.log(x / (1 - x))

def train_fusion_model(
    features_path="data/processed/features.parquet",
    ml_probs_path="models/p_ml_predictions.parquet",
    anomaly_path="data/processed/anomaly_scores.parquet",
    evidence_path="data/processed/rule_evidence.parquet",
    save_path="models/fusion_model.pkl",
):
    print(" Loading datasets...")
    df_feat = pd.read_parquet(features_path)
    df_ml = pd.read_parquet(ml_probs_path)
    df_anom = pd.read_parquet(anomaly_path)
    df_evid = pd.read_parquet(evidence_path)
    print(" Merging all components for fusion training...")
    df = df_feat.merge(df_ml, on=["user_id", "snapshot_time"], how="left")
    df = df.merge(df_anom, on=["user_id", "snapshot_time"], how="left")
    df = df.merge(df_evid, on=["user_id", "snapshot_time"], how="left")
    df = df.fillna(0)
    p_ml = df["p_ml"]
    a = df["anomaly_score"]
    e = df["evidence"]
    y = df["is_fraud"].astype(int)
    X = pd.DataFrame({
        "logit_p_ml": logit(p_ml),
        "logit_anomaly": logit(a),
        "evidence": e
    })
    print(" Training fusion logistic regression...")
    fusion = LogisticRegression()
    fusion.fit(X, y)
    preds = fusion.predict_proba(X)[:, 1]
    auc = roc_auc_score(y, preds)
    print(f"Fusion Model AUC: {auc:.4f}")
    print("Model coefficients:", fusion.coef_)
    print("Model intercept:", fusion.intercept_)
    joblib.dump(fusion, save_path)
    print(f"Saved fusion model → {save_path}")
    return fusion

