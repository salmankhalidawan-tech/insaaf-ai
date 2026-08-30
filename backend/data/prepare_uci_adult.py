"""
Download and prepare the UCI Adult Income (Census Income) dataset for
validation against the Insaaf AI bias-audit pipeline.

Source : https://archive.ics.uci.edu/dataset/2/adult
License: CC BY 4.0 (UCI Machine Learning Repository)

Usage:
    python prepare_uci_adult.py            # default: 2000 rows, seed 42
    python prepare_uci_adult.py --rows 5000 --seed 7
"""

import argparse
import os
import sys

import pandas as pd

URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"

COLUMNS = [
    "age", "workclass", "fnlwgt", "education", "education_num",
    "marital_status", "occupation", "relationship", "race", "sex",
    "capital_gain", "capital_loss", "hours_per_week", "native_country",
    "income",
]

KEEP = {
    "sex": "gender",
    "age": "age",
    "education": "education",
    "hours_per_week": "hours_per_week",
    "native_country": "native_country",
    "income": "loan_approved",
}

INCOME_MAP = {
    " >50K": "approved",
    " <=50K": "rejected",
    ">50K": "approved",
    "<=50K": "rejected",
}


def download_and_prepare(max_rows: int = 2000, seed: int = 42) -> pd.DataFrame:
    print(f"Downloading UCI Adult Income dataset from {URL} ...")
    raw = pd.read_csv(URL, header=None, names=COLUMNS, na_values=[" ?", " ?"], skipinitialspace=True)
    raw = raw.replace("?", pd.NA)
    print(f"  Raw shape: {raw.shape}")

    df = raw.dropna().reset_index(drop=True)
    print(f"  After dropping missing values: {df.shape}")

    df = df[list(KEEP.keys())].rename(columns=KEEP)
    df["loan_approved"] = df["loan_approved"].map(INCOME_MAP)
    df["gender"] = df["gender"].str.strip().str.lower()

    if len(df) > max_rows:
        df = df.sample(n=max_rows, random_state=seed).reset_index(drop=True)
        print(f"  Sampled {max_rows} rows (seed={seed})")

    print(f"  Final shape: {df.shape}")
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    out_path = args.output or os.path.join(os.path.dirname(__file__), "uci_adult_income.csv")
    df = download_and_prepare(max_rows=args.rows, seed=args.seed)
    df.to_csv(out_path, index=False)
    print(f"Saved to {out_path}")

    print("\nColumn value counts:")
    for col in df.columns:
        print(f"\n  {col}:")
        print(df[col].value_counts().head(10).to_string())
