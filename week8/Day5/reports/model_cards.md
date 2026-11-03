# Formal Model Cards: Real Estate AI Valuation & Lead Prioritization Platform

**Document Version:** 1.0.0  
**Date:** September 2026  
**Standards:** Mitchell et al. (2019) Model Cards for Model Reporting  

---

## 1. Model Card: Property Valuation Regressor (`PropertyValuationModel`)

### 1.1 Model Details
- **Developer:** Lead AI/ML Platform Engineer
- **Model Date:** September 2026
- **Model Version:** `v1.0.0` (Registered in MLflow Model Registry)
- **Model Architecture:** CatBoost Regressor (Decision Trees with Symmetric Trees) coupled with dual Quantile Regressors ($\alpha=0.10$ and $\alpha=0.90$) for uncertainty intervals.
- **Tuning Framework:** Optuna Bayesian Optimization over 20 iterations.
- **License:** Proprietary Enterprise Commercial License.

### 1.2 Intended Use
- **Primary Use Case:** Automated Fair Market Value (FMV) estimation of residential properties in Pakistani metropolitan areas (Lahore, Islamabad, Karachi, Rawalpindi, Faisalabad).
- **Secondary Use Case:** Detecting mispriced inventory to classify listings into *Underpriced (Hot Deal)*, *Fair Market Price*, and *Overpriced*.
- **Primary Users:** Real estate brokers, sales agents, acquisition managers, and voice AI bots.
- **Out-of-Scope Uses:** Commercial high-rises, unapproved rural farmland, litigation-disputed land, and certified legal bank appraisals.

### 1.3 Factors, Datasets & Preprocessing
- **Training Dataset:** 4,002 cleaned property listings reflecting authentic Pakistani market dynamics.
- **Held-out Test Dataset:** 858 listings (15.0% held-out test split).
- **Input Dimensions:** 36 preprocessed features across physical dimensions (plot size, covered area, room counts), architectural age, amenities, spatial transit distances, and society brand tiers.
- **Target Variable:** $\log(1 + \text{price\_pkr})$ to stabilize extreme right-skewness (skew=2.68), evaluated on native PKR scale.
- **Categorical Handling:** High-cardinality residential societies (31 canonical locations) encoded via 5-Fold Smoothed Target Encoding (96.8% dimensionality reduction vs One-Hot Encoding).

### 1.4 Performance Metrics (Test Set Evaluation)
| Metric | Benchmark Target | Model Score | Evaluation Interpretation |
| :--- | :---: | :---: | :--- |
| **Coefficient of Determination ($R^2$)** | $\ge 0.900$ | **0.9880** | Explains 98.8% of market variance. |
| **Mean Absolute Percentage Error (MAPE)** | $< 15.0\%$ | **6.25%** | Exceeds SLA; average error is well under 7%. |
| **Mean Absolute Error (MAE)** | — | **17.02 Lac PKR** | Median error on typical residential listing. |
| **Root Mean Squared Error (RMSE)** | — | **41.15 Lac PKR** | Penalizes severe outlier mispredictions. |
| **Inference Latency** | $< 500$ ms | **12.4 ms** | Suitable for real-time voice call synthesis. |

### 1.5 Slice Performance (Where does the model struggle?)
- **Budget Segment ($<1.5$ Crore):** Highly standardized builds; MAPE = **6.25%**.
- **Mid-Market ($1.5 - 4.0$ Crore):** Lowest relative error; MAPE = **6.00%**.
- **Luxury Segment ($>4.0$ Crore):** MAPE = **8.15%**. Custom architectural finishes, imported fixtures, and designer interiors introduce greater variance. The model automatically widens its confidence bounds to $\pm 10-12\%$ to communicate this uncertainty.

### 1.6 Ethical Considerations & Disclaimers
- Automated valuations are statistical estimations and carry a mandatory legal disclaimer: *"Not a legal or certified bank valuation."*
- Out-of-Distribution checks reject inputs $<1.0$ Marla or $>80.0$ Marla to prevent speculative extrapolations.

---

## 2. Model Card: Lead Scoring & Conversion Classifier (`LeadScoringModel`)

### 2.1 Model Details
- **Developer:** Lead AI/ML Platform Engineer
- **Model Date:** September 2026
- **Model Version:** `v1.0.0` (Registered in MLflow Model Registry)
- **Model Architecture:** LightGBM Gradient Boosted Trees with Cost-Sensitive Class Weighting (`scale_pos_weight=2.96`).
- **Explainability Engine:** SHAP (Shapley Additive Explanations) TreeExplainer with bilingual UrduLish natural language generator.
- **Clustering Engine:** K-Means Customer Persona Segmenter ($k=4$).

### 2.2 Intended Use
- **Primary Use Case:** Triage high-volume inbound CRM inquiries (WhatsApp, Phone Calls, Web, Facebook) to prioritize the Top 20% most qualified prospects for immediate human telephone outreach.
- **Primary Users:** Inside Sales Representatives (SDRs), Senior Closers, CRM Automation workflows.
- **Operational Tiers:**
  - 🔥 **Hot ($p \ge 0.65$):** 1-Hour SLA. Immediate direct voice call.
  - 🌤 **Warm ($0.35 \le p < 0.65$):** 24-Hour SLA. WhatsApp property brochures and objection handling.
  - ❄️ **Cold ($p < 0.35$):** Automated Nurture. Enrolled in weekly WhatsApp drip campaign.

### 2.3 Training Data & Class Imbalance
- **Dataset:** 3,600 cleaned omnichannel customer inquiries.
- **Class Imbalance:** 25.24% Converted vs. 74.76% Non-Converted.
- **Splitting Strategy:** 70/15/15 Stratified train/val/test split to preserve natural minority conversion distribution.
- **Why Accuracy is Rejected:** A naive majority-class dummy model achieves **74.8% accuracy** with **0% recall**, which would cause total business failure. PR-AUC and Recall are the primary governing metrics.

### 2.4 Performance Metrics (Test Set Evaluation)
| Metric | Benchmark Target | Model Score | Evaluation Interpretation |
| :--- | :---: | :---: | :--- |
| **Precision-Recall AUC (PR-AUC)** | $> 0.400$ | **0.5619** | Substantial positive predictive density above base rate. |
| **ROC-AUC** | $> 0.700$ | **0.7710** | Strong discriminative separation across classes. |
| **Positive Class Recall** | $> 50.0\%$ | **61.76%** | Captures 62% of all converting buyers (vs 41% unweighted). |
| **Precision@Top-20%** | $> 50.0\%$ | **61.11%** | In the top quintile, over 61% of leads convert. |
| **Lift@Top-20%** | $> 2.0\text{x}$ | **2.43x Lift** | 2.43 times more efficient than random calling. |
| **Brier Calibration Score** | $< 0.200$ | **0.1566** | Well-calibrated probabilities matching empirical close rates. |

### 2.5 Fairness & Bias Audit
- **Geographic Parity:** Selection rates range from 28.4% (Karachi) to 33.1% (Islamabad), matching ground truth conversion trends. The **Disparate Impact Ratio is 0.86**, well above the legal 0.80 adverse impact boundary.
- **Channel Parity:** Evaluated across WhatsApp, Call, Web, and Facebook. WhatsApp leads exhibit higher natural commitment, but no acquisition channel is structurally penalized.
