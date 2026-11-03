# Week 8 — Day 2 Evaluation Report: Property Valuation Model (Regression)

## AI Property Valuation & Fair Market Pricing Platform
**Date:** September 2026  
**Status:** Completed & Production Validated (100% Pass)  
**Primary Models Evaluated:** 9 Models (*Baselines, Linear Regularized, Random Forest, XGBoost, LightGBM, CatBoost*)  
**Champion Model:** Optuna-Tuned CatBoost Regressor ($R^2 = 0.9880$, $\text{MAPE} = 6.25\%$)  
**Registered in MLflow Registry:** `PropertyValuationModel` (Version 1)  
**Week 7 Agent Integration:** Fully Connected via `property_valuation_tool` in `ALL_TOOLS`

---

## 1. Scenario & Problem Statement

Our client's sales team struggled with subjective property valuations:
- Quoting prices based on agent gut feeling led to overpriced listings that stagnated on portals for months, and underpriced properties that cost the brokerage substantial commission.
- When prospective buyers or sales managers asked: **"Is plot ki sahi qeemat kya honi chahiye?"**, agents lacked empirical data to justify asking prices.

**Day 2 Objective:** Train, evaluate, tune, and register a production Machine Learning regression model that predicts fair market prices in Pakistani Rupee (PKR), bounds every valuation with a confidence range, classifies asking prices as *Underpriced*, *Fair*, or *Overpriced*, and exposes the model directly to the Week 7 Real Estate AI Agent.

---

## 2. Tasks 1 & 2 — Baseline and Advanced Model Comparison

All models were evaluated on the held-out test set ($N = 858$ listings, 15.0% of the dataset). The target was trained on $\log(1 + \text{price})$ to stabilize right-skewness and evaluated on native PKR scale.

### Comprehensive Model Comparison Table (Test Set Evaluation)
| Model Name | Architecture Type | Test $R^2$ | Test MAE (PKR) | Test RMSE (PKR) | Test MAPE (%) | Training Time |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **CatBoost (Tuned)** | **Gradient Boosted Trees** | **0.9880** | **17.02 Lac** | **41.15 Lac** | **6.25%** | **1.94s** |
| **CatBoost (Default)** | Gradient Boosted Trees | 0.9837 | 18.19 Lac | 46.22 Lac | 6.45% | 1.88s |
| **LightGBM (Tuned)** | Gradient Boosted Trees | 0.9851 | 18.58 Lac | 44.82 Lac | 6.86% | 0.42s |
| **LightGBM (Default)** | Gradient Boosted Trees | 0.9818 | 19.34 Lac | 48.82 Lac | 7.03% | 0.37s |
| **XGBoost** | Gradient Boosted Trees | 0.9751 | 20.18 Lac | 57.12 Lac | 7.20% | 1.12s |
| **Random Forest** | Bagged Decision Trees | 0.9463 | 30.61 Lac | 83.83 Lac | 9.89% | 2.96s |
| **Lasso Regression** | L1 Regularized Linear | 0.4456 | 64.27 Lac | 2.69 Crore | 16.17% | 0.01s |
| **Ridge Regression** | L2 Regularized Linear | 0.4355 | 64.59 Lac | 2.72 Crore | 16.26% | 0.01s |
| **Linear Regression** | Ordinary Least Squares | 0.3881 | 65.17 Lac | 2.83 Crore | 16.20% | 0.02s |
| **Mean Baseline** | Naive Dummy | -0.0041 | 1.84 Crore | 3.62 Crore | 136.55% | 0.00s |
| **Median Baseline** | Naive Dummy | -0.1006 | 1.67 Crore | 3.79 Crore | 74.91% | 0.00s |

### Key Baseline Takeaway
Linear and regularized models explain only $38-44\%$ of variance because Pakistani real estate exhibits non-linear feature interactions (e.g. plot size multiplied by society tier and corner status). The advanced tree-based ensembles (CatBoost and LightGBM) capture these non-linearities, reducing MAPE from **16.2%** down to **6.25%** and achieving an $R^2$ of **0.9880**.

---

## 3. Task 3 — Evaluation & Granular Error Slice Analysis

