import numpy as np

def rule_high_velocity_1h(row, threshold=5):
    return 1 if row["txn_count_1h"] >= threshold else 0

def rule_large_txn_1h(row, threshold=3000):
    return 1 if row["max_amount_1h"] >= threshold else 0

def rule_high_unique_cp_1h(row, threshold=3):
    return 1 if row["unique_cp_1h"] >= threshold else 0

def rule_structuring_small_then_large_24h(row):
    small = row["txn_count_24h"] >= 6 and row["avg_amount_24h"] < 800
    large = row["max_amount_24h"] > 5000
    return 1 if small and large else 0

def rule_high_volume_24h(row, threshold=20000):
    return 1 if row["total_amount_24h"] >= threshold else 0

def rule_rapid_counterparty_increase_24h(row, threshold=5):
    return 1 if row["unique_cp_24h"] >= threshold else 0

def rule_high_velocity_7d(row, threshold=25):
    return 1 if row["txn_count_7d"] >= threshold else 0

def rule_high_volume_7d(row, threshold=50000):
    return 1 if row["total_amount_7d"] >= threshold else 0

def rule_cp_spike_7d(row, threshold=10):
    return 1 if row["unique_cp_7d"] >= threshold else 0

def rule_incoming_outgoing_ratio(row):
    ratio = row["incoming_outgoing_ratio_7d"]
    return 1 if ratio >= 3 or ratio == 0 else 0

def rule_rapid_growth_between_windows(row):
    if row["txn_count_7d"] == 0:
        return 0
    ratio = row["txn_count_1h"] / row["txn_count_7d"]
    return 1 if ratio >= 0.5 else 0

def rule_unusual_average_amount(row):
    avg7 = row["avg_amount_7d"]
    max7 = row["max_amount_7d"]
    return 1 if avg7 > 0 and (max7 / avg7) >= 10 else 0

RULE_FEATURES = [
    "total_amount_1h", "txn_count_1h", "unique_cp_1h", "avg_amount_1h",
    "max_amount_1h", "min_amount_1h",
    "total_amount_24h", "txn_count_24h", "unique_cp_24h", "avg_amount_24h",
    "max_amount_24h", "min_amount_24h",
    "total_amount_7d", "txn_count_7d", "unique_cp_7d", "avg_amount_7d",
    "max_amount_7d", "min_amount_7d",
    "total_amount_30d", "txn_count_30d", "unique_cp_30d", "avg_amount_30d",
    "max_amount_30d", "min_amount_30d",
    "incoming_outgoing_ratio_7d"
]

def evaluate_rules(row):
    safe_row = {}
    for k in RULE_FEATURES:
        safe_row[k] = float(row[k]) if k in row else 0.0

    
    return {
        "high_velocity_1h": safe_row["txn_count_1h"] >= 5,
        "large_txn_1h": safe_row["max_amount_1h"] >= 3000,
        "high_unique_cp_1h": safe_row["unique_cp_1h"] >= 3,

        "structuring_small_then_large_24h": (
            safe_row["txn_count_24h"] >= 6 and
            safe_row["avg_amount_24h"] < 800 and
            safe_row["max_amount_24h"] > 5000
        ),

        "high_volume_24h": safe_row["total_amount_24h"] >= 20000,
        "rapid_counterparty_increase_24h": safe_row["unique_cp_24h"] >= 5,

        "high_velocity_7d": safe_row["txn_count_7d"] >= 25,
        "high_volume_7d": safe_row["total_amount_7d"] >= 50000,
        "cp_spike_7d": safe_row["unique_cp_7d"] >= 10,

        "incoming_outgoing_anomaly": (
            safe_row["incoming_outgoing_ratio_7d"] >= 3 or
            safe_row["incoming_outgoing_ratio_7d"] == 0
        ),

        "rapid_growth_between_windows": (
            safe_row["txn_count_7d"] > 0 and
            (safe_row["txn_count_1h"] / safe_row["txn_count_7d"]) >= 0.5
        ),

        "unusual_average_amount": (
            safe_row["avg_amount_7d"] > 0 and
            (safe_row["max_amount_7d"] / safe_row["avg_amount_7d"]) >= 10
        )
    }

