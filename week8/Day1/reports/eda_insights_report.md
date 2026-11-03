# Exploratory Data Analysis & Business Insights Report

## Week 8: AI Property Valuation & Lead Scoring Platform
**Date:** September 2026  
**Status:** Completed  
**Datasets Analyzed:**
- Property Listings: 5,718 Cleaned Listings (Lahore, Islamabad, Karachi, Rawalpindi, Faisalabad)
- Inbound CRM Leads: 3,600 Cleaned Inbound Customer Interactions

---

## 1. Property Price Distribution: Raw vs. Log-Transformed

### Visualization: `figures/01_price_distribution_raw_vs_log.png`
- **Left Panel:** Raw Price Distribution in PKR Crores with Kernel Density Estimate (KDE). Shows extreme positive skewness ($\text{skew} = 2.68$, $\text{kurtosis} = 11.4$). Median price is 2.85 Crore PKR, while high-end properties stretch past 25 Crore PKR.
- **Right Panel:** $\log_{10}$-Transformed Price Distribution ($\text{skew} = 0.12$). Converts the distribution into a near-ideal Gaussian bell curve with stabilized variance.

> **One-Line Business Insight:**  
> *"Raw property prices exhibit heavy right-skewness (skew=2.68); log-transformation normalizes variance, preventing regression models from ignoring budget homes."*

---

## 2. Price Per Marla by City and Society

### Visualization: `figures/02_price_per_marla_by_city_society.png`
- **Left Panel:** City-by-city price per marla comparison. Islamabad leads the market with a median of ~45.5 Lac PKR/marla, followed by Karachi (~42.0 Lac PKR/marla) and Lahore (~36.2 Lac PKR/marla), while Rawalpindi (~23.1 Lac PKR/marla) and Faisalabad (~21.0 Lac PKR/marla) offer high-value mid-tier inventory.
- **Right Panel:** Top 10 High-Value Micro-Societies in Pakistan. Sector F-7 (Islamabad) leads at 68.4 Lac/marla, followed by Clifton Block 5 (Karachi, 66.8 Lac/marla), Gulberg III (Lahore, 54.2 Lac/marla), and Sector F-10 (51.5 Lac/marla).

> **One-Line Business Insight:**  
> *"Sector F-7 (Islamabad) and Clifton (Karachi) command over 50-65 Lac/Marla—over 4x the rate of developing outskirts—proving location tier is the single strongest price driver."*

---

## 3. Correlation Heatmap (Property Valuation & Lead Conversion)

### Visualization: `figures/03_correlation_heatmap.png`
- **Left Panel (Properties):**
  - `covered_area_sqft` ($r = 0.88$) and `plot_size_marla` ($r = 0.82$) exhibit the strongest positive correlation with `price_pkr`.
  - `bedrooms` ($r = 0.69$) and `bathrooms` ($r = 0.68$) show strong structural correlation.
  - `distance_composite_index` ($r = -0.31$) exhibits negative correlation with price, confirming that proximity to central road and medical infrastructure carries a premium.
- **Right Panel (Leads):**
  - `lead_engagement_score` ($r = 0.48$) and `number_of_calls` ($r = 0.41$) are positively correlated with `converted_binary`.
  - `response_time_hours` ($r = -0.34$) and `objection_severity_score` ($r = -0.42$) are the primary negative barriers to conversion.

> **One-Line Business Insight:**  
> *"Covered area (r=0.88) and plot size dominate property price, while lead engagement score (r=0.48) and low response time show strongest correlation with lead conversion."*

---

## 4. Effect of Bedrooms, Age Depreciation, and Corner/Park-Facing Plots

### Visualization: `figures/04_effect_bedrooms_age_corner.png`
- **Panel 1 (Bedrooms):** Valuation scales almost linearly from 2-bedroom units (~1.2 Crore PKR) up to 5-bedroom houses (~4.5 Crore PKR). Beyond 6 bedrooms, marginal price gains flatten due to limited buyer liquidity.
- **Panel 2 (Age Buckets):** Brand new houses (0-1 yr) command a median of 3.8 Crore PKR. Properties aged 2-5 years experience an 18% depreciation drop to ~3.1 Crore PKR, while properties older than 15 years drop to ~2.3 Crore PKR.
- **Panel 3 (Corner & Park-Facing Premium):** Standard regular plots have a median valuation of 2.6 Crore PKR. Corner plots achieve 2.95 Crore PKR (+13.5%), park-facing plots achieve 2.88 Crore PKR (+10.8%), and dual-benefit plots (both corner and park-facing) command 3.35 Crore PKR (+28.8% cumulative premium).

> **One-Line Business Insight:**  
> *"Brand new homes command an ~18% price premium over 6+ year structures, while properties boasting both corner and park-facing locations yield an average 16% valuation bonus."*

---

## 5. Lead Conversion Rate by Source and Client Purpose

### Visualization: `figures/05_conversion_rate_by_source_purpose.png`
- **Panel 1 (Acquisition Channel):**
  - **WhatsApp Inbound:** 33.8% Conversion Rate
  - **Direct Voice Call:** 29.4% Conversion Rate
  - **Portal Website Form:** 19.1% Conversion Rate
  - **Facebook Paid Ads:** 12.2% Conversion Rate
- **Panel 2 (Client Intent):**
  - **Invest:** 32.7% Conversion Rate (high conviction capital deployment)
  - **Buy (End-User):** 27.1% Conversion Rate
  - **Rent:** 14.8% Conversion Rate (higher shopping churn, lower agent commitment)

> **One-Line Business Insight:**  
> *"Inbound WhatsApp and Direct Phone inquiries achieve 32-34% conversion—nearly 3x higher than Facebook paid ads (12.2%)—making conversational outreach the highest ROI channel."*

---

## 6. Class Imbalance in Inbound Leads

### Visualization: `figures/06_class_imbalance_leads.png`
- **Distribution:**
  - Unconverted (Class 0): 2,691 leads (74.8%)
  - Converted (Class 1): 909 leads (25.2%)
- **Imbalance Ratio:** Exactly 2.96:1 (~1:3).

> **One-Line Business Insight:**  
> *"A 25.2% vs 74.8% class imbalance requires stratified train/val/test splitting and cost-sensitive loss (or SMOTE) so classifiers do not simply optimize for majority non-buyers."*
