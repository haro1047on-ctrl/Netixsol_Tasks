# Model Tuning, Regularization & Reproducible Pipelines Report

## Overview
This report documents the Day 4 workflow for the Adult Census Income classification task. The notebook in this folder builds a reproducible preprocessing-and-modeling pipeline, tunes candidate models with randomized search, diagnoses bias and variance with learning curves, evaluates probability calibration, selects an operating threshold, and saves a final model artifact for inference.

This document is written as a concise 1–2 page summary of the work completed, with a focus on the search process, diagnostic interpretation, and final performance results.

## Summary of the work
The workflow covers all required Day 4 tasks:
- reproducible pipeline construction with fixed random seeds and documented library versions
- randomized hyperparameter search for multiple model families
- learning-curve analysis to diagnose possible overfitting or underfitting
- calibration and threshold selection for deployment-oriented decision making
- final test-set evaluation and artifact saving for inference

## Task 1 — Reproducible pipelines
The notebook uses a single scikit-learn pipeline composed of:
- feature engineering via FunctionTransformer
- imputation and scaling for numeric features
- imputation and one-hot encoding for categorical features
- a classifier step for the selected model

All randomness is controlled through a fixed random seed set as RANDOM_STATE = 42. The notebook also records the library versions used for scikit-learn, pandas, numpy, and joblib. A short README-style note explains how to rerun the training workflow from top to bottom.

## Task 2 — Hyperparameter search
Three model families are tuned with RandomizedSearchCV using stratified cross-validation:
- Logistic Regression: penalty and C
- Random Forest: n_estimators, max_depth, min_samples_leaf, and max_features
- Gradient Boosting: learning_rate, max_iter, max_depth, and l2_regularization

The search uses 5-fold cross-validation rather than a smaller 3-fold setup, which provides a more stable estimate of validation performance. The best estimator from each search is compared on the validation set, and the strongest candidate is selected for calibration and final evaluation. The notebook also records the best parameter settings from each search so the tuning decisions are explicit rather than implicit.

## Task 3 — Overfitting and underfitting diagnosis
Learning curves are generated for:
- Logistic Regression with different values of C
- Random Forest with different max_depth values

These curves help distinguish between underfitting and overfitting behavior. In practice:
- if validation performance remains low while training performance is high, the model is overfitting and should be regularized more strongly or made shallower
- if both train and validation scores are low, the model is underfitting and may need a weaker regularization setting, a deeper tree, or more informative features

The updated notebook includes both training and validation precision curves on the same chart, which makes the diagnosis much clearer. This is important because the earlier version only showed validation curves, which made bias and variance interpretation harder.

## Task 4 — Probability calibration and threshold selection
Probability calibration is evaluated with a calibration plot and Brier score. The notebook uses CalibratedClassifierCV with sigmoid calibration to improve probability reliability. The calibration step is interpreted carefully: the Brier score improves from 0.1157 to 0.1012, which indicates better probability quality overall, but the calibration curve still shows mid-range distortion, so the improvement is real but not perfect.

After calibration, a threshold sweep is performed over validation probabilities with a recall floor of 0.50 and a precision-first ranking. This makes the operating point more aligned with the business goal of keeping precision high while still retaining acceptable recall. The selected threshold is 0.60.

## Task 5 — Final evaluation and saved artifact
The final calibrated model is evaluated on the untouched test set. The notebook reports:
- accuracy: 0.8466
- precision: 0.7964
- recall: 0.4820
- F1 score: 0.6006
- ROC AUC: 0.8948
- Brier score: 0.1073
- confusion matrix: [[5358, 216], [908, 845]]
- selected decision threshold: 0.60

These results show that the tuned model performs strongly on the precision-oriented operating point, although the recall remains moderate. That is consistent with the chosen threshold and the business objective of favouring precision over a very aggressive positive prediction rule.

The final pipeline is saved as an artifact in the same folder:
- adult_tuned_pipeline.joblib

The notebook also writes a small JSON summary file containing the best model, validation precision, selected threshold, and final test metrics.

## Reproduction steps
1. Open the notebook in this folder.
2. Run each cell in order.
3. Review the generated plots and saved artifacts in the Day 4 folder.
4. Use the saved joblib object for inference on new records.

## Deliverables
- Notebook: model_tuning_day4.ipynb
- Saved model artifact: adult_tuned_pipeline.joblib
- Summary artifacts: tuning_results.json and plotting outputs such as learning_curve_logistic.png and calibration_plot.png
