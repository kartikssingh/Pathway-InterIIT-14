import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import MinMaxScaler
import joblib

FEATURE_BLACKLIST = ["user_id", "snapshot_time", "is_fraud"]

def train_anomaly_model(
    feature_path="data/processed/features.parquet",
    model_path="models/anomaly_model.pkl",
    scaler_path="models/anomaly_scaler.pkl"
):
    df = pd.read_parquet(feature_path)
    X = df.drop(columns=FEATURE_BLACKLIST)
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0)

    iso = IsolationForest(
        n_estimators=500,
        contamination=0.01,       
        max_samples="auto",
        random_state=42,
        n_jobs=-1
    )

    iso.fit(X)
    raw_scores = iso.decision_function(X)
    scaler = MinMaxScaler()
    norm_scores = scaler.fit_transform(raw_scores.reshape(-1, 1))
    df["anomaly_score"] = norm_scores
    joblib.dump(iso, model_path)
    joblib.dump(scaler, scaler_path)
    print(f"Saved anomaly model to: {model_path}")
    print(f"Saved scaler to: {scaler_path}")
    print(df["anomaly_score"].describe())

    return iso, scaler, df[["user_id", "snapshot_time", "anomaly_score"]]

