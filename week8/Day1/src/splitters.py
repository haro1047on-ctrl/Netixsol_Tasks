"""Data Splitting and Partitioning Module.

Implements:
1. 70 / 15 / 15 Train / Validation / Test split for regression (Properties)
2. Stratified 70 / 15 / 15 split for classification (Leads) to preserve class balance
3. Parquet and CSV export to data/processed/
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple
import pandas as pd
from sklearn.model_selection import train_test_split

BASE_DIR = Path(__file__).resolve().parent.parent
PROC_DIR = BASE_DIR / "data" / "processed"


def split_properties_data(
    df: pd.DataFrame,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, any]]:
    """Splits cleaned property listings into Train (70%), Validation (15%), and Test (15%)."""
    # 70% Train, 30% Temp
    train_df, temp_df = train_test_split(df, test_size=0.30, random_state=random_state, shuffle=True)
    # Split Temp into 50% Val, 50% Test (15% and 15% overall)
    val_df, test_df = train_test_split(temp_df, test_size=0.50, random_state=random_state, shuffle=True)

    stats = {
        "total_rows": len(df),
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "train_pct": round(len(train_df) / len(df) * 100, 2),
        "val_pct": round(len(val_df) / len(df) * 100, 2),
        "test_pct": round(len(test_df) / len(df) * 100, 2),
        "train_median_price": float(train_df["price_pkr"].median()),
        "val_median_price": float(val_df["price_pkr"].median()),
        "test_median_price": float(test_df["price_pkr"].median()),
    }

    # Save to disk
    train_df.to_csv(PROC_DIR / "properties_train.csv", index=False)
    val_df.to_csv(PROC_DIR / "properties_val.csv", index=False)
    test_df.to_csv(PROC_DIR / "properties_test.csv", index=False)

    return train_df, val_df, test_df, stats


def split_leads_data(
    df: pd.DataFrame,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, any]]:
    """Splits CRM leads into Stratified Train (70%), Validation (15%), and Test (15%).
    Preserves exact positive conversion class ratio across all partitions.
    """
    y = df["converted_binary"]

    # Stratified 70% Train, 30% Temp
    train_df, temp_df = train_test_split(
        df, test_size=0.30, random_state=random_state, shuffle=True, stratify=y
    )

    y_temp = temp_df["converted_binary"]
    # Stratified 50% Val, 50% Test (15% and 15% overall)
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, random_state=random_state, shuffle=True, stratify=y_temp
    )

    stats = {
        "total_rows": len(df),
        "train_rows": len(train_df),
        "val_rows": len(val_df),
        "test_rows": len(test_df),
        "train_pct": round(len(train_df) / len(df) * 100, 2),
        "val_pct": round(len(val_df) / len(df) * 100, 2),
        "test_pct": round(len(test_df) / len(df) * 100, 2),
        "overall_conversion_rate": round(float(y.mean()) * 100, 2),
        "train_conversion_rate": round(float(train_df['converted_binary'].mean()) * 100, 2),
        "val_conversion_rate": round(float(val_df['converted_binary'].mean()) * 100, 2),
        "test_conversion_rate": round(float(test_df['converted_binary'].mean()) * 100, 2),
    }

    # Save to disk
    train_df.to_csv(PROC_DIR / "leads_train.csv", index=False)
    val_df.to_csv(PROC_DIR / "leads_val.csv", index=False)
    test_df.to_csv(PROC_DIR / "leads_test.csv", index=False)

    return train_df, val_df, test_df, stats


if __name__ == "__main__":
    print("--- Executing 70/15/15 Data Splitting ---")
    df_props = pd.read_csv(PROC_DIR / "cleaned_properties.csv")
    _, _, _, prop_stats = split_properties_data(df_props)
    print("Properties Split Statistics:")
    for k, v in prop_stats.items():
        print(f"  {k}: {v}")

    df_leads = pd.read_csv(PROC_DIR / "cleaned_leads.csv")
    _, _, _, lead_stats = split_leads_data(df_leads)
    print("\nLeads Stratified Split Statistics:")
    for k, v in lead_stats.items():
        print(f"  {k}: {v}")
