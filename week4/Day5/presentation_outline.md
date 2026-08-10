# Capstone Presentation Outline

**Target Audience:** Stakeholders (Business & Technical Leadership)
**Estimated Time:** 5-7 minutes

## Slide 1: Executive Summary
- **Business Goal:** Accurately predict whether an individual earns >50K to optimize targeted marketing and resource allocation.
- **The Challenge:** The dataset has a significant class imbalance (only ~24% earn >50K).
- **The Solution:** An ensemble Machine Learning model (Random Forest + Class Weighting) that balances precision and recall, backed by an interpretability framework.

## Slide 2: Data & Preprocessing Pipeline
- **Data Source:** Adult Census Income dataset (48k records).
- **Feature Engineering:** Created income-relevant features (e.g., `age_bucket`, `education_hours`, `has_capital_gain`).
- **Robust Pipeline:** Automated missing value imputation, scaling for numeric data, and one-hot encoding for categorical data to ensure no data leakage.

## Slide 3: Model Selection & Ensembles
- **Tested Models:** Random Forest, HistGradientBoosting, and a Stacking Ensemble.
- **Why Random Forest?** Offers excellent performance (ROC AUC ~ 0.89), naturally handles non-linear relationships, and provides built-in feature importance.
- **Evaluation:** Using F1-Score to ensure we don't over-index on the majority class.

## Slide 4: Addressing Class Imbalance
- **The Issue:** Models naturally favor the majority class (<=50K), leading to high false negatives (missing high earners).
- **Approaches Tested:** 
  - Class Weighting (`balanced`)
  - Random Under-Sampling
  - Synthetic Data Generation (SMOTE)
- **Winner:** Class Weighting provided the most stable Cross-Validation F1-score without the computational overhead of SMOTE.

## Slide 5: Interpretability & Fairness
- **Global Insights:** The top drivers of income are `capital-gain`, `age`, `education-num`, and `marital-status`.
- **Local Explanations (SHAP):** We can explain exactly *why* a specific user was classified as >50K or <=50K, providing transparency to our marketing team.
- **Fairness Observation:** Disparities exist across `sex` and `race` due to historical biases in the census data. We recommend monitoring these metrics in production to ensure the model doesn't amplify inequality.

## Slide 6: Deployment & Monitoring
- **End-to-End Inference:** Deployed a self-contained pipeline (`.joblib`) wrapped in a Python script capable of handling missing data and unseen categories gracefully.
- **Monitoring Checklist:**
  - **Data Drift:** Watch for shifts in the `age` or `education` distributions.
  - **Label Distribution:** Alert if the predicted >50K ratio drops below 20% or exceeds 30%.
  - **Retraining Cadence:** Re-evaluate model metrics quarterly or when drift alerts trigger.

## Slide 7: Next Steps & Q&A
- **A/B Testing:** Roll out the model to 10% of users and measure conversion lift vs. the baseline.
- **Feedback Loop:** Capture false positives/negatives to continuously improve the model.
- **Questions?**
