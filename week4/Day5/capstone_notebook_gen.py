import json
import os

notebook = {
    "cells": [
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "# Capstone Project — Ensembles, Imbalance Handling, Interpretability & Deployment\n",
                "\n",
                "This notebook brings together the final deliverables: ensemble modeling, handling class imbalance, and providing interpretability analyses on the Adult dataset."
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 1,
            "metadata": {},
            "outputs": [],
            "source": [
                "import os, json, time, joblib\n",
                "import numpy as np\n",
                "import pandas as pd\n",
                "import matplotlib.pyplot as plt\n",
                "import seaborn as sns\n",
                "from sklearn.datasets import fetch_openml\n",
                "from sklearn.model_selection import train_test_split, cross_validate, StratifiedKFold\n",
                "from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler\n",
                "from sklearn.impute import SimpleImputer\n",
                "from sklearn.pipeline import Pipeline\n",
                "from sklearn.compose import ColumnTransformer\n",
                "from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, StackingClassifier\n",
                "from sklearn.linear_model import LogisticRegression\n",
                "from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, precision_recall_curve, roc_curve, average_precision_score\n",
                "from imblearn.pipeline import Pipeline as ImbPipeline\n",
                "from imblearn.over_sampling import SMOTE\n",
                "from imblearn.under_sampling import RandomUnderSampler\n",
                "from sklearn.inspection import permutation_importance\n",
                "import shap\n",
                "shap.initjs()"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## 1. Load Data & Setup Preprocessing (Reuse from Day 4)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 2,
            "metadata": {},
            "outputs": [],
            "source": [
                "adult = fetch_openml(name='adult', version=2, as_frame=True)\n",
                "df = adult.frame.copy()\n",
                "df = df.replace('?', np.nan)\n",
                "df['target'] = df['class'].astype(str).str.strip().map({'<=50K': 0, '<=50K.': 0, '>50K': 1, '>50K.': 1})\n",
                "X = df.drop(columns=['class', 'target'])\n",
                "y = df['target'].astype(int)\n",
                "\n",
                "X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 3,
            "metadata": {},
            "outputs": [],
            "source": [
                "def create_engineered_features(X_df):\n",
                "    X = X_df.copy()\n",
                "    X['age_bucket'] = pd.cut(X['age'], bins=[0, 25, 35, 50, 65, 100], labels=['18-25', '26-35', '36-50', '51-65', '65+'], include_lowest=True)\n",
                "    X['hours_bucket'] = pd.cut(X['hours-per-week'], bins=[0, 20, 40, 60, 100], labels=['Part-Time', 'Full-Time', 'Overtime', 'Extreme'], include_lowest=True)\n",
                "    X['has_capital_gain'] = (X['capital-gain'] > 0).astype(int)\n",
                "    X['log_capital_gain'] = np.log1p(X['capital-gain'].fillna(0))\n",
                "    X['higher_education'] = X['education'].isin(['Bachelors', 'Masters', 'Doctorate', 'Prof-school']).astype(int)\n",
                "    X['education_hours'] = X['education-num'] * X['hours-per-week']\n",
                "    return X\n",
                "\n",
                "numeric_cols = ['age', 'fnlwgt', 'education-num', 'capital-gain', 'capital-loss', 'hours-per-week', 'log_capital_gain', 'education_hours']\n",
                "cat_cols = ['workclass', 'education', 'marital-status', 'occupation', 'relationship', 'race', 'sex', 'native-country', 'age_bucket', 'hours_bucket']\n",
                "binary_cols = ['has_capital_gain', 'higher_education']\n",
                "\n",
                "numeric_pipe = Pipeline([('imputer', SimpleImputer(strategy='median')), ('scaler', StandardScaler())])\n",
                "cat_pipe = Pipeline([('imputer', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])\n",
                "feature_adder = FunctionTransformer(create_engineered_features)\n",
                "preprocessor = ColumnTransformer([('num', numeric_pipe, numeric_cols), ('cat', cat_pipe, cat_cols), ('bin', 'passthrough', binary_cols)], remainder='drop')\n",
                "\n",
                "base_preproc = Pipeline([('add_feats', feature_adder), ('preproc', preprocessor)])\n",
                "\n",
                "X_train_prep = base_preproc.fit_transform(X_train)\n",
                "X_test_prep = base_preproc.transform(X_test)\n",
                "feature_names = numeric_cols + list(base_preproc.named_steps['preproc'].named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(cat_cols)) + binary_cols"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Task 1: Train & Compare Ensemble Models"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 4,
            "metadata": {},
            "outputs": [],
            "source": [
                "rf = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, max_features='log2', max_depth=5, random_state=42, n_jobs=-1)\n",
                "gb = HistGradientBoostingClassifier(max_iter=50, max_depth=3, learning_rate=0.03, l2_regularization=0.0, random_state=42)\n",
                "lr = LogisticRegression(solver='liblinear', penalty='l1', C=0.1, random_state=42)\n",
                "stack = StackingClassifier(estimators=[('rf', rf), ('gb', gb)], final_estimator=lr, n_jobs=-1)\n",
                "\n",
                "models = {'RandomForest': rf, 'HistGradientBoosting': gb, 'Stacking': stack}\n",
                "results = {}\n",
                "\n",
                "for name, model in models.items():\n",
                "    start = time.time()\n",
                "    model.fit(X_train_prep, y_train)\n",
                "    inf_start = time.time()\n",
                "    preds = model.predict(X_test_prep)\n",
                "    probs = model.predict_proba(X_test_prep)[:, 1]\n",
                "    inf_time = time.time() - inf_start\n",
                "    \n",
                "    results[name] = {\n",
                "        'Precision': precision_score(y_test, preds),\n",
                "        'Recall': recall_score(y_test, preds),\n",
                "        'F1': f1_score(y_test, preds),\n",
                "        'ROC_AUC': roc_auc_score(y_test, probs),\n",
                "        'Inference_Time': inf_time\n",
                "    }\n",
                "\n",
                "pd.DataFrame(results).T"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Task 2: Systematically Address Class Imbalance"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 5,
            "metadata": {},
            "outputs": [],
            "source": [
                "cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)\n",
                "\n",
                "rf_cw = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, max_features='log2', max_depth=5, random_state=42, class_weight='balanced', n_jobs=-1)\n",
                "pipe_cw = ImbPipeline([('model', rf_cw)])\n",
                "\n",
                "rus = RandomUnderSampler(random_state=42)\n",
                "pipe_rus = ImbPipeline([('rus', rus), ('model', rf)])\n",
                "\n",
                "smote = SMOTE(random_state=42)\n",
                "pipe_smote = ImbPipeline([('smote', smote), ('model', rf)])\n",
                "\n",
                "imb_pipelines = {'Class_Weight': pipe_cw, 'RandomUnderSampler': pipe_rus, 'SMOTE': pipe_smote}\n",
                "imb_results = {}\n",
                "\n",
                "for name, pipe in imb_pipelines.items():\n",
                "    cv_res = cross_validate(pipe, X_train_prep, y_train, cv=cv, scoring='f1', n_jobs=-1)\n",
                "    pipe.fit(X_train_prep, y_train)\n",
                "    preds = pipe.predict(X_test_prep)\n",
                "    imb_results[name] = {\n",
                "        'CV_F1': cv_res['test_score'].mean(),\n",
                "        'Holdout_F1': f1_score(y_test, preds)\n",
                "    }\n",
                "\n",
                "pd.DataFrame(imb_results).T"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 6,
            "metadata": {},
            "outputs": [],
            "source": [
                "final_model = imb_pipelines['Class_Weight'].named_steps['model']\n",
                "final_pipeline = Pipeline([('preproc', base_preproc), ('model', final_model)])\n",
                "joblib.dump(final_pipeline, 'final_model_pipeline.joblib')\n",
                "print('Model saved!')"
            ]
        },
        {
            "cell_type": "markdown",
            "metadata": {},
            "source": [
                "## Task 3: Interpretability & Fairness Checks"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 7,
            "metadata": {},
            "outputs": [],
            "source": [
                "pi = permutation_importance(final_model, X_test_prep[:1000], y_test.iloc[:1000], n_repeats=5, random_state=42, n_jobs=-1)\n",
                "pi_df = pd.DataFrame({'Feature': feature_names, 'Importance': pi.importances_mean}).sort_values('Importance', ascending=False)\n",
                "pi_df.head(8)"
            ]
        },
        {
            "cell_type": "code",
            "execution_count": 8,
            "metadata": {},
            "outputs": [],
            "source": [
                "# SHAP Local Explanations (TreeExplainer for RF)\n",
                "explainer = shap.TreeExplainer(final_model)\n",
                "shap_values = explainer.shap_values(X_test_prep[:100])\n",
                "if isinstance(shap_values, list):\n",
                "    shap_values_pos = shap_values[1]\n",
                "elif len(shap_values.shape) == 3:\n",
                "    shap_values_pos = shap_values[:, :, 1]\n",
                "else:\n",
                "    shap_values_pos = shap_values\n",
                "shap.summary_plot(shap_values_pos, X_test_prep[:100], feature_names=feature_names, max_display=8)"
            ]
        }
    ],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {
                "name": "ipython",
                "version": 3
            },
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.8.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open(r"d:\Netixsol\week5\Capstone\capstone.ipynb", "w", encoding='utf-8') as f:
    json.dump(notebook, f, indent=4)
print("capstone.ipynb generated successfully.")
