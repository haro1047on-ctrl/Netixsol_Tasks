# Two-Page Summary — Engineered Features & Model Comparison

## Executive Summary

- Objective: Introduce engineered features, evaluate model performance with 5-fold stratified CV, perform paired statistical comparisons, and recommend the model and feature set to use for hyperparameter tuning.
- Key takeaway: (Paste final chosen model and short rationale here.)

## Engineered Features (brief)

1. `age_bucket` — grouped age into career stages (18-25, 26-35, 36-50, 51-65, 65+). Rationale: career stage often correlates with income.
2. `hours_bucket` — grouped weekly hours (Part-Time, Full-Time, Overtime, Extreme). Rationale: more hours often correspond to higher earnings.
3. `has_capital_gain` — binary indicator if `capital-gain` > 0. Rationale: any capital gains strongly associated with higher income.
4. `log_capital_gain` — log(1 + `capital-gain`) to reduce skew. Rationale: preserves signal while controlling outliers.
5. `higher_education` — binary (Bachelors/Masters/Doctorate/Prof-school). Rationale: degree level correlates with earning potential.
6. `education_hours` — interaction `education-num * hours-per-week`. Rationale: captures combined effect of education and workload.

(Include the Mutual Information scores and feature dictionary from the notebook here.)

## Cross-Validation Results

- Method: 5-fold stratified cross-validation with identical preprocessing pipeline (feature engineering in `FunctionTransformer`, imputation, scaling, one-hot encoding).

- Models evaluated:
  - Logistic Regression
  - Random Forest
  - HistGradientBoosting

- Paste the cross-validation summary table (mean ± std for Accuracy, Precision, Recall, F1, ROC AUC) from the notebook here.

Example (replace with values from notebook):

| Model | Accuracy | Precision | Recall | F1 | ROC AUC |
|---|---:|---:|---:|---:|---:|
| Random Forest | 0.XXX ± 0.XXX | ... | ... | ... | ... |
| HistGradientBoosting | 0.XXX ± 0.XXX | ... | ... | ... | ... |
| Logistic Regression | 0.XXX ± 0.XXX | ... | ... | ... | ... |


## Statistical Comparison

- Test used: Wilcoxon signed-rank test (paired, non-parametric) on fold-by-fold F1 scores — appropriate for n=5 paired observations.

- Primary comparison: top two models by mean F1 (table above). Reported statistic and p-value:

  - Top model: (paste `top1`)
  - Second model: (paste `top2`)
  - Wilcoxon statistic: (paste) — p = (paste)
  - Mean F1 difference (top1 - top2): (paste)

- Logistic Regression comparison: Wilcoxon statistic and p-value between Logistic and top model: (paste)

Interpretation guidance (use these rules):
- If p < 0.05 and the mean difference is practically meaningful (e.g., > 0.005–0.01 in F1 depending on domain), prefer the higher-performing model.
- If p >= 0.05, there is no statistical evidence of a consistent difference — prefer the simpler or faster model (often Logistic Regression) unless operational needs demand the slightly higher-performing model.

## Feature Importance & Selection

- Logistic Regression coefficients and Random Forest importances were inspected to identify which engineered features contributed strongly. (Paste top engineered features and their coefficients/importances.)

- SelectKBest with Mutual Information (k=30) was applied to reduce dimensionality. Paste the list of selected features and note how many engineered features were retained.

## Training Time Comparison

- Measured training times (seconds):

| Pipeline | Training Time (s) |
|---|---:|
| Original Random Forest | (paste measured time) |
| Random Forest + SelectKBest | (paste measured time) |

Interpretation: If feature selection produces similar CV performance while reducing training time, prefer the reduced feature set for hyperparameter tuning.

## Recommendation & Next Steps

- Recommendation: (state recommended model and feature set — e.g., "Use HistGradientBoosting on selected features for tuning because it shows statistically significant improvement", or "Use Logistic Regression if differences are not significant and interpretability/speed is preferred").

- Next steps:
  1. Run a hyperparameter search (e.g., randomized or Bayesian) on the selected model and feature set.
  2. Validate final model on the held-out test set and report final metrics and calibration.
  3. Produce a short model spec and monitoring plan for production.

## Appendix

- Full feature dictionary and Mutual Information table (copy/paste from notebook).
- Full cross-validation per-fold scores (copy/paste `cv_results` contents) for reproducibility.

---

File: week4/Day3/two_page_summary.md

Please paste the numeric outputs from the notebook into the placeholders above to complete the two-page summary.