Visualizations were rendered to [`reports/figures/`](file:///d:/netixsol_work/week8/Day2/reports/figures/):
- **Figure 07 (`07_actual_vs_predicted_models.png`):** 2x2 scatter plots of Actual vs Predicted prices with the $45^\circ$ parity line. Shows tight adherence for CatBoost/LightGBM with minimal variance across budget and luxury segments.
- **Figure 08 (`08_error_by_city_and_price_tier.png`):** Error breakdown across geographic markets and price tiers.

### Error Analysis by Metropolitan City
| Metropolitan City | Test Listings | Mean Absolute Error (PKR) | MAPE (%) | Median City Price (PKR) |
| :--- | :---: | :---: | :---: | :---: |
| **Rawalpindi** | 172 | 12.17 Lac | **5.94%** | 1.19 Crore |
| **Lahore** | 145 | 17.43 Lac | **6.20%** | 1.89 Crore |
| **Karachi** | 181 | 18.85 Lac | **6.20%** | 1.56 Crore |
| **Faisalabad** | 206 | 12.37 Lac | **6.68%** | 1.06 Crore |
| **Islamabad** | 154 | 32.64 Lac | **7.23%** | 1.87 Crore |

### Error Analysis by Price Tier (Where does the model fail?)
| Price Tier | Range | Test Listings | MAE (PKR) | MAPE (%) | Median Price (PKR) | Failure Mode Diagnosis |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Budget** | $<1.5\text{ Crore}$ | 449 | 5.23 Lac | **6.25%** | 84.0 Lac | Highly standardized housing; low error. |
| **Mid-Market** | $1.5 - 4.0\text{ Crore}$ | 282 | 14.64 Lac | **6.00%** | 2.24 Crore | **Lowest relative error (best performance).** |
| **Luxury** | $>4.0\text{ Crore}$ | 127 | 71.86 Lac | **8.15%** | 6.20 Crore | Higher variance due to custom imported fittings, high-end interior architecture, and unique landscape features not fully captured by basic tabular attributes. |

> **Diagnostic Conclusion:** The model maintains sub-7% relative error across 85% of standard residential listings. For ultra-luxury properties ($>4\text{ Crore}$), the model's confidence band widens to $\pm 10-12\%$ to communicate this intrinsic architectural uncertainty.

---

## 4. Task 4 — Hyperparameter Tuning & MLflow Experiment Tracking

Using Optuna Bayesian Optimization (20 trials per model family), we optimized validation RMSE on:
- **LightGBM:** `learning_rate=0.048`, `n_estimators=245`, `num_leaves=38`, `max_depth=6`, `subsample=0.88`, `colsample_bytree=0.82`, `reg_alpha=0.12`, `reg_lambda=0.45`.
- **CatBoost:** `learning_rate=0.065`, `iterations=280`, `depth=6`, `l2_leaf_reg=4.2`.

### MLflow Logging Architecture
- **Tracking URI:** `sqlite:///mlflow.db`
- **Experiment:** `Week8_Property_Valuation`
- **Logged Entities:**
  - Full hyperparameter configurations
  - Test and validation metrics (`test_r2`, `test_mae_pkr`, `test_rmse_pkr`, `test_mape_pct`)
  - Training duration (seconds)
  - Feature tags (36 engineered dimensions)
  - Serialized model artifacts via cloudpickle
- **Model Registry:** The winning model (`Tuned_CatBoost`) was registered as:
  - **Model Name:** `PropertyValuationModel`
  - **Version:** 1
  - **Stage:** Production

---

## 5. Task 5 — Price Range & Confidence (Quantile Prediction Intervals)

Instead of a fragile point estimate, the platform employs **Quantile Regression** ($10^{\text{th}}$ and $90^{\text{th}}$ percentiles) to return a bounded confidence range and automated market verdict:

### Market Verdict Classification Logic
$$\text{Variance \%} = \frac{\text{Listed Price} - \hat{y}_{\text{pred}}}{\hat{y}_{\text{pred}}} \times 100\%$$
- **Underpriced (Hot Deal!):** $\text{Listed Price} < Q_{0.10} \times 0.97$ (Demand is significantly below fair market value).
- **Fair Market Price:** $Q_{0.10} \le \text{Listed Price} \le Q_{0.90}$ (Demand falls within standard bounds).
- **Overpriced:** $\text{Listed Price} > Q_{0.90} \times 1.03$ (Demand is inflated relative to market comparables).

### Live Consultation Examples
1. **Scenario: Overpriced Listing Assessment**
   - **Property:** 10 Marla House in DHA Phase 5 Lahore, Listed at **4.90 Crore PKR**.
   - **Predicted Fair Price:** **4.22 Crore PKR** (Confidence Range: **4.01 Crore to 4.58 Crore**).
   - **Verdict:** **Overpriced by ~16.1%**.
   - **English Summary:** *"Predicted: 4.22 crore (range 4.01 crore to 4.58 crore). Listed at 4.90 crore -> Overpriced by ~16.1%."*
   - **UrduLish Consultation:** *"Sahi market qeemat: 4.22 crore (range 4.01 crore se 4.58 crore tak). Demand 4.90 crore hai jo ke market se ~16.1% mehngi (overpriced) hai."*

2. **Scenario: Manager Asking "Is plot ki sahi qeemat kya honi chahiye?"**
   - **Property:** 1 Kanal (20 Marla) House in Sector F-7 Islamabad.
   - **Predicted Fair Price:** **13.36 Crore PKR** (Range: **11.44 Crore to 15.72 Crore**).
   - **English Summary:** *"Fair Market Valuation: 13.36 crore (expected range: 11.44 crore to 15.72 crore)."*
   - **UrduLish Consultation:** *"Is property ki sahi market qeemat: 13.36 crore hai (expected range: 11.44 crore se 15.72 crore tak)."*

---

## 6. Week 7 RE Agent Extension & Integration

As requested, all Week 8 capabilities directly extend the Week 7 Agent:
1. **Tool Definition:** [`week7-RE_Agent/day5-langgraph-agent/tools/valuation_tool.py`](file:///d:/netixsol_work/week7-RE_Agent/day5-langgraph-agent/tools/valuation_tool.py) defines `property_valuation_tool` and `evaluate_property_valuation_core`.
2. **Tool Registry:** Registered in `ALL_TOOLS` in [`tools/__init__.py`](file:///d:/netixsol_work/week7-RE_Agent/day5-langgraph-agent/tools/__init__.py).
3. **Recommendation Enrichment:** Updated [`recommendation_node.py`](file:///d:/netixsol_work/week7-RE_Agent/day5-langgraph-agent/nodes/recommendation_node.py) to automatically evaluate each retrieved property with the Week 8 ML engine, appending the market verdict to the voice TTS output:
   *Example Voice Output:* *"Option 1: 10 marla House in T & T Aabpara, price 1.05 crore, 3 bedrooms (AI Market Verdict: Underpriced (Hot Deal!))."*
4. **Integration Test Suite:** Executed [`test_valuation_agent_integration.py`](file:///d:/netixsol_work/week7-RE_Agent/day5-langgraph-agent/test_valuation_agent_integration.py) with **100% Pass** across tool registry check, direct invocation, question answering, and recommendation node integration.
