import pandas as pd
import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_recall_curve
)
from sklearn.model_selection import train_test_split
from catboost import CatBoostClassifier
import joblib
import json

FEATURE_BLACKLIST = ["user_id", "snapshot_time", "is_fraud"]


def compute_optimal_thresholds(y_true, y_score):
    precision, recall, thresholds = precision_recall_curve(y_true, y_score)
    precision = precision[:-1]
    recall = recall[:-1]
    thresholds = thresholds
    f1_scores = 2 * precision * recall / (precision + recall + 1e-9)
    best_f1_thresh = thresholds[np.argmax(f1_scores)]
    high_precision_idx = np.where(precision >= 0.95)[0]
    if len(high_precision_idx) > 0:
        prec95_thresh = thresholds[high_precision_idx[0]]
    else:
        prec95_thresh = float(best_f1_thresh)
    high_recall_idx = np.where(recall >= 0.80)[0]
    if len(high_recall_idx) > 0:
        rec80_thresh = thresholds[high_recall_idx[-1]]
    else:
        rec80_thresh = float(best_f1_thresh)

    return {
        "best_f1": float(best_f1_thresh),
        "precision_95": float(prec95_thresh),
        "recall_80": float(rec80_thresh)
    }


def train_supervised_model(
    feature_path="data/processed/features.parquet",
    model_path="models/p_ml_model.pkl",
    threshold_path="models/p_ml_thresholds.json"
):

    print("Loading dataset...")
    df = pd.read_parquet(feature_path)
    df = df.sort_values("snapshot_time")   
    y = df["is_fraud"].astype(int)
    X = df.drop(columns=FEATURE_BLACKLIST).apply(pd.to_numeric, errors="coerce").fillna(0)
    split = int(len(df) * 0.8)
    X_train, y_train = X.iloc[:split], y.iloc[:split]
    X_test, y_test = X.iloc[split:], y.iloc[split:]
    print(f"Training size: {len(X_train)}, Fraud count: {y_train.sum()}")
    print(f"Test size:     {len(X_test)}, Fraud count: {y_test.sum()}")
    imbalance_ratio = (len(y_train) - y_train.sum()) / max(1, y_train.sum())
    print(f"Imbalance ratio: {imbalance_ratio:.2f}")
    print("Training CatBoost (best for tiny fraud samples)...")
    model = CatBoostClassifier(
        iterations=1500,
        learning_rate=0.02,
        depth=8,
        loss_function="Logloss",
        eval_metric="AUC",
        class_weights=[1.0, imbalance_ratio],   
        random_seed=42,
        verbose=200
    )
    model.fit(
        X_train,
        y_train,
        eval_set=(X_test, y_test),
        verbose=False
    )
    y_score = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_score)
    pr_auc = average_precision_score(y_test, y_score)
    print(f"ROC-AUC:  {auc:.4f}")
    print(f"PR-AUC:   {pr_auc:.4f}")
    thresholds = compute_optimal_thresholds(y_test, y_score)
    print("Optimal thresholds:", thresholds)
    with open(threshold_path, "w") as f:
        json.dump(thresholds, f, indent=4)
    joblib.dump(model, model_path)
    print(f"Saved CatBoost model → {model_path}")
    print(f"Saved thresholds → {threshold_path}")

    return model, thresholds



if __name__ == "__main__":
    train_supervised_model()

