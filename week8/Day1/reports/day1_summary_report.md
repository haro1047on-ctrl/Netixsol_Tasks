# Week 8 — Day 1 Executive Summary: Data Understanding, EDA & Feature Engineering

## AI Property Valuation & Lead Scoring Platform for Real Estate
**Date:** September 2026  
**Status:** Completed & Validated (100% Pass)  
**Execution Runtime:** 10.52s End-to-End  

---

## 1. Project Background & Business Context

In Week 7, the AI Voice Agent automated hundreds of customer calls. However, our real estate client faced two critical operational bottlenecks:
1. **Inconsistent Pricing:** Agents quoted property valuations based on gut feeling, causing overpriced listings to stagnate for months while underpriced deals resulted in severe commission loss.
2. **Sales Team Inefficiency:** Sales agents treated all inbound inquiries equally, wasting hours chasing cold prospects while high-intent, qualified buyers cooled off.

**Day 1 Objective:** Build the data science and engineering foundation to power two core models:
- **Model A (Regression):** Predict fair market values for residential properties.
- **Model B (Classification):** Score inbound leads by their probability of successful conversion.

---

## 2. Task 1 — Data Collection & Documentation

Two realistic datasets reflecting the Pakistani real estate landscape and multi-channel CRM logs were established:
- **Dataset A — Property Listings (`data/raw/raw_properties.csv`):** 6,180 raw records across 5 primary metropolitan markets (Lahore, Islamabad, Karachi, Rawalpindi, Faisalabad). Includes diverse property types (Houses, Flats, Portions, Farmhouses, Penthouses), architectural attributes, amenities, and spatial proximity metrics.
- **Dataset B — Inbound CRM Leads (`data/raw/raw_leads.csv`):** 3,690 raw records across WhatsApp, Phone Calls, Web forms, and Facebook ads, capturing client budgets, call intensity, response latency, in-person visit scheduling, objections, and deal conversion outcomes.
- **Data Dictionary:** Formally authored at [`data/data_dictionary.md`](file:///d:/netixsol_work/week8/data/data_dictionary.md), specifying Column Names, Data Types, Descriptions, Native Units (PKR, Marla, Sq. Ft.), Sources, and Known Data Quality Issues.

---

## 3. Task 2 — Data Cleaning & Standardization

A production cleaner ([`src/data_cleaner.py`](file:///d:/netixsol_work/week8/src/data_cleaner.py)) resolves real-world Pakistani data anomalies:

### Cleaning Summary Table
| Issue Addressed | Methodology & Implementation | Results |
| :--- | :--- | :--- |
| **Missing Values (Properties)** | • `covered_area_sqft`: Imputed via median plot-to-covered ratio per `property_type`<br>• `bathrooms`: Imputed via median bathrooms per `(property_type, bedrooms)`<br>• `floors`: Imputed via property type defaults (House=2, Flat/Portion=1)<br>• `distance_to_hospital_km`: Imputed via median distance within the respective society | 100% complete; zero null values remaining. |
| **Missing Values (Leads)** | • `response_time_hours`: Imputed via median latency per `lead_source`<br>• `objection_raised`: Imputed as `"None"` | 100% complete. |
| **Duplicate Listings** | Deduplicated on unique tuple `(city, society, property_type, plot_size, bedrooms, price)` | 292 property duplicates removed.<br>90 lead duplicates removed. |
| **Currency Normalization** | Regex parser for Pakistani financial units:<br>• "Crore" / "Cr" $\to \times 10^7$<br>• "Lac" / "Lakh" $\to \times 10^5$<br>• "Thousand" / "K" $\to \times 10^3$ | Standardized to numeric `price_pkr` and `budget_pkr`. |
| **Land Area Normalization** | Standardized to Marla (225 sq ft) and Covered Area to Sq Ft:<br>• 1 Kanal $= 20$ Marla<br>• 1 Sq Yard $= 0.04$ Marla<br>• 1 Sq Ft $= 0.00444$ Marla | Uniform base metrics: `plot_size_marla` and `covered_area_sqft`. |
| **Location Standardization** | Fuzzy & regex map standardizing 89 colloquial variants (e.g. "DHA Ph 5", "DHA-5", "Gulberg 3", "F 7") | Normalized to 31 canonical residential societies. |
| **Outlier Detection & Removal** | Dual-stage filter:<br>1. Domain bounds (Price/Marla $\in [200\text{k}, 25\text{M}]\text{ PKR}$, Price $\ge 800\text{k}\text{ PKR}$)<br>2. Statistical IQR filter per `(city, property_type)` on `price_per_marla` ($10^{\text{th}}-90^{\text{th}}$ percentile with $2.5\times \text{IQR}$) | 146 domain outliers removed.<br>24 statistical IQR anomalies filtered.<br>5,718 high-quality properties retained. |

---

## 4. Task 4 — Feature Engineering (12 New Features)

Authored in [`src/feature_engineering.py`](file:///d:/netixsol_work/week8/src/feature_engineering.py), each feature targets a specific real estate pricing or behavioral conversion dynamic:

| Feature Name | Target Dataset | Formula / Logic | Business & Modeling Justification |
| :--- | :--- | :--- | :--- |
| `price_per_marla` | Properties | $\frac{\text{price\_pkr}}{\text{plot\_size\_marla}}$ | Fundamental micro-market rate metric. *Note: Strictly reserved for EDA and excluded from modeling features to avoid target leakage.* |
| `property_age_bucket` | Properties | `[0-1 yr: Brand New]`, `[2-5 yrs: Modern]`, `[6-15 yrs: Established]`, `[16+ yrs: Vintage]` | Captures non-linear physical depreciation; new finishes command substantial price premiums, while 16+ year structures face major demolition/renovation deductions. |
| `society_tier` | Properties | `Tier 1 - Elite`, `Tier 2 - Prime`, `Tier 3 - Developing` | Captures societal brand equity, underground cabling, security infrastructure, and municipal prestige independent of plot size. |
| `amenity_score` | Properties | Weighted index: Generator (2.0), Solar (2.0), Security (1.5), Servant Quarter (1.5), Lawn (1.0), Parking (1.0) | High energy tariffs and load shedding make solar/generators disproportionately valuable compared to simple amenity count. |
| `distance_composite_index` | Properties | $0.40 \cdot d_{\text{road}} + 0.30 \cdot d_{\text{hosp}} + 0.30 \cdot d_{\text{school}}$ | Consolidates collinear spatial metrics into a single urban accessibility barrier index. |
| `covered_to_plot_ratio` | Properties | $\frac{\text{covered\_area\_sqft}}{\text{plot\_size\_marla} \times 225}$ | Indicates construction density vs open garden/lawn space. |
| `bed_to_bath_ratio` | Properties | $\frac{\text{bedrooms}}{\text{bathrooms} + 0.001}$ | Modern Pakistani homes feature en-suite attached bathrooms ($1.0$ ratio). Ratios $>1.5$ indicate dated or lower-tier builds. |
| `is_luxury_plot` | Properties | Binary flag: Corner or Park-Facing | Captures ventilation, extra road frontage, and green view pricing uplift. |
| `lead_engagement_score` | Leads | $\text{number\_of\_calls} \times \text{avg\_call\_duration\_mins}$ | Quantifies cumulative prospect attention; higher voice conversation duration directly correlates with purchase intent. |
| `response_speed_category` | Leads | `Immediate (<15m)`, `Fast (15-60m)`, `Standard (1-6h)`, `Delayed (>6h)` | Quick agent response times prevent prospect cooling and prevent competition from closing the lead first. |
| `budget_to_market_ratio` | Leads | $\frac{\text{stated\_budget}}{\text{median\_market\_price}}$ | Identifies qualified buyers from unrealistic prospects who have budgets far below prevailing society market rates. |
| `interaction_intensity` | Leads | $\frac{\text{number\_of\_calls}}{\text{days\_since\_first\_contact} + 1}$ | Touchpoint velocity metric distinguishing actively engaged prospects from slow, dormant leads. |
| `objection_severity_score` | Leads | Ordinal score (0 = None, 1 = Family approval, ..., 4 = Price high / Low trust, 5 = Dropped) | Converts qualitative agent CRM friction notes into an ordinal feature for gradient boosted trees. |
| `is_high_intent` | Leads | Binary flag: `visit_booked == Yes` and `engagement_score >= 8.0` | Combines physical commitment with high voice engagement. |

---

## 5. Task 3 — Exploratory Data Analysis & Business Insights

Six high-resolution figures were generated in [`reports/figures/`](file:///d:/netixsol_work/week8/reports/figures/) via [`src/eda_visualizer.py`](file:///d:/netixsol_work/week8/src/eda_visualizer.py), each accompanied by a sharp business insight:

1. **Price Distribution (`01_price_distribution_raw_vs_log.png`):**
   - *Insight:* Raw property prices exhibit heavy right-skewness (skew=2.68); log-transformation normalizes variance, preventing regression models from ignoring budget homes.
2. **Price Per Marla by City and Society (`02_price_per_marla_by_city_society.png`):**
   - *Insight:* Sector F-7 (Islamabad) and Clifton (Karachi) command over 50-65 Lac/Marla—over 4x the rate of developing outskirts—proving location tier is the single strongest price driver.
3. **Correlation Heatmap (`03_correlation_heatmap.png`):**
   - *Insight:* Covered area (r=0.88) and plot size dominate property price, while lead engagement score (r=0.48) and low response time show strongest correlation with lead conversion.
4. **Effect of Bedrooms, Age, and Corner Plots (`04_effect_bedrooms_age_corner.png`):**
   - *Insight:* Brand new homes command an ~18% price premium over 6+ year structures, while properties boasting both corner and park-facing locations yield an average 16% valuation bonus.
5. **Lead Conversion by Source & Purpose (`05_conversion_rate_by_source_purpose.png`):**
   - *Insight:* Inbound WhatsApp and Direct Phone inquiries achieve 32-34% conversion—nearly 3x higher than Facebook paid ads (12.2%)—making conversational outreach the highest ROI channel.
6. **Class Imbalance in Leads (`06_class_imbalance_leads.png`):**
   - *Insight:* A 25.2% vs 74.8% class imbalance requires stratified train/val/test splitting and cost-sensitive loss (or SMOTE) so classifiers do not simply optimize for majority non-buyers.

---

## 6. Task 5 — Encoding, Scaling, Splitting & Reusable Pipelines

Authored in [`src/splitters.py`](file:///d:/netixsol_work/week8/src/splitters.py) and [`src/pipelines.py`](file:///d:/netixsol_work/week8/src/pipelines.py):

### A. One-Hot vs. Target Encoding Benchmark (High-Cardinality Societies)
Evaluating 31 unique residential societies on property valuation:
- **One-Hot Encoding:** Generates 31 sparse columns. 5-Fold Cross-Validated Ridge $R^2 = 0.3097 \pm 0.0407$.
- **Target Encoding (with 5-fold smoothing):** Generates **1 continuous column**. 5-Fold Cross-Validated Ridge $R^2 = 0.3109 \pm 0.0408$.
- **Architectural Conclusion:** Target Encoding yields a **96.8% dimensionality reduction** with identical explanatory power, avoiding matrix sparsity and mitigating overfitting in gradient-boosted decision trees.

### B. Data Leakage Audit
- **Properties Matrix:** `price_pkr` (target), `price_pkr_normalized`, `raw_price_str`, and crucially `price_per_marla` (which contains `price_pkr` in its numerator) were verified and dropped from the feature matrix $X$.
- **Leads Matrix:** `converted`, `converted_binary` (target), `lead_id`, `client_name`, `phone` (PII), and redundant raw strings were verified and dropped from $X$.
- **Audit Result:** **100% Passed (Zero Data Leakage).**

### C. 70 / 15 / 15 Train / Validation / Test Splits
- **Properties (5,718 rows):**
  - Train: 4,002 rows (69.99%) | Median Price: 1.34 Crore PKR
  - Validation: 858 rows (15.01%) | Median Price: 1.34 Crore PKR
  - Test: 858 rows (15.01%) | Median Price: 1.39 Crore PKR
- **Leads (Stratified on Conversion Target, 3,600 rows):**
  - Overall Conversion: 25.25%
  - Train: 2,520 rows (70.00%) | Conversion Rate: **25.24%**
  - Validation: 540 rows (15.00%) | Conversion Rate: **25.37%**
  - Test: 540 rows (15.00%) | Conversion Rate: **25.19%**
  - *Perfect class preservation achieved across all three partitions.*

### D. Production Scikit-Learn Pipelines
- **Property Preprocessor:** [`models/property_preprocessor.joblib`](file:///d:/netixsol_work/week8/models/property_preprocessor.joblib) (`StandardScaler` on numerical features, `OneHotEncoder` on low-cardinality categories, `TargetEncoder` on high-cardinality societies). Produces a dense 36-dimensional feature matrix.
- **Lead Preprocessor:** [`models/lead_preprocessor.joblib`](file:///d:/netixsol_work/week8/models/lead_preprocessor.joblib) (`StandardScaler` on continuous engagement metrics, `OneHotEncoder` on source/intent, binary passthrough on visit booked and high intent flag). Produces a dense 38-dimensional feature matrix.

---

## 7. Artifacts & Deliverables Registry

1. **Datasets:**
   - Raw: [`data/raw/raw_properties.csv`](file:///d:/netixsol_work/week8/data/raw/raw_properties.csv), [`data/raw/raw_leads.csv`](file:///d:/netixsol_work/week8/data/raw/raw_leads.csv)
   - Cleaned: [`data/processed/cleaned_properties.csv`](file:///d:/netixsol_work/week8/data/processed/cleaned_properties.csv), [`data/processed/cleaned_leads.csv`](file:///d:/netixsol_work/week8/data/processed/cleaned_leads.csv)
   - Partitions: `properties_train.csv`, `properties_val.csv`, `properties_test.csv`, `leads_train.csv`, `leads_val.csv`, `leads_test.csv`
2. **Documentation & Notebooks:**
   - Data Dictionary: [`data/data_dictionary.md`](file:///d:/netixsol_work/week8/data/data_dictionary.md)
   - EDA Insights Report: [`reports/eda_insights_report.md`](file:///d:/netixsol_work/week8/reports/eda_insights_report.md)
   - Interactive Jupyter Notebook: [`notebooks/day1_data_understanding_eda.ipynb`](file:///d:/netixsol_work/week8/notebooks/day1_data_understanding_eda.ipynb)
3. **Source Code Modules:**
   - Data Generator: [`src/data_generator.py`](file:///d:/netixsol_work/week8/src/data_generator.py)
   - Data Cleaner: [`src/data_cleaner.py`](file:///d:/netixsol_work/week8/src/data_cleaner.py)
   - Feature Engineering: [`src/feature_engineering.py`](file:///d:/netixsol_work/week8/src/feature_engineering.py)
   - EDA Visualizer: [`src/eda_visualizer.py`](file:///d:/netixsol_work/week8/src/eda_visualizer.py)
   - Splitters: [`src/splitters.py`](file:///d:/netixsol_work/week8/src/splitters.py)
   - Pipelines: [`src/pipelines.py`](file:///d:/netixsol_work/week8/src/pipelines.py)
   - Master Runner: [`run_day1.py`](file:///d:/netixsol_work/week8/run_day1.py)
4. **Fitted Model Pipelines:**
   - [`models/property_preprocessor.joblib`](file:///d:/netixsol_work/week8/models/property_preprocessor.joblib)
   - [`models/lead_preprocessor.joblib`](file:///d:/netixsol_work/week8/models/lead_preprocessor.joblib)
