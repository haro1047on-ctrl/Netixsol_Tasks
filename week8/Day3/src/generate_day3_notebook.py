"""Generates day3_lead_scoring_classification.ipynb notebook."""
from pathlib import Path
import nbformat as nbf

DAY3_DIR = Path(__file__).resolve().parent.parent

nb = nbf.v4.new_notebook()
cells = []

# Title cell
cells.append(nbf.v4.new_markdown_cell("""# Week 8 — Day 3: Lead Scoring Model (Classification) & Explainability
## AI Property Valuation & Lead Scoring Platform for Real Estate
**Platform Architecture:** Machine Learning (LightGBM/CatBoost) • Imbalanced Data Handling • K-Means Personas • SHAP Explainable AI • MLflow Model Registry • Week 7 Agent Tool Calling  
**Scenario:** The sales team has 200 new leads and time to call only 40. Your model decides who gets called first with zero wasted calls and explains its predictions in English & UrduLish.

---

### Day 3 Core Deliverables:
- **Task 1 — Classification Models:** Dummy baseline, Logistic Regression, Random Forest, XGBoost, LightGBM, CatBoost
- **Task 2 — Handling Imbalanced Data:** No balancing vs Class weights vs SMOTE vs Threshold tuning (with proof why accuracy is misleading)
- **Task 3 — Comprehensive Evaluation:** Precision, Recall, F1, ROC-AUC, PR-AUC, Confusion Matrix, Calibration Curve, Precision@Top-20%, and Business Cost Optimization ($C_{\\text{FN}} = 400\\text{k PKR}$ vs $C_{\\text{FP}} = 1.2\\text{k PKR}$)
- **Task 4 — Lead Segmentation & Customer Personas:** 🔥 Hot (1-hr SLA), 🌤 Warm (24-hr SLA), ❄️ Cold (drip), plus K-Means discovery of 4 customer personas
- **Task 5 — Explainability with SHAP (Both Models):** Global beeswarm, Local waterfall, Plain-language English & UrduLish reason generator, and Fairness/Bias audit across City and Lead Source
- **Week 7 Agent Integration:** `lead_scoring_tool` in `week7-RE_Agent/day5-langgraph-agent`
"""))

# Imports
cells.append(nbf.v4.new_code_cell("""import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

# Setup paths
NOTEBOOK_DIR = Path.cwd()
DAY3_DIR = NOTEBOOK_DIR.parent if NOTEBOOK_DIR.name == "notebooks" else NOTEBOOK_DIR
WEEK8_DIR = DAY3_DIR.parent
SRC_DIR = DAY3_DIR / "src"
REPORTS_DIR = DAY3_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = DAY3_DIR / "models"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

print("Environment configured successfully!")
"""))

# Task 1: Load Data & Preprocessing
cells.append(nbf.v4.new_markdown_cell("""## Step 1: Stratified Data Splits & Feature Pipeline
We load the 70/15/15 stratified train, validation, and test splits ($N=2,520$ train, $N=540$ val, $N=540$ test) with a 25.2% base conversion rate.
All 7 leakage columns (`converted`, `converted_binary`, `lead_id`, `client_name`, `phone`, `budget_raw`, `budget_pkr_normalized`) are safely stripped before column transformation.
"""))

cells.append(nbf.v4.new_code_cell("""from lead_models import load_lead_splits, prepare_feature_matrices

train_df, val_df, test_df = load_lead_splits()
X_train, y_train, X_val, y_val, X_test, y_test, preprocessor, feature_names = prepare_feature_matrices(
    train_df, val_df, test_df
)

print(f"Engineered Features Count: {len(feature_names)}")
print(f"Train Shape: {X_train.shape} | Positive Rate: {np.mean(y_train):.1%}")
print(f"Val Shape:   {X_val.shape}   | Positive Rate: {np.mean(y_val):.1%}")
print(f"Test Shape:  {X_test.shape}  | Positive Rate: {np.mean(y_test):.1%}")
"""))

# Task 1 & 2: Models Comparison
cells.append(nbf.v4.new_markdown_cell("""## Step 2: Model Comparison & Imbalance Handling (Tasks 1 & 2)
### Why Accuracy is Misleading:
The Dummy (Most Frequent) classifier achieves **74.81% accuracy** simply by predicting `0` for every lead. However, its Recall and Precision are **0.0%**, missing every single closing deal!

We benchmark:
1. Baseline: Dummy Classifier, Logistic Regression
2. Tree Ensembles: Random Forest, XGBoost, LightGBM, CatBoost
3. Imbalance Strategies: No Balancing vs Class Weights vs SMOTE vs Threshold Tuning
"""))

cells.append(nbf.v4.new_code_cell("""from lead_models import train_and_compare_models, compare_imbalance_strategies

models_df, fitted_models = train_and_compare_models(X_train, y_train, X_test, y_test)
print("=== CLASSIFICATION MODELS COMPARISON (TEST SET) ===")
display(models_df)

strat_df, strat_models = compare_imbalance_strategies(X_train, y_train, X_val, y_val, X_test, y_test)
print("\n=== IMBALANCE HANDLING STRATEGIES (LIGHTGBM) ===")
display(strat_df)
"""))

