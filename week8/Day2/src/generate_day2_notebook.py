"""Generates day2_property_valuation_regression.ipynb notebook."""
from pathlib import Path
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

# Title cell
cells.append(nbf.v4.new_markdown_cell("""# Week 8 — Day 2: Property Valuation Model (Regression)
## AI Property Valuation & Fair Market Pricing Platform
**Platform Architecture:** Machine Learning (Gradient Boosted Trees) • Explainable AI • MLflow Tracking • Week 7 Agent Tool Calling  
**Scenario:** Sales manager asks: *"Is plot ki sahi qeemat kya honi chahiye?"*

---

### Day 2 Tasks:
- **Task 1 — Baseline Models:** Mean / Median baseline, Linear Regression, Ridge, Lasso
- **Task 2 — Advanced Models:** Random Forest, XGBoost, LightGBM, CatBoost
- **Task 3 — Comprehensive Evaluation:** MAE, RMSE, R², MAPE, City & Price Tier Slice Error Analysis, Actual vs Predicted Plot
- **Task 4 — Optuna Hyperparameter Tuning & MLflow Tracking:** Logging parameters, metrics, artifacts, and Model Registry
- **Task 5 — Price Range & Confidence:** Quantile prediction intervals, market verdict (Overpriced / Fair / Underpriced), and UrduLish consultation
- **Week 7 Agent Integration:** Exposing the model as `property_valuation_tool` in `week7-RE_Agent/day5-langgraph-agent`
"""))

# Cell 2: Imports
cells.append(nbf.v4.new_code_cell("""import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Add Day 2 src to path
SRC_DIR = Path.cwd().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from valuation_models import load_partitioned_data, train_and_evaluate_all_models
from valuation_evaluator import plot_actual_vs_predicted, analyze_error_slices
from valuation_inference import PropertyValuationEngine, train_quantile_models

print("Environment configured and modules imported successfully!")
"""))

# Cell 3: Tasks 1 & 2 Model Training
cells.append(nbf.v4.new_markdown_cell("""## Tasks 1 & 2 — Baseline and Advanced Model Training
We evaluate 9 models on the held-out test set ($N=858$).
"""))

cells.append(nbf.v4.new_code_cell("""results_df, trained_models, test_preds, test_df = train_and_evaluate_all_models()
display(results_df)
"""))

# Cell 4: Task 3 Evaluation
cells.append(nbf.v4.new_markdown_cell("""## Task 3 — Comprehensive Evaluation & Error Slice Analysis
- Actual vs. Predicted plots with 45-degree parity lines
- Slice error by City and Price Range
"""))

cells.append(nbf.v4.new_code_cell("""from IPython.display import Image, display

FIG_DIR = Path.cwd().parent / "reports" / "figures"

# Display Figure 07
display(Image(filename=str(FIG_DIR / "07_actual_vs_predicted_models.png"), width=900))

# Display Figure 08
display(Image(filename=str(FIG_DIR / "08_error_by_city_and_price_tier.png"), width=900))
"""))

# Cell 5: Task 4 Hyperparameter Tuning & MLflow
cells.append(nbf.v4.new_markdown_cell("""## Task 4 — Optuna Hyperparameter Tuning & MLflow Tracking
We inspect the winning model registered in the MLflow Model Registry.
"""))

cells.append(nbf.v4.new_code_cell("""import mlflow

MLFLOW_DB_PATH = Path.cwd().parent / "mlflow.db"
mlflow.set_tracking_uri(f"sqlite:///{MLFLOW_DB_PATH.as_posix()}")

client = mlflow.tracking.MlflowClient()
registered_models = client.search_registered_models()

for rm in registered_models:
    print(f"Model Name: {rm.name}")
    for mv in rm.latest_versions:
        print(f"  Version: {mv.version} | Status: {mv.status} | Source: {mv.source}")
"""))

# Cell 6: Task 5 Prediction Intervals & Market Verdict
cells.append(nbf.v4.new_markdown_cell("""## Task 5 — Price Range, Quantile Intervals & Market Verdict
Testing the inference engine on sample sales inquiries.
"""))

cells.append(nbf.v4.new_code_cell("""engine = PropertyValuationEngine()

# Scenario 1: Manager asks: "Is plot ki sahi qeemat kya honi chahiye?"
quote_1 = engine.evaluate_property({
    "city": "Islamabad",
    "area_society": "Sector F-7",
    "property_type": "House",
    "plot_size_marla": 20.0,
    "bedrooms": 5,
    "bathrooms": 5,
    "age_years": 1.0,
})

print("Scenario 1: Fair Market Price Inquiry")
print("  English: ", quote_1["english_summary"])
print("  UrduLish:", quote_1["urdulish_summary"])

# Scenario 2: Overpriced Listing Assessment
quote_2 = engine.evaluate_property({
    "city": "Lahore",
    "area_society": "DHA Phase 5",
    "property_type": "House",
    "plot_size_marla": 10.0,
    "bedrooms": 4,
    "bathrooms": 4,
    "age_years": 2.0,
    "is_corner": "Yes",
}, listed_price_pkr=49000000.0)

print("\\nScenario 2: Asking Price Assessment (Listed 4.90 Crore)")
print("  English: ", quote_2["english_summary"])
print("  UrduLish:", quote_2["urdulish_summary"])
"""))

# Cell 7: Week 7 Agent Integration
cells.append(nbf.v4.new_markdown_cell("""## Week 7 RE Agent Extension
Calling `property_valuation_tool` through the Week 7 Agent Tool Registry.
"""))

cells.append(nbf.v4.new_code_cell("""# Add Week 7 agent tools to path
WEEK7_AGENT_DIR = Path.cwd().parent.parent.parent / "week7-RE_Agent" / "day5-langgraph-agent"
if str(WEEK7_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(WEEK7_AGENT_DIR))

from tools import property_valuation_tool

tool_response = property_valuation_tool.invoke({
    "city": "Lahore",
    "area_society": "DHA Phase 5",
    "property_type": "House",
    "plot_size_marla": 10.0,
    "bedrooms": 4,
    "age_years": 2.0,
    "listed_price_pkr": 49000000.0,
    "is_corner": "Yes",
})

print("Week 7 Agent Tool Output:")
print(tool_response)
"""))

nb["cells"] = cells

NOTEBOOK_PATH = Path.cwd().parent / "notebooks" / "day2_property_valuation_regression.ipynb"
with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print(f"Successfully generated: {NOTEBOOK_PATH}")
