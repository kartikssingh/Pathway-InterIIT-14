import numpy as np
import joblib

def logit(x, eps=1e-9):
    x = np.clip(x, eps, 1 - eps)
    return np.log(x / (1 - x))

def score_rps(p_ml, anomaly, evidence):
    fusion = joblib.load("models/fusion_model.pkl")

    X = np.array([
        logit(p_ml),
        logit(anomaly),
        evidence
    ]).reshape(1, -1)

    prob = fusion.predict_proba(X)[0][1]
    return prob

