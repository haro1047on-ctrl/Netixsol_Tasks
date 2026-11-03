"""Hyperparameter Tuning (Optuna) and Experiment Tracking (MLflow).

Tunes top 2 models (CatBoost and LightGBM) using Optuna Bayesian Optimization.
Logs parameters, metrics, feature sets, training time, and model artifacts to MLflow.
Registers the winning model in the MLflow Model Registry.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Dict, Tuple
import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import optuna
import pandas as pd
from catboost import CatBoostRegressor
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error, mean_squared_error, r2_score

from valuation_models import compute_metrics, load_partitioned_data

# Suppress verbose Optuna logging
optuna.logging.set_verbosity(optuna.logging.WARNING)

BASE_DIR = Path(__file__).resolve().parent.parent
MLFLOW_DB_PATH = BASE_DIR / "mlflow.db"
MLFLOW_URI = f"sqlite:///{MLFLOW_DB_PATH.as_posix()}"
EXPERIMENT_NAME = "Week8_Property_Valuation"
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def setup_mlflow():
    """Initializes MLflow tracking URI and experiment."""
    mlflow.set_tracking_uri(MLFLOW_URI)
    experiment = mlflow.get_experiment_by_name(EXPERIMENT_NAME)
    if experiment is None:
        mlflow.create_experiment(EXPERIMENT_NAME)
    mlflow.set_experiment(EXPERIMENT_NAME)
    print(f"MLflow configured with URI: {MLFLOW_URI} | Experiment: {EXPERIMENT_NAME}")


def tune_lightgbm(
    X_train: np.ndarray, y_train_log: np.ndarray,
    X_val: np.ndarray, y_val_log: np.ndarray,
    y_val_pkr: np.ndarray,
    n_trials: int = 20
) -> Tuple[Dict[str, Any], LGBMRegressor]:
    """Tunes LightGBM hyperparameters with Optuna."""
    print(f"\n--- Running Optuna Tuning for LightGBM ({n_trials} trials) ---")

    def objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 150, 350),
            "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.12, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 20, 60),
            "max_depth": trial.suggest_int("max_depth", 4, 9),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 40),
            "subsample": trial.suggest_float("subsample", 0.70, 0.95),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.70, 0.95),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-3, 5.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-3, 5.0, log=True),
            "random_state": 42,
            "verbose": -1,
            "n_jobs": -1,
        }

        model = LGBMRegressor(**params)
        model.fit(X_train, y_train_log)
        preds_log = model.predict(X_val)
        preds_pkr = np.expm1(preds_log)
        val_rmse = np.sqrt(mean_squared_error(y_val_pkr, preds_pkr))
        return float(val_rmse)

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_params = study.best_params
    best_params.update({"random_state": 42, "verbose": -1, "n_jobs": -1})
    print(f"  LightGBM Best Trial RMSE: {study.best_value/1e5:.2f} Lac PKR")

    best_lgbm = LGBMRegressor(**best_params)
    best_lgbm.fit(X_train, y_train_log)
    return best_params, best_lgbm


def tune_catboost(
    X_train: np.ndarray, y_train_log: np.ndarray,
    X_val: np.ndarray, y_val_log: np.ndarray,
    y_val_pkr: np.ndarray,
    n_trials: int = 20
) -> Tuple[Dict[str, Any], CatBoostRegressor]:
    """Tunes CatBoost hyperparameters with Optuna."""
    print(f"\n--- Running Optuna Tuning for CatBoost ({n_trials} trials) ---")

    def objective(trial: optuna.Trial) -> float:
        params = {
            "iterations": trial.suggest_int("iterations", 180, 350),
            "learning_rate": trial.suggest_float("learning_rate", 0.03, 0.12, log=True),
            "depth": trial.suggest_int("depth", 4, 8),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 10.0),
            "random_seed": 42,
            "verbose": 0,
        }

        model = CatBoostRegressor(**params)
        model.fit(X_train, y_train_log)
        preds_log = model.predict(X_val)
        preds_pkr = np.expm1(preds_log)
        val_rmse = np.sqrt(mean_squared_error(y_val_pkr, preds_pkr))
        return float(val_rmse)

    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_params = study.best_params
    best_params.update({"random_seed": 42, "verbose": 0})
    print(f"  CatBoost Best Trial RMSE: {study.best_value/1e5:.2f} Lac PKR")

    best_cb = CatBoostRegressor(**best_params)
    best_cb.fit(X_train, y_train_log)
    return best_params, best_cb


def run_tuning_and_tracking():
    setup_mlflow()

    (
        X_train, y_train, y_train_log,
        X_val, y_val, y_val_log,
        X_test, y_test, y_test_log,
        train_df, val_df, test_df,
        preprocessor
    ) = load_partitioned_data()

    feature_names = [f"feat_{i}" for i in range(X_train.shape[1])]

    # 1. Tune LightGBM
    t0_lgbm = time.time()
    lgbm_params, tuned_lgbm = tune_lightgbm(X_train, y_train_log, X_val, y_val_log, y_val.values, n_trials=20)
    train_time_lgbm = time.time() - t0_lgbm

    pred_test_lgbm = np.expm1(tuned_lgbm.predict(X_test))
    lgbm_metrics = compute_metrics(y_test.values, pred_test_lgbm)

    # Log LightGBM Run in MLflow
    with mlflow.start_run(run_name="Tuned_LightGBM_Valuation") as run_lgbm:
        mlflow.log_params(lgbm_params)
        mlflow.log_metric("test_mae_pkr", lgbm_metrics["MAE_PKR"])
        mlflow.log_metric("test_rmse_pkr", lgbm_metrics["RMSE_PKR"])
        mlflow.log_metric("test_r2", lgbm_metrics["R2"])
        mlflow.log_metric("test_mape_pct", lgbm_metrics["MAPE_pct"])
        mlflow.log_metric("training_time_seconds", train_time_lgbm)
        mlflow.set_tag("model_family", "LightGBM")
        mlflow.set_tag("feature_count", str(X_train.shape[1]))
        mlflow.sklearn.log_model(tuned_lgbm, name="model", serialization_format="cloudpickle")
        print(f"Logged Tuned LightGBM to MLflow (Run ID: {run_lgbm.info.run_id})")

    # 2. Tune CatBoost
    t0_cb = time.time()
    cb_params, tuned_cb = tune_catboost(X_train, y_train_log, X_val, y_val_log, y_val.values, n_trials=20)
    train_time_cb = time.time() - t0_cb

    pred_test_cb = np.expm1(tuned_cb.predict(X_test))
    cb_metrics = compute_metrics(y_test.values, pred_test_cb)

    # Log CatBoost Run in MLflow
    with mlflow.start_run(run_name="Tuned_CatBoost_Valuation") as run_cb:
        mlflow.log_params(cb_params)
        mlflow.log_metric("test_mae_pkr", cb_metrics["MAE_PKR"])
        mlflow.log_metric("test_rmse_pkr", cb_metrics["RMSE_PKR"])
        mlflow.log_metric("test_r2", cb_metrics["R2"])
        mlflow.log_metric("test_mape_pct", cb_metrics["MAPE_pct"])
        mlflow.log_metric("training_time_seconds", train_time_cb)
        mlflow.set_tag("model_family", "CatBoost")
        mlflow.set_tag("feature_count", str(X_train.shape[1]))
        mlflow.sklearn.log_model(tuned_cb, name="model", serialization_format="cloudpickle")
        print(f"Logged Tuned CatBoost to MLflow (Run ID: {run_cb.info.run_id})")

    # Compare tuned models
    print("\n" + "=" * 80)
    print("OPTUNA TUNED MODELS COMPARISON ON TEST SET")
    print("=" * 80)
    print(f"LightGBM -> R2: {lgbm_metrics['R2']:.4f} | MAE: {lgbm_metrics['MAE_PKR']/1e5:.2f} Lac | MAPE: {lgbm_metrics['MAPE_pct']:.2f}%")
    print(f"CatBoost -> R2: {cb_metrics['R2']:.4f} | MAE: {cb_metrics['MAE_PKR']/1e5:.2f} Lac | MAPE: {cb_metrics['MAPE_pct']:.2f}%")

    # Register the Winning Model
    if cb_metrics["R2"] >= lgbm_metrics["R2"]:
        champion_name = "Tuned_CatBoost"
        champion_model = tuned_cb
        champion_run_id = run_cb.info.run_id
        champion_metrics = cb_metrics
    else:
        champion_name = "Tuned_LightGBM"
        champion_model = tuned_lgbm
        champion_run_id = run_lgbm.info.run_id
        champion_metrics = lgbm_metrics

    print(f"\nWinning Model Selected: {champion_name}")

    # Register in MLflow Model Registry
    model_uri = f"runs:/{champion_run_id}/model"
    reg_model_name = "PropertyValuationModel"
    try:
        reg_model = mlflow.register_model(model_uri=model_uri, name=reg_model_name)
        print(f"Successfully registered model '{reg_model_name}' (Version: {reg_model.version}) in MLflow Model Registry!")
    except Exception as e:
        print(f"MLflow Model Registry notice: {e}")

    # Save local production artifact for inference engine & agent
    save_payload = {
        "model_name": champion_name,
        "model": champion_model,
        "preprocessor": preprocessor,
        "test_metrics": champion_metrics,
        "target_transform": "log1p",
        "registered_name": reg_model_name,
    }
    prod_model_path = MODEL_DIR / "best_property_valuation_model.joblib"
    joblib.dump(save_payload, prod_model_path)
    print(f"Exported production bundle to: {prod_model_path}")

    return save_payload


if __name__ == "__main__":
    run_tuning_and_tracking()
