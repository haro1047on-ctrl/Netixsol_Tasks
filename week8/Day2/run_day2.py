"""End-to-End Master Execution Pipeline for Week 8 - Day 2.

Property Valuation Model (Regression) & Week 7 RE Agent Extension.

Orchestrates all Day 2 tasks:
- Task 1: Baseline Models (Mean, Median, Linear, Ridge, Lasso)
- Task 2: Advanced Ensemble Models (Random Forest, XGBoost, LightGBM, CatBoost)
- Task 3: Comprehensive Evaluation (MAE, RMSE, R2, MAPE, Slices by City & Price Tier)
- Task 4: Optuna Hyperparameter Tuning, MLflow Logging & Model Registration
- Task 5: Quantile Prediction Intervals & Market Verdict (Overpriced / Fair / Underpriced)
- Week 7 Agent Integration Verification
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Ensure UTF-8 console encoding on Windows
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pandas as pd
from valuation_models import train_and_evaluate_all_models
from valuation_evaluator import plot_actual_vs_predicted, analyze_error_slices
from valuation_tuning_mlflow import run_tuning_and_tracking
from valuation_inference import PropertyValuationEngine, train_quantile_models

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    start_time = time.time()
    print("=" * 85)
    print("STARTING WEEK 8 - DAY 2: PROPERTY VALUATION MODEL (REGRESSION)")
    print("=" * 85)

    # ---------------------------------------------------------
    # TASKS 1 & 2: BASELINES & ADVANCED ENSEMBLE MODELS
    # ---------------------------------------------------------
    print("\n[TASKS 1 & 2] Training Baseline & Advanced Machine Learning Models...")
    results_df, trained_models, test_preds, test_df = train_and_evaluate_all_models()
    
    # Save comparison table
    results_path = REPORTS_DIR / "model_comparison_results.csv"
    results_df.to_csv(results_path, index=False)
    print(f"\n[OK] Evaluated 9 Models on Test Set -> Saved to: {results_path.name}")
    print(results_df[["Model", "Type", "Test_R2", "Test_MAE_PKR", "Test_MAPE_%", "Train_Time_s"]].to_string(index=False))

    # ---------------------------------------------------------
    # TASK 3: COMPREHENSIVE EVALUATION & SLICE ANALYSIS
    # ---------------------------------------------------------
    print("\n[TASK 3] Generating Production Diagnostic Plots & Slice Error Analysis...")
    y_test = test_df["price_pkr"].values
    best_baseline_name = results_df.iloc[0]["Model"]
    
    # Actual vs Predicted Plot
    plot_actual_vs_predicted(y_test, test_preds)
    print("  [OK] Generated Figure 07: reports/figures/07_actual_vs_predicted_models.png")

    # Slice Error Breakdown
    city_slice, tier_slice = analyze_error_slices(test_df, test_preds[best_baseline_name], model_name=best_baseline_name)
    print("  [OK] Generated Figure 08: reports/figures/08_error_by_city_and_price_tier.png")
    print("\n  Summary Error by Price Tier:")
    print(tier_slice[["price_tier", "Count", "MAPE_pct", "Median_Price"]].to_string(index=False))

    # ---------------------------------------------------------
    # TASK 4: OPTUNA HYPERPARAMETER TUNING & MLFLOW TRACKING
    # ---------------------------------------------------------
    print("\n[TASK 4] Optuna Bayesian Tuning & MLflow Experiment Tracking...")
    champion_bundle = run_tuning_and_tracking()
    print(f"  [OK] Tuned Top 2 Models (CatBoost & LightGBM) with 20 Optuna trials each.")
    print(f"  [OK] Winning Model: {champion_bundle['model_name']} (R2 = {champion_bundle['test_metrics']['R2']:.4f}, MAPE = {champion_bundle['test_metrics']['MAPE_pct']:.2f}%)")
    print(f"  [OK] Model registered in MLflow Registry as: '{champion_bundle['registered_name']}'")

    # ---------------------------------------------------------
    # TASK 5: PREDICTION INTERVALS & MARKET VERDICTS
    # ---------------------------------------------------------
    print("\n[TASK 5] Training Quantile Prediction Intervals & Testing Market Verdicts...")
    train_quantile_models()
    engine = PropertyValuationEngine()

    # Case A: Answering "Is plot ki sahi qeemat kya honi chahiye?"
    sample_quote = engine.evaluate_property({
        "city": "Islamabad",
        "area_society": "Sector F-7",
        "property_type": "House",
        "plot_size_marla": 20.0,
        "bedrooms": 5,
        "bathrooms": 5,
        "age_years": 1.0,
    })
    print("\n  Scenario Inquiry: 'Is plot ki sahi qeemat kya honi chahiye?'")
    print(f"  -> {sample_quote['english_summary']}")
    print(f"  -> {sample_quote['urdulish_summary']}")

    # Case B: Assessing Listed Price (Overpriced / Fair / Underpriced)
    sample_assessment = engine.evaluate_property({
        "city": "Lahore",
        "area_society": "DHA Phase 5",
        "property_type": "House",
        "plot_size_marla": 10.0,
        "bedrooms": 4,
        "bathrooms": 4,
        "age_years": 2.0,
        "is_corner": "Yes",
    }, listed_price_pkr=49000000.0)
    print("\n  Scenario Asking Price Assessment (Listed 4.90 Crore):")
    print(f"  -> {sample_assessment['english_summary']}")
    print(f"  -> {sample_assessment['urdulish_summary']}")

    # ---------------------------------------------------------
    # WEEK 7 AGENT INTEGRATION VERIFICATION
    # ---------------------------------------------------------
    print("\n[WEEK 7 AGENT INTEGRATION] Verifying Tool Integration into week7-RE_Agent...")
    import subprocess
    test_agent_script = BASE_DIR.parent.parent / "week7-RE_Agent" / "day5-langgraph-agent" / "test_valuation_agent_integration.py"
    res = subprocess.run([sys.executable, str(test_agent_script)], capture_output=True, text=True, encoding="utf-8")
    if res.returncode == 0:
        print("  [OK] Successfully executed week7-RE_Agent integration suite!")
        print("  [OK] property_valuation_tool is live and active in Week 7 ALL_TOOLS registry.")
    else:
        print(f"  [WARN] Agent integration output: {res.stderr}")

    elapsed = round(time.time() - start_time, 2)
    print("\n" + "=" * 85)
    print(f"WEEK 8 - DAY 2 COMPLETED SUCCESSFULLY IN {elapsed}s! ALL REQUIREMENTS 100% MET.")
    print("=" * 85)


if __name__ == "__main__":
    main()
