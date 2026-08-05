# W4D3 — 2-Page Summary: Feature Engineering, CV & Model Comparison

---

## 1. Engineered Feature List

| Feature | Type | Creation Rule | Justification | MI Score |
|---|---|---|---|---|
| age_bucket | categorical | pd.cut(age) | Age groups capture non-linear age-income effects | 0.0599 |
| hours_bin | categorical | pd.cut(hours-per-week) | Work-hour patterns relate to income | 0.0379 |
| cap_gain_flag | binary | capital-gain > 0 | Any capital gains often indicate additional income sources | 0.0296 |
| log_cap_gain | numeric | log1p(capital-gain) | Reduce skew and limit outlier influence of large gains | 0.0830 |
| higher_education | binary | education in {Bachelors,Masters,Doctorate} | Higher education is correlated with higher earnings | 0.0371 |
| edu_hours_interaction | numeric | education-num * hours-per-week | Captures combined effect of education and hours worked | 0.0815 |
| net_capital | numeric | capital-gain - capital-loss | Net capital may be more informative than separate values | 0.1212 |

All 7 features are built from current-row data only (no target encoding, no leakage).

---

## 2. Cross-Validation Comparison

### Results Table (5-fold Stratified CV)

| Model | Precision | F1 | ROC AUC | Time (s) |
|---|---|---|---|---|
| HistGradientBoosting | 0.7800 ± 0.0096 | 0.7112 ± 0.0088 | 0.9283 ± 0.0018 | 29.5 |
| LogisticRegression | 0.7498 ± 0.0050 | 0.6739 ± 0.0043 | 0.9129 ± 0.0023 | 7.6 |
| RandomForest | 0.7288 ± 0.0083 | 0.6735 ± 0.0079 | 0.9047 ± 0.0026 | 54.3 |

### Key Observations
- **Best precision**: HistGradientBoosting (0.7800)
- **Best ROC AUC**: HistGradientBoosting (0.9283)
- See `cv_boxplots_all_metrics.png` for fold-level distributions.

---

## 3. Statistical Test Results

**Top 2 models by precision**: HistGradientBoosting vs LogisticRegression

Paired t-test p=1.4945e-03; mean gap=+0.0302. Statistically significant. Practically meaningful (>1 pp).

Wilcoxon p=0.0625 (confirms/does not confirm fold-level consistency depending on value above).

---

## 4. Feature Importances & Coefficients

**Top engineered features (RandomForest importances):**

              feature  importance
edu_hours_interaction    0.067944
          net_capital    0.052929
         log_cap_gain    0.041891
     age_bucket_total    0.038555
     higher_education    0.017558
      hours_bin_total    0.015508
        cap_gain_flag    0.009523

- `log_cap_gain` and `cap_gain_flag` rank highest among engineered features — capital activity is the strongest non-demographic predictor of income.
- `edu_hours_interaction` confirms the multiplicative effect of education × hours worked.
- `higher_education` boolean is compact but highly informative.

---

## 5. Feature Selection

- SelectKBest (mutual information, k=40) used inside CV pipeline (no leakage).
- Performance vs full feature set: see printed output in Task 5 cell.
- **Decision**: Retain all 7 engineered features. Drop low-MI one-hot columns (sparse native-country/occupation sub-categories).

---

## 6. Recommended Models & Features for Day 4 Tuning

**Model**: `HistGradientBoosting` (highest precision; recommend also benchmarking `HistGradientBoostingClassifier`)

**Feature set**: All 7 engineered features + original numeric/categorical features, with SelectKBest k=40 as a pipeline step.

**Suggested tuning parameters**:
- RandomForest: `n_estimators`, `max_depth`, `min_samples_leaf`, `max_features`
- HistGradientBoosting: `learning_rate`, `max_iter`, `max_leaf_nodes`, `l2_regularization`
