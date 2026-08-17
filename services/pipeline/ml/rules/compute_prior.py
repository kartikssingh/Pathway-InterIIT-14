import pandas as pd

def compute_prior(feature_path="data/processed/features.parquet"):
    df = pd.read_parquet(feature_path)

    fraud_count = df["is_fraud"].sum()
    total = len(df)

    pi = fraud_count / total

    print(f"Fraud count: {fraud_count}")
    print(f"Total count: {total}")
    print(f"Prior (pi): {pi:.6f}")

    return pi

