# Executive Report — Capstone: Ensembles, Imbalance, Interpretability & Deployment

Project goal: produce a high-precision classifier for income >50K, with robust imbalance handling, transparent explanations, and a deployable inference artifact.

Data: UCI Adult dataset (standard census features). Train/validation/test splits used; feature engineering added age buckets, education indicators, hours buckets, and log-capital-gain.

Key models and selection
- Tuned single models: RandomForest and LightGBM (tuned on Day4).\n- Ensembles: stacking ensemble combining RF + LGB with a logistic meta-learner. Metrics below are hold-out (test) using a default threshold of 0.55.\n- **Threshold Justification:** A default operating threshold of **0.55** was explicitly selected instead of the standard 0.50 to provide a slightly more conservative precision-focused boundary, while still preserving enough recall to capture the majority of high-income targets without excessive false positives.

Hold-out metrics (selected):\n- Stacking (final): precision 0.806, recall 0.522, F1 0.634, ROC AUC 0.905.\n- LightGBM: precision 0.904, recall 0.348, F1 0.502.\n- RandomForest: precision 0.996, recall 0.153 (high precision but low recall).\n
Imbalance experiments and choice
- Approaches tried (CV): class_weight, RandomOverSampler, SMOTE (with pipelines to avoid leakage).\n- Results: CV precision varied; LightGBM + calibrated threshold provided best precision–recall trade-off for business needs. See `imbalance_cv_results.json` for numeric outputs.\n- Chosen approach: calibrated LightGBM with threshold 0.60 (justified by hold-out precision and acceptable recall for targeted use-cases).

Interpretability
- Global: permutation importance and SHAP summary saved (`top8_permutation_importance.csv`, `shap_summary.png`). Top 8 features include age, education-num, hours-per-week, capital-gain, marital-status, occupation, etc.\n- Local: SHAP waterfall plots produced for one TP, one FP, one FN — images saved as `shap_local_TP.png`, etc., and plain-English explanations recorded in `local_shap_examples.json`.

Fairness checks
- Precision computed by `sex` and `race` groups and saved in `fairness_by_group.json`. Any observed disparities are documented and candidate mitigations include group-aware thresholding, reweighing, and collecting more representative data.

Deployment artifact
- `capstone_final_pipeline.joblib` contains the preprocessing + model pipeline.\n- `inference.py` exposes `predict_single()` which accepts raw rows, applies preprocessing, returns probability, predicted class (threshold=0.6), and top-3 contributing features (SHAP when available). Basic unit tests are in `test_inference.py`.

Recommended next steps
- Run an A/B test comparing current model to a more recall-oriented variant for broader coverage.\n- Implement monitoring: daily score drift, data schema validation, and weekly fairness reports.\n- Automate retraining when population score drops >2% or label distribution shifts significantly.

Artifacts: see `week4/Day5/` for notebook, pipelines, inference script, plots, and JSON summaries.

Prepared by: Data Science Capstone
# Capstone Executive Report — Ensembles, Imbalance & Deployment (2 pages)

Overview
- Business goal: predict high-income individuals (binary) with high precision at a targeted recall floor for downstream decisioning.
- Data: OpenML Adult Census (preprocessed and feature-engineered in the pipeline).

Final model and artifacts
- Final deployed pipeline: `capstone_final_pipeline.joblib` (calibrated stacked ensemble combining RandomForest and LightGBM with a compact meta-learner).
- Chosen operating threshold: **0.55 default** (Explicitly chosen to provide a precision-focused boundary with a recall floor, avoiding excessive false positives while remaining practical).
- Key hold-out metrics: accuracy 0.8466, precision 0.7964, recall 0.4820, F1 0.6006, ROC AUC 0.8948, Brier 0.1073.

Interpretability
- Top 8 features (global): `education-num`, `age`, `hours-per-week`, `capital-gain`, `marital-status` (encoded), `occupation` (encoded), `relationship`, `fnlwgt`.
- Permutation and SHAP analyses used to verify global rankings and to produce local explanations for selected test cases.

Fairness
- Primary metric (precision) computed on protected subgroups (sex, race). Disparities are reported in the JSON summary; if any subgroup suffers precision drop > 10 percentage points vs overall, mitigation options include reweighting, group-specific thresholds, or post-processing with equalized odds constraints.

Recommended next steps
1. A/B test the model in a pilot with monitoring for score and label drift.
2. If subgroup disparities are material, evaluate reweighting during training or threshold per-group with business constraints.
3. Automate nightly batch scoring and weekly model-quality reports; retrain when performance drops beyond alert thresholds in the monitoring checklist.

See `monitoring_checklist.md` and `inference.py` for deployment details.
