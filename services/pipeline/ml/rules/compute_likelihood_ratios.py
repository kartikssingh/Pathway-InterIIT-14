import pandas as pd
from collections import defaultdict

def compute_likelihood_ratios(rule_results_path, features_path):
    df_rules = pd.read_parquet(rule_results_path)
    df_feat = pd.read_parquet(features_path)

    
    df = df_rules.merge(df_feat[["user_id", "snapshot_time", "is_fraud"]],
                        on=["user_id", "snapshot_time"],
                        how="left")

    lr_dict = {}

    print("Computing LR for each rule...")

    for rule in [c for c in df.columns if c not in ["user_id", "snapshot_time", "is_fraud"]]:
        rule_df = df[[rule, "is_fraud"]]
        num_rule_fraud = len(rule_df[(rule_df[rule] == 1) & (rule_df["is_fraud"] == 1)])
        num_fraud = len(rule_df[rule_df["is_fraud"] == 1])
        p_rule_given_fraud = num_rule_fraud / num_fraud if num_fraud > 0 else 0.0001
        num_rule_legit = len(rule_df[(rule_df[rule] == 1) & (rule_df["is_fraud"] == 0)])
        num_legit = len(rule_df[rule_df["is_fraud"] == 0])
        p_rule_given_legit = num_rule_legit / num_legit if num_legit > 0 else 0.0001
        LR = p_rule_given_fraud / p_rule_given_legit if p_rule_given_legit > 0 else 1.0
        lr_dict[rule] = LR
        print(f"Rule: {rule} | LR = {LR:.4f}")

    return lr_dict

