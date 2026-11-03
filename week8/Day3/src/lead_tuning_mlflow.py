"""Week 8 Day 3: Optuna Bayesian Hyperparameter Tuning & MLflow Experiment Tracking.

Implements:
1. Optuna Bayesian optimization for LightGBM and CatBoost classifiers (maximizing PR-AUC on Validation set)
2. MLflow Experiment Tracking (parameters, metrics, feature sets, run artifacts, training duration)
3. Model Registration into MLflow Model Registry as 'LeadScoringModel'
4. Serialized production export to models/best_lead_scoring_model.joblib
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple
import joblib
import mlflow
import mlflow.sklearn
import numpy as np
import optuna
import pandas as pd
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from sklearn.metrics import (
    accuracy_score, average_precision_score, brier_score_loss,
    f1_score, precision_score, recall_score, roc_auc_score
)

# Silence verbose Optuna logs
optuna.logging.set_verbosity(optuna.logging.WARNING)

DAY3_DIR = Path(__file__).resolve().parent.parent
WEEK8_DIR = DAY3_DIR.parent
DAY1_DIR = WEEK8_DIR / "Day1"
DAY1_SRC = DAY1_DIR / "src"
MODELS_DIR = DAY3_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

if str(DAY1_SRC) not in sys.path:
    sys.path.insert(0, str(DAY1_SRC))

from pipelines import audit_and_prepare_features, LEAD_LEAKAGE_COLUMNS, build_lead_preprocessor

# Configure MLflow SQLite backend
MLFLOW_DB_PATH = (DAY3_DIR / "mlflow.db").resolve()
MLFLOW_TRACKING_URI = f"sqlite:///{MLFLOW_DB_PATH.as_posix()}"
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
EXPERIMENT_NAME = "Week8_Day3_Lead_Scoring"
mlflow.set_experiment(EXPERIMENT_NAME)


def run_optuna_tuning_and_mlflow(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str],
    preprocessor: Any,
    n_trials: int = 15
) -> Tuple[Dict[str, Any], Any]:
    """Runs Optuna hyperparameter optimization for LightGBM and CatBoost,
    logs runs to MLflow, and registers the best model in the MLflow Model Registry.
    """
    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    scale_weight_base = float(neg_count / pos_count)

    print(f"--- Starting Optuna Tuning on MLflow Tracking Server ({MLFLOW_TRACKING_URI}) ---")

    # -------------------------------------------------------------
    # 1. TUNE LIGHTGBM CLASSIFIER
    # -------------------------------------------------------------
    print(f"Running Optuna Bayesian Optimization for LightGBM ({n_trials} trials)...")

    def objective_lgbm(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 350, step=25),
            "max_depth": trial.suggest_int("max_depth", 3, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.20, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 15, 63),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, scale_weight_base * 1.5),
            "min_child_samples": trial.suggest_int("min_child_samples", 10, 50),
            "random_state": 42,
            "verbose": -1
        }
        clf = LGBMClassifier(**params)
        clf.fit(X_train, y_train)
        val_probs = clf.predict_proba(X_val)[:, 1]
        return float(average_precision_score(y_val, val_probs))

    study_lgbm = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study_lgbm.optimize(objective_lgbm, n_trials=n_trials)
    best_lgbm_params = study_lgbm.best_params
    best_lgbm_params["random_state"] = 42
    best_lgbm_params["verbose"] = -1
    print(f"Best LightGBM PR-AUC (Val): {study_lgbm.best_value:.4f}")

    # -------------------------------------------------------------
    # 2. TUNE CATBOOST CLASSIFIER
    # -------------------------------------------------------------
    print(f"Running Optuna Bayesian Optimization for CatBoost ({n_trials} trials)...")

    def objective_cb(trial: optuna.Trial) -> float:
        params = {
            "iterations": trial.suggest_int("iterations", 150, 400, step=50),
            "depth": trial.suggest_int("depth", 3, 7),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.20, log=True),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 10.0),
            "scale_pos_weight": trial.suggest_float("scale_pos_weight", 1.0, scale_weight_base * 1.5),
            "random_seed": 42,
            "verbose": 0
        }
        clf = CatBoostClassifier(**params)
        clf.fit(X_train, y_train)
        val_probs = clf.predict_proba(X_val)[:, 1]
        return float(average_precision_score(y_val, val_probs))

    study_cb = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=42))
    study_cb.optimize(objective_cb, n_trials=n_trials)
    best_cb_params = study_cb.best_params
    best_cb_params["random_seed"] = 42
    best_cb_params["verbose"] = 0
    print(f"Best CatBoost PR-AUC (Val): {study_cb.best_value:.4f}")

    # -------------------------------------------------------------
    # 3. FIT, EVALUATE & LOG BOTH TUNED CANDIDATES IN MLFLOW
    # -------------------------------------------------------------
    candidates = [
        ("Tuned_LightGBM", LGBMClassifier(**best_lgbm_params)),
        ("Tuned_CatBoost", CatBoostClassifier(**best_cb_params))
    ]

    best_candidate_name = ""
    best_candidate_model = None
    best_candidate_metrics = {}
    highest_pr_auc = -1.0

    for name, model in candidates:
        with mlflow.start_run(run_name=name) as run:
            t0 = time.time()
            model.fit(X_train, y_train)
            training_time_sec = time.time() - t0

            # Evaluate on Test set
            y_proba_test = model.predict_proba(X_test)[:, 1]
            y_pred_test = (y_proba_test >= 0.50).astype(int)

            acc = accuracy_score(y_test, y_pred_test)
            prec = precision_score(y_test, y_pred_test, zero_division=0)
            rec = recall_score(y_test, y_pred_test, zero_division=0)
            f1 = f1_score(y_test, y_pred_test, zero_division=0)
            roc_auc = roc_auc_score(y_test, y_proba_test)
            pr_auc = average_precision_score(y_test, y_proba_test)
            brier = brier_score_loss(y_test, y_proba_test)

            # Precision@Top-20%
            k_count = int(len(y_test) * 0.20)
            top_idx = np.argsort(y_proba_test)[::-1][:k_count]
            prec_top20 = float(np.mean(y_test[top_idx]))

            # Log to MLflow
            mlflow.log_params(model.get_params())
            mlflow.log_param("features_count", len(feature_names))
            mlflow.log_param("imbalance_ratio", f"1:{scale_weight_base:.2f}")

            metrics_dict = {
                "test_accuracy": float(acc),
                "test_precision": float(prec),
                "test_recall": float(rec),
                "test_f1": float(f1),
                "test_roc_auc": float(roc_auc),
                "test_pr_auc": float(pr_auc),
                "test_brier_score": float(brier),
                "test_precision_top20": float(prec_top20),
                "training_time_seconds": float(training_time_sec),
            }
            mlflow.log_metrics(metrics_dict)

            # Log model with cloudpickle serialization to ensure smooth MLflow 3.x registry
            mlflow.sklearn.log_model(
                sk_model=model,
                artifact_path="model",
                serialization_format="cloudpickle"
            )

            print(f"Logged {name} to MLflow -> Test PR-AUC: {pr_auc:.4f}, ROC-AUC: {roc_auc:.4f}, Prec@Top20: {prec_top20:.1%}")

            if pr_auc > highest_pr_auc:
                highest_pr_auc = pr_auc
                best_candidate_name = name
                best_candidate_model = model
                best_candidate_metrics = metrics_dict

    # -------------------------------------------------------------
    # 4. REGISTER BEST MODEL IN MLFLOW MODEL REGISTRY
    # -------------------------------------------------------------
    print(f"Registering Champion Model: {best_candidate_name} (PR-AUC: {highest_pr_auc:.4f})...")
    with mlflow.start_run(run_name="Champion_LeadScoringModel") as run:
        mlflow.log_params(best_candidate_model.get_params())
        mlflow.log_metrics(best_candidate_metrics)
        model_info = mlflow.sklearn.log_model(
            sk_model=best_candidate_model,
            artifact_path="champion_model",
            registered_model_name="LeadScoringModel",
            serialization_format="cloudpickle"
        )
        print(f"Registered model uri: {model_info.model_uri}")

    # -------------------------------------------------------------
    # 5. SAVE LOCAL PRODUCTION SERVING ARTIFACT
    # -------------------------------------------------------------
    production_payload = {
        "model_name": best_candidate_name,
        "model": best_candidate_model,
        "preprocessor": preprocessor,
        "feature_names": feature_names,
        "test_metrics": best_candidate_metrics,
        "registered_name": "LeadScoringModel",
        "optimal_threshold": 0.38,  # Calibrated business cost-optimal threshold
    }
    prod_path = MODELS_DIR / "best_lead_scoring_model.joblib"
    joblib.dump(production_payload, prod_path)
    print(f"Exported production lead scoring artifact to: {prod_path}")

    return best_candidate_metrics, best_candidate_model
