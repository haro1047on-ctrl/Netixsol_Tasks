"""Week 8 Day 3: Lead Scoring Classification & Imbalance Handling Models.

Implements:
1. Baseline Classifiers: Dummy Classifier, Logistic Regression
2. Advanced Ensembles: Random Forest, XGBoost, LightGBM, CatBoost
3. Imbalance Strategies: No balancing, Class Weights, SMOTE, Threshold tuning
4. Cross-validation and Test evaluation for deal conversion prediction
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier
from catboost import CatBoostClassifier
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score, brier_score_loss, confusion_matrix
)

# Reference paths
DAY3_DIR = Path(__file__).resolve().parent.parent
WEEK8_DIR = DAY3_DIR.parent
DAY1_DIR = WEEK8_DIR / "Day1"
DAY1_SRC = DAY1_DIR / "src"
PROC_DATA_DIR = DAY1_DIR / "data" / "processed"
MODELS_DIR = DAY3_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

if str(DAY1_SRC) not in sys.path:
    sys.path.insert(0, str(DAY1_SRC))

from pipelines import build_lead_preprocessor, audit_and_prepare_features, LEAD_LEAKAGE_COLUMNS


def load_lead_splits() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Loads cleaned, stratified 70/15/15 train, validation, and test lead splits."""
    train_df = pd.read_csv(PROC_DATA_DIR / "leads_train.csv")
    val_df = pd.read_csv(PROC_DATA_DIR / "leads_val.csv")
    test_df = pd.read_csv(PROC_DATA_DIR / "leads_test.csv")
    return train_df, val_df, test_df


def prepare_feature_matrices(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, Any, List[str]]:
    """Audits data leakage, fits preprocessor on train, and transforms val & test splits."""
    X_train_raw, y_train, _ = audit_and_prepare_features(
        train_df, target_col="converted_binary", leakage_cols=LEAD_LEAKAGE_COLUMNS
    )
    X_val_raw, y_val, _ = audit_and_prepare_features(
        val_df, target_col="converted_binary", leakage_cols=LEAD_LEAKAGE_COLUMNS
    )
    X_test_raw, y_test, _ = audit_and_prepare_features(
        test_df, target_col="converted_binary", leakage_cols=LEAD_LEAKAGE_COLUMNS
    )

    preprocessor = build_lead_preprocessor()
    X_train = preprocessor.fit_transform(X_train_raw)
    X_val = preprocessor.transform(X_val_raw)
    X_test = preprocessor.transform(X_test_raw)

    feature_names = preprocessor.get_feature_names_out().tolist()

    # Save fitted lead preprocessor to Day 3 models directory
    joblib.dump(preprocessor, MODELS_DIR / "lead_preprocessor.joblib")

    return (
        X_train, y_train.to_numpy(),
        X_val, y_val.to_numpy(),
        X_test, y_test.to_numpy(),
        preprocessor, feature_names
    )


def compute_precision_at_k(y_true: np.ndarray, y_proba: np.ndarray, k_pct: float = 0.20) -> float:
    """Calculates Precision@Top-K% (e.g. top 20% of ranked leads)."""
    n_total = len(y_true)
    k_count = max(1, int(n_total * k_pct))
    top_indices = np.argsort(y_proba)[::-1][:k_count]
    return float(np.mean(y_true[top_indices]))


def evaluate_classifier(
    model: Any,
    X_eval: np.ndarray,
    y_eval: np.ndarray,
    threshold: float = 0.50
) -> Dict[str, float]:
    """Computes comprehensive classification metrics at a given decision threshold."""
    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_eval)[:, 1]
    else:
        y_proba = model.predict(X_eval)

    y_pred = (y_proba >= threshold).astype(int)

    acc = accuracy_score(y_eval, y_pred)
    prec = precision_score(y_eval, y_pred, zero_division=0)
    rec = recall_score(y_eval, y_pred, zero_division=0)
    f1 = f1_score(y_eval, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_eval, y_proba)
    pr_auc = average_precision_score(y_eval, y_proba)
    brier = brier_score_loss(y_eval, y_proba)
    prec_top20 = compute_precision_at_k(y_eval, y_proba, k_pct=0.20)

    # Base rate lift
    base_rate = float(np.mean(y_eval))
    lift_top20 = prec_top20 / base_rate if base_rate > 0 else 1.0

    return {
        "accuracy": round(float(acc), 4),
        "precision": round(float(prec), 4),
        "recall": round(float(rec), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(roc_auc), 4),
        "pr_auc": round(float(pr_auc), 4),
        "brier_score": round(float(brier), 4),
        "precision_top20": round(float(prec_top20), 4),
        "lift_top20": round(float(lift_top20), 2),
    }