# Task 3: Evaluation & Business Cost Curve
cells.append(nbf.v4.new_markdown_cell("""## Step 3: Evaluation, Calibration & Business Cost Optimization (Task 3)
### Scenario: 200 Leads, SDR Time to Call Only 40
We evaluate:
- ROC Curves and Precision-Recall Curves (PR-AUC is the gold standard under imbalance)
- Precision@Top-20% and Lift over random calling
- Calibration Reliability Diagrams (Brier Score)
- **Business Cost Optimization Curve:**
  $$\\text{Total Cost}(t) = \\text{FN}(t) \\times C_{\\text{FN}} + \\text{FP}(t) \\times C_{\\text{FP}}$$
  where $C_{\\text{FN}} = 400,000\\text{ PKR}$ (lost deal commission) and $C_{\\text{FP}} = 1,200\\text{ PKR}$ (wasted 15-minute SDR call).
"""))

cells.append(nbf.v4.new_code_cell("""from IPython.display import Image, display

# Display Figures 01, 02, and 03
display(Image(filename=str(FIGURES_DIR / "01_imbalance_and_model_roc_pr_curves.png")))
display(Image(filename=str(FIGURES_DIR / "02_confusion_matrices_and_calibration.png")))
display(Image(filename=str(FIGURES_DIR / "03_business_cost_threshold_curve.png")))
"""))

# Task 4: Personas
cells.append(nbf.v4.new_markdown_cell("""## Step 4: Customer Persona Discovery via K-Means Clustering (Task 4)
Unsupervised clustering on behavioral engagement and financial capacity reveals 4 natural real estate customer personas:
1. **High-Net-Worth / Overseas Investor:** Mean Budget ~8.5 Cr PKR, Buy purpose, rapid WhatsApp response
2. **Serious First-Time Homebuyer:** Mean Budget ~1.8 Cr PKR, highest engagement (4.4 calls, visit booked), 49.9% actual conversion rate
3. **Casual Window Shoppers / Speculators:** Low engagement, no visit booked, slower response
"""))

cells.append(nbf.v4.new_code_cell("""display(Image(filename=str(FIGURES_DIR / "04_customer_personas_clustering.png")))

personas_df = pd.read_csv(REPORTS_DIR / "customer_personas_summary.csv")
display(personas_df[["cluster", "persona_title", "mean_budget_display", "mean_calls", "visit_booked_rate", "actual_conversion_rate"]])
"""))

# Task 5: SHAP
cells.append(nbf.v4.new_markdown_cell("""## Step 5: Explainability with SHAP for Both Models (Task 5)
We provide complete transparency with TreeExplainer SHAP for **both**:
1. **Lead Scoring Model:** Global beeswarm and local waterfall showing why a lead is Hot/Warm/Cold
2. **Property Valuation Model (Day 2 CatBoost):** Global beeswarm and local waterfall explaining price drivers
"""))

cells.append(nbf.v4.new_code_cell("""print("=== LEAD SCORING SHAP EXPLANATIONS ===")
display(Image(filename=str(FIGURES_DIR / "05_lead_shap_global_summary.png")))
display(Image(filename=str(FIGURES_DIR / "06_lead_shap_local_waterfall.png")))

print("=== PROPERTY VALUATION SHAP EXPLANATIONS ===")
display(Image(filename=str(FIGURES_DIR / "07_property_shap_global_summary.png")))
display(Image(filename=str(FIGURES_DIR / "08_property_shap_local_waterfall.png")))
"""))

# Fairness
cells.append(nbf.v4.new_markdown_cell("""## Step 6: Fairness & Unfair Bias Audit
We audit model selection rates and disparate impact ratios across **City** and **Lead Source** to verify demographic parity and prevent systematic exclusion.
"""))

cells.append(nbf.v4.new_code_cell("""display(Image(filename=str(FIGURES_DIR / "09_fairness_and_bias_audit.png")))

fairness_df = pd.read_csv(REPORTS_DIR / "fairness_bias_audit.csv")
display(fairness_df)
"""))

# Production Inference & Agent
cells.append(nbf.v4.new_markdown_cell("""## Step 7: Production Inference Engine & Week 7 Agent Tool Calling
We test the live inference engine and LangChain `@tool lead_scoring_tool` integrated into `week7-RE_Agent/day5-langgraph-agent`.
"""))

cells.append(nbf.v4.new_code_cell("""from lead_inference import LeadScoringEngine

engine = LeadScoringEngine()

sample_hot_lead = {
    "client_name": "Tariq Mahmood",
    "budget_pkr": 35000000.0,
    "preferred_city": "Islamabad",
    "property_type": "House",
    "purpose": "Buy",
    "number_of_calls": 5,
    "avg_call_duration_mins": 5.8,
    "response_time_hours": 0.2,
    "visit_booked": "Yes",
    "days_since_first_contact": 10,
    "objection_raised": "None",
    "lead_source": "WhatsApp",
}

res = engine.score_lead(sample_hot_lead)
print(res["consultation_statement"])
"""))

nb.cells = cells
nb_path = DAY3_DIR / "notebooks" / "day3_lead_scoring_classification.ipynb"
with open(nb_path, "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print(f"Jupyter Notebook successfully written to: {nb_path}")
