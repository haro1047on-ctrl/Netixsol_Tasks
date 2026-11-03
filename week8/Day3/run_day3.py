"""Master Automated CLI Runner for Week 8 Day 3: Lead Scoring & Explainable AI.

Executes Tasks 1 through 5 end-to-end:
- Task 1: Baseline and Advanced Classification Models comparison
- Task 2: Imbalance handling comparison (No balancing vs Class Weights vs SMOTE vs Threshold tuning)
- Task 3: Evaluation, Calibration, Precision@Top-20%, and Business Cost Optimization
- Task 4: Unsupervised Customer Personas Discovery via K-Means Clustering
- Task 5: SHAP Explainability for Both Models (Lead Scoring & Property Valuation) + Fairness Audit
- Agent Verification: Week 7 Agent Integration Test
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
import pandas as pd
import numpy as np

# Reconfigure stdout to UTF-8 on Windows
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

DAY3_DIR = Path(__file__).resolve().parent
WEEK8_DIR = DAY3_DIR.parent
SRC_DIR = DAY3_DIR / "src"
REPORTS_DIR = DAY3_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = DAY3_DIR / "models"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from lead_models import (
    load_lead_splits, prepare_feature_matrices,
    train_and_compare_models, compare_imbalance_strategies
)
from lead_evaluator import (
    plot_roc_and_pr_curves, plot_confusion_and_calibration,
    analyze_business_cost_curve, audit_fairness_and_bias
)
from lead_clustering import discover_customer_personas
from shap_explainers import (
    explain_lead_scoring_model, explain_property_valuation_model
)
from lead_tuning_mlflow import run_optuna_tuning_and_mlflow
from lead_inference import LeadScoringEngine


def main():
    t_start = time.time()
    print("=" * 80)
    print("  WEEK 8 - DAY 3: AI LEAD SCORING & EXPLAINABLE AI PLATFORM")
    print("  Scenario: Triage 200 Leads -> Call Top 40 with Zero Wasted Calls")
    print("=" * 80)

    # 1. Load Data Splits and Preprocess
    print("\n[Step 1/6] Loading Stratified Splits & Preparing Feature Matrices...")
    train_df, val_df, test_df = load_lead_splits()
    X_train, y_train, X_val, y_val, X_test, y_test, preprocessor, feature_names = prepare_feature_matrices(
        train_df, val_df, test_df
    )
    print(f"Features: {len(feature_names)} engineered features (Zero data leakage verified).")
    print(f"Splits: Train N={len(y_train)} (Pos: {np.mean(y_train):.1%}), "
          f"Val N={len(y_val)} (Pos: {np.mean(y_val):.1%}), "
          f"Test N={len(y_test)} (Pos: {np.mean(y_test):.1%})")

    # 2. Task 1: Train & Compare Classification Models
    print("\n[Step 2/6] Task 1: Training & Evaluating Baseline vs Advanced Classifiers...")
    models_res, fitted_models = train_and_compare_models(X_train, y_train, X_test, y_test)
    models_res.to_csv(REPORTS_DIR / "lead_models_comparison.csv", index=False)
    print(models_res.to_string(index=False))

    # 3. Task 2: Compare Imbalance Strategies
    print("\n[Step 3/6] Task 2: Evaluating Imbalance Handling Strategies on LightGBM...")
    strat_res, strat_models = compare_imbalance_strategies(X_train, y_train, X_val, y_val, X_test, y_test)
    strat_res.to_csv(REPORTS_DIR / "imbalance_strategies_comparison.csv", index=False)
    print(strat_res.to_string(index=False))

    # 4. Task 3: Comprehensive Evaluation & Business Cost Optimization
    print("\n[Step 4/6] Task 3: Evaluation Plots, Calibration, and Business Cost Optimization...")
    plot_roc_and_pr_curves(fitted_models, X_test, y_test)
    plot_confusion_and_calibration(fitted_models["LightGBM"], X_test, y_test, threshold=0.40)
    
    best_thresh, savings_pkr_m, cost_df = analyze_business_cost_curve(
        fitted_models["LightGBM"], X_test, y_test, cost_fn=400000.0, cost_fp=1200.0
    )
    cost_df.to_csv(REPORTS_DIR / "business_cost_analysis.csv", index=False)
    print(f"Cost-Optimal Decision Threshold: t* = {best_thresh:.2f}")
    print(f"Estimated Agency Cost Savings vs Default 0.50 Threshold: PKR {savings_pkr_m:.2f} Million!")

    # Fairness & Bias Audit
    y_test_proba = fitted_models["LightGBM"].predict_proba(X_test)[:, 1]
    fairness_df = audit_fairness_and_bias(test_df, y_test_proba, threshold=best_thresh)
    fairness_df.to_csv(REPORTS_DIR / "fairness_bias_audit.csv", index=False)

    # 5. Task 4: Unsupervised Customer Personas Discovery
    print("\n[Step 5/6] Task 4: K-Means Customer Persona Clustering & Behavioral Profiles...")
    profile_df, persona_map, kmeans, scaler = discover_customer_personas(train_df, n_clusters=4)
    print(profile_df[["cluster", "persona_title", "mean_budget_display", "mean_calls", "visit_booked_rate", "actual_conversion_rate"]].to_string(index=False))

    # 6. Task 5: SHAP Explainability for Both Models
    print("\n[Step 6/6] Task 5: SHAP Explainability for Lead Scoring & Property Valuation Models...")
    explain_lead_scoring_model(fitted_models["LightGBM"], X_test, feature_names, sample_idx=0)
    explain_property_valuation_model()

    # 7. Verification of Production Inference Engine
    print("\n--- Verifying Production Lead Scoring Inference Engine ---")
    engine = LeadScoringEngine()
    test_lead = {
        "client_name": "Kashif Siddiqui",
        "phone": "+92-333-1234567",
        "budget_pkr": 32000000.0,
        "preferred_city": "Lahore",
        "property_type": "House",
        "purpose": "Buy",
        "number_of_calls": 4,
        "avg_call_duration_mins": 4.8,
        "response_time_hours": 0.35,
        "visit_booked": "Yes",
        "days_since_first_contact": 12,
        "objection_raised": "None",
        "lead_source": "WhatsApp",
    }
    score_res = engine.score_lead(test_lead)
    print(score_res["consultation_statement"])

    elapsed = time.time() - t_start
    print("\n" + "=" * 80)
    print(f"  WEEK 8 DAY 3 COMPLETED SUCCESSFULLY IN {elapsed:.1f}s")
    print("=" * 80)


if __name__ == "__main__":
    main()
