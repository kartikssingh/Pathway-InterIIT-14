import pandas as pd
import numpy as np
from tqdm import tqdm

WINDOWS = {
    "1h":  pd.Timedelta(hours=1),
    "24h": pd.Timedelta(hours=24),
    "7d":  pd.Timedelta(days=7),
    "30d": pd.Timedelta(days=30)
}
def generate_rolling_features(df, output_path="data/processed/features.parquet"):
    df = df.sort_values(["user_id", "timestamp"])
    user_groups = df.groupby("user_id")
    all_feature_rows = []
    for user_id, group in tqdm(user_groups, desc="Users"):
        group = group.sort_values("timestamp")
        for idx, row in group.iterrows():
            ts = row["timestamp"]
            feature_row = {
                "user_id": user_id,
                "snapshot_time": ts,
                "is_fraud": row["is_fraud"],  
            }
            for wname, wdelta in WINDOWS.items():
                w_start = ts - wdelta
                window_df = group[(group["timestamp"] > w_start) & (group["timestamp"] <= ts)]
                feature_row[f"total_amount_{wname}"] = window_df["amount"].sum()
                feature_row[f"txn_count_{wname}"] = len(window_df)
                feature_row[f"unique_cp_{wname}"] = window_df["counterparty_id"].nunique()
                feature_row[f"avg_amount_{wname}"] = (
                    window_df["amount"].mean() if len(window_df) > 0 else 0
                )
                feature_row[f"max_amount_{wname}"] = (
                    window_df["amount"].max() if len(window_df) > 0 else 0
                )
                feature_row[f"min_amount_{wname}"] = (
                    window_df["amount"].min() if len(window_df) > 0 else 0
                )
            w7 = group[(group["timestamp"] > ts - pd.Timedelta(days=7)) & (group["timestamp"] <= ts)]
            incoming = w7[w7["amount"] < 0].shape[0]
            outgoing = w7[w7["amount"] > 0].shape[0]
            feature_row["incoming_outgoing_ratio_7d"] = (
                incoming / outgoing if outgoing != 0 else 0
            )
            all_feature_rows.append(feature_row)  
    feature_df = pd.DataFrame(all_feature_rows)
    feature_df.to_parquet(output_path, index=False)
    print(f"Feature engineering completed. Saved to: {output_path}")
    print(f"Rows: {len(feature_df):,}")

    return feature_df

