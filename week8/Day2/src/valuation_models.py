"""Property Valuation Models Module (Week 8 - Day 2).

Implements:
- Task 1: Baseline Models
  * Naive Mean / Median Regressor
  * Linear Regression
  * Ridge Regression
  * Lasso Regression
- Task 2: Advanced Gradient Boosted & Ensemble Models
  * Random Forest Regressor
  * XGBoost Regressor
  * LightGBM Regressor
  * CatBoost Regressor
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

BASE_DIR = Path(__file__).resolve().parent.parent
DAY1_DIR = BASE_DIR.parent / "Day1"
PROC_DIR = DAY1_DIR / "data" / "processed"
DAY1_MODEL_DIR = DAY1_DIR / "models"
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# Non-feature leakage columns
LEAKAGE_COLS = [
    "price_pkr", "price_pkr_normalized", "raw_price_str", "price_per_marla",
    "property_id", "listing_date", "plot_size_raw", "covered_area_raw",
    "area_society", "amenities"
]


def load_partitioned_data() -> Tuple[np.ndarray, pd.Series, np.ndarray, pd.Series, np.ndarray, pd.Series, pd.DataFrame, pd.DataFrame, pd.DataFrame, Any]:
    """Loads train, validation, and test datasets and transforms them using the fitted preprocessor."""
    train_df = pd.read_csv(PROC_DIR / "properties_train.csv")
    val_df = pd.read_csv(PROC_DIR / "properties_val.csv")
    test_df = pd.read_csv(PROC_DIR / "properties_test.csv")

    preprocessor = joblib.load(DAY1_MODEL_DIR / "property_preprocessor.joblib")

    X_train_raw = train_df.drop(columns=LEAKAGE_COLS, errors="ignore")
    y_train = train_df["price_pkr"]

    X_val_raw = val_df.drop(columns=LEAKAGE_COLS, errors="ignore")
    y_val = val_df["price_pkr"]

    X_test_raw = test_df.drop(columns=LEAKAGE_COLS, errors="ignore")
    y_test = test_df["price_pkr"]

    # Target transform: log1p to stabilize variance
    y_train_log = np.log1p(y_train)
    y_val_log = np.log1p(y_val)
    y_test_log = np.log1p(y_test)

    # Transform features
    X_train = preprocessor.transform(X_train_raw)
    X_val = preprocessor.transform(X_val_raw)
    X_test = preprocessor.transform(X_test_raw)

    return (
        X_train, y_train, y_train_log,
        X_val, y_val, y_val_log,
        X_test, y_test, y_test_log,
        train_df, val_df, test_df,
        preprocessor
    )


def get_all_models() -> Dict[str, Any]:
    """Instantiates baseline and advanced regression models."""
    return {
        # Task 1: Baseline Models
        "Median Baseline": DummyRegressor(strategy="median"),
        "Mean Baseline": DummyRegressor(strategy="mean"),
        "Linear Regression": LinearRegression(),
        "Ridge Regression": Ridge(alpha=10.0, random_state=42),
        "Lasso Regression": Lasso(alpha=0.001, max_iter=2000, random_state=42),

        # Task 2: Advanced Machine Learning Models
        "Random Forest": RandomForestRegressor(
            n_estimators=150, max_depth=16, min_samples_split=4, random_state=42, n_jobs=-1
        ),
        "XGBoost": XGBRegressor(
            n_estimators=200, learning_rate=0.06, max_depth=6, subsample=0.85,
            colsample_bytree=0.85, random_state=42, n_jobs=-1
        ),
        "LightGBM": LGBMRegressor(
            n_estimators=200, learning_rate=0.06, num_leaves=31, max_depth=7,
            subsample=0.85, colsample_bytree=0.85, random_state=42, n_jobs=-1, verbose=-1
        ),
        "CatBoost": CatBoostRegressor(
            iterations=250, learning_rate=0.06, depth=6, random_seed=42, verbose=0
        ),
    }


def compute_metrics(y_true_pkr: np.ndarray, y_pred_pkr: np.ndarray) -> Dict[str, float]:
    """Computes all required regression metrics on native PKR scale."""
    mae = mean_absolute_error(y_true_pkr, y_pred_pkr)
    rmse = np.sqrt(mean_squared_error(y_true_pkr, y_pred_pkr))
    r2 = r2_score(y_true_pkr, y_pred_pkr)
    mape = mean_absolute_percentage_error(y_true_pkr, y_pred_pkr) * 100.0

    return {
        "MAE_PKR": float(mae),
        "RMSE_PKR": float(rmse),
        "R2": float(r2),
        "MAPE_pct": float(mape),
    }


def train_and_evaluate_all_models() -> Tuple[pd.DataFrame, Dict[str, Any], Dict[str, np.ndarray], pd.DataFrame]:
    """Trains all 9 baseline and advanced models, evaluates on validation and test sets,
    and returns a structured comparison table, trained models, test predictions, and test dataframe.
    """
    (
        X_train, y_train, y_train_log,
        X_val, y_val, y_val_log,
        X_test, y_test, y_test_log,
        train_df, val_df, test_df,
        preprocessor
    ) = load_partitioned_data()

    models = get_all_models()
    records = []
    trained_models = {}
    test_predictions = {}

    print(f"Loaded datasets -> Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")
    print("Beginning model training and evaluation...\n")

    for name, model in models.items():
        t0 = time.time()
        # Train on log target for regression models, direct for dummy baseline
        if isinstance(model, DummyRegressor):
            model.fit(X_train, y_train)
            pred_val = model.predict(X_val)
            pred_test = model.predict(X_test)
        else:
            model.fit(X_train, y_train_log)
            pred_val_log = model.predict(X_val)
            pred_test_log = model.predict(X_test)
            pred_val = np.expm1(pred_val_log)
            pred_test = np.expm1(pred_test_log)

        train_time = time.time() - t0
        trained_models[name] = model
        test_predictions[name] = pred_test

        # Compute metrics on test set
        val_metrics = compute_metrics(y_val.values, pred_val)
        test_metrics = compute_metrics(y_test.values, pred_test)

        records.append({
            "Model": name,
            "Type": "Baseline" if "Baseline" in name or "Linear" in name or "Ridge" in name or "Lasso" in name else "Advanced Ensemble",
            "Val_R2": round(val_metrics["R2"], 4),
            "Val_MAE_PKR": round(val_metrics["MAE_PKR"]),
            "Val_MAPE_%": round(val_metrics["MAPE_pct"], 2),
            "Test_R2": round(test_metrics["R2"], 4),
            "Test_MAE_PKR": round(test_metrics["MAE_PKR"]),
            "Test_RMSE_PKR": round(test_metrics["RMSE_PKR"]),
            "Test_MAPE_%": round(test_metrics["MAPE_pct"], 2),
            "Train_Time_s": round(train_time, 2),
        })

        print(f"  [{name}] -> Test R2: {test_metrics['R2']:.4f} | Test MAE: {test_metrics['MAE_PKR']/1e5:.2f} Lac PKR | MAPE: {test_metrics['MAPE_pct']:.2f}% ({train_time:.2f}s)")

    results_df = pd.DataFrame(records).sort_values(by="Test_R2", ascending=False).reset_index(drop=True)
    return results_df, trained_models, test_predictions, test_df


if __name__ == "__main__":
    results_df, _, _, _ = train_and_evaluate_all_models()
    print("\n" + "=" * 95)
    print("MODEL COMPARISON TABLE (TEST SET EVALUATION)")
    print("=" * 95)
    print(results_df.to_string(index=False))
    results_path = BASE_DIR / "reports" / "model_comparison_results.csv"
    results_df.to_csv(results_path, index=False)
    print(f"\nSaved comparison results to: {results_path}")
