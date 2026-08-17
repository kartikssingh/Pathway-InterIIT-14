import pandas as pd
import numpy as np
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_recall_curve
)
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
import joblib
import json

from catboost import CatBoostClassifier
import lightgbm as lgb
from xgboost import XGBClassifier

FEATURE_BLACKLIST = ["user_id", "snapshot_time", "is_fraud"]



def compute_optimal_thresholds(y_true, y_score):
    precision, recall, thresholds = precision_recall_curve(y_true, y_score)

    precision = precision[:-1]
    recall = recall[:-1]

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



def train_supervised_model_best(
    feature_path="data/processed/features.parquet",
    model_path="models/p_ml_model.pkl",
    threshold_path="models/p_ml_thresholds.json"
):
    print("Loading dataset...")
    df = pd.read_parquet(feature_path)
    df = df.sort_values("snapshot_time")

    y = df["is_fraud"].astype(int)
    X = df.drop(columns=FEATURE_BLACKLIST)
    X = X.apply(pd.to_numeric, errors="coerce").fillna(0)

    
    split = int(len(df) * 0.8)
    X_train, y_train = X.iloc[:split], y.iloc[:split]
    X_test, y_test = X.iloc[split:], y.iloc[split:]

    print(f"Train size: {len(X_train)}, Frauds: {y_train.sum()}")
    print(f"Test size:  {len(X_test)}, Frauds: {y_test.sum()}")

    imbalance_ratio = (len(y_train) - y_train.sum()) / max(1, y_train.sum())
    print(f"Imbalance ratio: {imbalance_ratio:.2f}")

    
    
    

    print("Training CatBoost...")
    cat = CatBoostClassifier(
        iterations=1500,
        depth=8,
        learning_rate=0.03,
        class_weights=[1.0, imbalance_ratio],
        random_seed=42,
        verbose=False
    )
    cat.fit(X_train, y_train, eval_set=(X_test, y_test), verbose=False)
    p_cat_train = cat.predict_proba(X_train)[:, 1]
    p_cat_test = cat.predict_proba(X_test)[:, 1]

    
    
    

    print("Training LightGBM...")
    lgbm = lgb.LGBMClassifier(
        n_estimators=600,
        learning_rate=0.03,
        num_leaves=128,
        scale_pos_weight=imbalance_ratio,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42
    )
    lgbm.fit(X_train, y_train)
    p_lgb_train = lgbm.predict_proba(X_train)[:, 1]
    p_lgb_test = lgbm.predict_proba(X_test)[:, 1]

    
    
    

    print("Training XGBoost...")
    xgb = XGBClassifier(
        n_estimators=700,
        learning_rate=0.03,
        max_depth=8,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=imbalance_ratio,
        eval_metric="logloss",
        random_state=42
    )
    xgb.fit(X_train, y_train)
    p_xgb_train = xgb.predict_proba(X_train)[:, 1]
    p_xgb_test = xgb.predict_proba(X_test)[:, 1]

    
    
    

    print("Training Meta-Model...")
    meta_X_train = np.vstack([p_cat_train, p_lgb_train, p_xgb_train]).T
    meta_X_test  = np.vstack([p_cat_test, p_lgb_test, p_xgb_test]).T

    scaler = StandardScaler()
    meta_X_train = scaler.fit_transform(meta_X_train)
    meta_X_test = scaler.transform(meta_X_test)

    meta = LogisticRegression(max_iter=500)
    meta.fit(meta_X_train, y_train)

    
    y_score = meta.predict_proba(meta_X_test)[:, 1]

    
    
    

    auc = roc_auc_score(y_test, y_score)
    pr_auc = average_precision_score(y_test, y_score)

    print(f"ROC-AUC (Ensemble): {auc:.4f}")
    print(f"PR-AUC (Ensemble):  {pr_auc:.4f}")

    
    
    

    thresholds = compute_optimal_thresholds(y_test, y_score)
    print("Optimal thresholds:", thresholds)

    with open(threshold_path, "w") as f:
        json.dump(thresholds, f, indent=4)

    
    
    

    final_ensemble = {
        "catboost": cat,
        "lightgbm": lgbm,
        "xgboost": xgb,
        "meta": meta,
        "scaler": scaler,
        "feature_list": list(X.columns)
    }

    joblib.dump(final_ensemble, model_path)
    print(f"Final ensemble saved → {model_path}")

    return final_ensemble, thresholds



if __name__ == "__main__":
    train_supervised_model_best()