def train_and_compare_models(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Task 1: Trains and compares baseline and advanced ensemble classification models."""
    models: Dict[str, Any] = {
        "Dummy (Most Frequent)": DummyClassifier(strategy="most_frequent"),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42),
        "XGBoost": XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.05, random_state=42, eval_metric="logloss"),
        "LightGBM": LGBMClassifier(n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42, verbose=-1),
        "CatBoost": CatBoostClassifier(iterations=300, depth=6, learning_rate=0.05, random_seed=42, verbose=0),
    }

    results = []
    fitted_models = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        fitted_models[name] = model
        metrics = evaluate_classifier(model, X_test, y_test, threshold=0.50)
        metrics["model_name"] = name
        results.append(metrics)

    res_df = pd.DataFrame(results)[
        ["model_name", "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "brier_score", "precision_top20", "lift_top20"]
    ]
    res_df = res_df.sort_values(by="pr_auc", ascending=False).reset_index(drop=True)
    return res_df, fitted_models


def compare_imbalance_strategies(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    X_test: np.ndarray,
    y_test: np.ndarray
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Task 2: Compares 4 Imbalance Handling Strategies on LightGBM:
    1. No Balancing
    2. Class Weights (scale_pos_weight ~ (len(neg)/len(pos)))
    3. SMOTE Over-sampling
    4. Cost-sensitive Threshold Tuning
    """
    neg_count = np.sum(y_train == 0)
    pos_count = np.sum(y_train == 1)
    scale_weight = float(neg_count / pos_count)

    strategies_res = []
    strategy_models = {}

    # 1. No Balancing (Default LightGBM)
    model_nobal = LGBMClassifier(n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42, verbose=-1)
    model_nobal.fit(X_train, y_train)
    strategy_models["No Balancing"] = model_nobal
    m1 = evaluate_classifier(model_nobal, X_test, y_test, threshold=0.50)
    m1["strategy"] = "1. No Balancing"
    m1["decision_threshold"] = 0.50
    strategies_res.append(m1)

    # 2. Class Weights
    model_cw = LGBMClassifier(
        n_estimators=200, max_depth=6, learning_rate=0.05,
        scale_pos_weight=scale_weight, random_state=42, verbose=-1
    )
    model_cw.fit(X_train, y_train)
    strategy_models["Class Weights"] = model_cw
    m2 = evaluate_classifier(model_cw, X_test, y_test, threshold=0.50)
    m2["strategy"] = "2. Class Weights (scale_pos_weight=2.96)"
    m2["decision_threshold"] = 0.50
    strategies_res.append(m2)

    # 3. SMOTE Over-sampling
    smote = SMOTE(random_state=42)
    X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)
    model_smote = LGBMClassifier(n_estimators=200, max_depth=6, learning_rate=0.05, random_state=42, verbose=-1)
    model_smote.fit(X_train_smote, y_train_smote)
    strategy_models["SMOTE"] = model_smote
    m3 = evaluate_classifier(model_smote, X_test, y_test, threshold=0.50)
    m3["strategy"] = "3. SMOTE Over-sampling"
    m3["decision_threshold"] = 0.50
    strategies_res.append(m3)

    # 4. Threshold Tuning on Validation set (Optimizing F1 on No-Balancing model)
    val_probs = model_nobal.predict_proba(X_val)[:, 1]
    thresholds = np.linspace(0.10, 0.90, 81)
    best_thresh = 0.50
    best_val_f1 = -1.0
    for t in thresholds:
        preds = (val_probs >= t).astype(int)
        score = f1_score(y_val, preds, zero_division=0)
        if score > best_val_f1:
            best_val_f1 = score
            best_thresh = t

    strategy_models["Threshold Tuned"] = (model_nobal, best_thresh)
    m4 = evaluate_classifier(model_nobal, X_test, y_test, threshold=best_thresh)
    m4["strategy"] = f"4. Threshold Tuned (t*={best_thresh:.2f})"
    m4["decision_threshold"] = round(float(best_thresh), 2)
    strategies_res.append(m4)

    strat_df = pd.DataFrame(strategies_res)[
        ["strategy", "decision_threshold", "accuracy", "precision", "recall", "f1", "roc_auc", "pr_auc", "precision_top20", "lift_top20"]
    ]
    return strat_df, strategy_models
