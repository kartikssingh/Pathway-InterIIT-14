import pandas as pd
import numpy as np
from datetime import datetime
from dateutil import parser
import os
from tqdm import tqdm
import uuid 

UNIFIED_COLUMNS = [
    "transaction_id",
    "user_id",
    "timestamp",
    "amount",
    "currency",
    "txn_type",
    "counterparty_id",
    "country",
    "device_id",
    "is_fraud",
    "raw_source"
]

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def normalize_aml_data(path):
    """
    AML-Data by IBM
    """
    df = pd.read_csv(path)

    df_norm = pd.DataFrame({
        "transaction_id": df["transaction_id"].astype(str),
        "user_id": df["account_id"].astype(str),
        "timestamp": pd.to_datetime(df["timestamp"]),
        "amount": df["amount"].astype(float),
        "currency": df.get("currency", "USD"),
        "txn_type": df.get("type", "transfer"),
        "counterparty_id": df.get("counterparty", None),
        "country": df.get("country", None),
        "device_id": None,
        "is_fraud": df["is_laundering"].astype(int),
        "raw_source": "AML-Data"
    })

    return df_norm


import pandas as pd
import uuid

def normalize_amlsim(path):
    """
    Normalize AMLSim transactions_modified.csv into RPS schema.
    """
    df = pd.read_csv(path)

    df_norm = pd.DataFrame({
        "transaction_id": df["TX_ID"].astype(str),
        "user_id": df["SENDER_ACCOUNT_ID"].astype(str),   # treat account as user
        "timestamp": pd.to_datetime(df["TIMESTAMP"]),
        "amount": df["TX_AMOUNT"].astype(float),
        "currency": "USD",
        "txn_type": df["TX_TYPE"].astype(str),
        "counterparty_id": df["RECEIVER_ACCOUNT_ID"].astype(str),
        "country": None,
        "device_id": None,
        "is_fraud": df["IS_FRAUD"].astype(int),
        "raw_source": "AMLSim"
    })

    return df_norm


def normalize_saml_d(path):
    df = pd.read_csv(path)

    # Combine Date + Time
    df['timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])

    # Generate transaction_id
    df['transaction_id'] = [str(uuid.uuid4()) for _ in range(len(df))]

    # Clean the Is_laundering column safely
    df["Is_laundering"] = (
        df["Is_laundering"]
        .fillna(0)
        .replace("", 0)
        .replace(" ", 0)
        .astype(float)
        .astype(int)
    )

    df_norm = pd.DataFrame({
        "transaction_id": df["transaction_id"],
        "user_id": df["Sender_account"].astype(str),
        "timestamp": df["timestamp"],
        "amount": df["Amount"].astype(float),
        "currency": df["Payment_currency"].astype(str),
        "txn_type": df["Payment_type"].astype(str),
        "counterparty_id": df["Receiver_account"].astype(str),
        "country": df["Sender_bank_location"].astype(str),
        "device_id": None,
        "is_fraud": df["Is_laundering"].astype(int),
        "raw_source": "SAML-D"
    })

    return df_norm


def normalize_xgt(trans_path, account_map=None):
    """
    xGT AML dataset (very large)
    """
    df = pd.read_csv(trans_path)

    df_norm = pd.DataFrame({
        "transaction_id": df["TRANSACTION_ID"].astype(str),
        "user_id": df["SENDER_ID"].astype(str),
        "timestamp": pd.to_datetime(df["TIMESTAMP"]),
        "amount": df["AMOUNT"].astype(float),
        "currency": "USD",
        "txn_type": df["TRANSACTION_TYPE"].astype(str),
        "counterparty_id": df["RECEIVER_ID"].astype(str),
        "country": None,
        "device_id": None,
        "is_fraud": 0,  
        "raw_source": "xGT_AML"
    })

    return df_norm


def normalize_fraud_benchmark(path):
    """
    Amazon Fraud Benchmark (choose one dataset)
    """
    df = pd.read_csv(path)

    df_norm = pd.DataFrame({
        "transaction_id": df["id"].astype(str),
        "user_id": df["user"].astype(str),
        "timestamp": pd.to_datetime(df["timestamp"]),
        "amount": df["amount"].astype(float),
        "currency": "USD",
        "txn_type": "mixed",
        "counterparty_id": None,
        "country": None,
        "device_id": None,
        "is_fraud": df["fraud"].astype(int),
        "raw_source": "fraud_benchmark"
    })

    return df_norm


def normalize_financial_fraud(path):
    """
    Financial-Fraud-Dataset (corporate filings - used for media signals)
    """
    df = pd.read_csv(path)

    df_norm = pd.DataFrame({
        "transaction_id": df["FilingID"].astype(str),
        "user_id": df["CIK"].astype(str),
        "timestamp": pd.to_datetime(df["FilingDate"]),
        "amount": 0.0,
        "currency": None,
        "txn_type": "filing",
        "counterparty_id": None,
        "country": None,
        "device_id": None,
        "is_fraud": df["Fraud"].astype(int),
        "raw_source": "financial_fraud"
    })

    return df_norm

import os
import pandas as pd

def load_all_datasets(input_root, output_path="data/processed/unified.parquet"):
    
    all_frames = []

    print("Loading SAML-D...")
    saml_path = f"{input_root}/Anti_Money_Laundering_Transaction_Data_SAML-D/data.csv"
    if os.path.exists(saml_path):
        all_frames.append(normalize_saml_d(saml_path))
    else:
        print("SAML-D not found:", saml_path)

    print("Looking for AMLSim modified dataset...")
    amlsim_path = f"{input_root}/AMLSim/transactions.csv"  # <-- correct file
    if os.path.exists(amlsim_path):
        print("Loading AMLSim modified dataset...")
        all_frames.append(normalize_amlsim(amlsim_path))
    else:
        print("AMLSim modified file not found:", amlsim_path)

    print("Concatenating all datasets...")
    if len(all_frames) == 0:
        raise ValueError("No datasets loaded. Check paths.")

    df_all = pd.concat(all_frames, ignore_index=True)
    df_all = df_all.sort_values("timestamp")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df_all.to_parquet(output_path, index=False)

    print(f"Unified dataset created at: {output_path}")
    print(f"Total Rows: {len(df_all):,}")

    return df_all

