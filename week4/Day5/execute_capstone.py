import os
import json
import time
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.datasets import fetch_openml
from sklearn.model_selection import train_test_split, cross_validate, StratifiedKFold
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, StackingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score, precision_recall_curve, roc_curve, average_precision_score
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.over_sampling import SMOTE
from imblearn.under_sampling import RandomUnderSampler
from sklearn.inspection import permutation_importance
import shap

OUT_DIR = r"d:\Netixsol\week5\Capstone"
os.makedirs(OUT_DIR, exist_ok=True)

# 1. Load Data
print("Loading data...")
adult = fetch_openml(name='adult', version=2, as_frame=True)
df = adult.frame.copy()
df = df.replace('?', np.nan)
df['target'] = df['class'].astype(str).str.strip().map({'<=50K': 0, '<=50K.': 0, '>50K': 1, '>50K.': 1})
X = df.drop(columns=['class', 'target'])
y = df['target'].astype(int)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

# Preprocessing
def create_engineered_features(X_df):
    X = X_df.copy()
    X['age_bucket'] = pd.cut(X['age'], bins=[0, 25, 35, 50, 65, 100], labels=['18-25', '26-35', '36-50', '51-65', '65+'], include_lowest=True)
    X['hours_bucket'] = pd.cut(X['hours-per-week'], bins=[0, 20, 40, 60, 100], labels=['Part-Time', 'Full-Time', 'Overtime', 'Extreme'], include_lowest=True)
    X['has_capital_gain'] = (X['capital-gain'] > 0).astype(int)
    X['log_capital_gain'] = np.log1p(X['capital-gain'].fillna(0))
    X['higher_education'] = X['education'].isin(['Bachelors', 'Masters', 'Doctorate', 'Prof-school']).astype(int)
    X['education_hours'] = X['education-num'] * X['hours-per-week']
    return X

numeric_cols = ['age', 'fnlwgt', 'education-num', 'capital-gain', 'capital-loss', 'hours-per-week', 'log_capital_gain', 'education_hours']
cat_cols = ['workclass', 'education', 'marital-status', 'occupation', 'relationship', 'race', 'sex', 'native-country', 'age_bucket', 'hours_bucket']
binary_cols = ['has_capital_gain', 'higher_education']

numeric_pipe = Pipeline([('imputer', SimpleImputer(strategy='median')), ('scaler', StandardScaler())])
cat_pipe = Pipeline([('imputer', SimpleImputer(strategy='most_frequent')), ('onehot', OneHotEncoder(handle_unknown='ignore', sparse_output=False))])
feature_adder = FunctionTransformer(create_engineered_features)
preprocessor = ColumnTransformer([('num', numeric_pipe, numeric_cols), ('cat', cat_pipe, cat_cols), ('bin', 'passthrough', binary_cols)], remainder='drop')

base_preproc = Pipeline([('add_feats', feature_adder), ('preproc', preprocessor)])

# Transform training data to speed up experiments
print("Fitting preprocessor...")
X_train_prep = base_preproc.fit_transform(X_train)
X_test_prep = base_preproc.transform(X_test)
feature_names = numeric_cols + list(base_preproc.named_steps['preproc'].named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(cat_cols)) + binary_cols

# Task 1: Train Ensembles
print("Task 1: Training Models...")
rf = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, max_features='log2', max_depth=5, random_state=42, n_jobs=-1)
gb = HistGradientBoostingClassifier(max_iter=50, max_depth=3, learning_rate=0.03, l2_regularization=0.0, random_state=42)
lr = LogisticRegression(solver='liblinear', penalty='l1', C=0.1, random_state=42)
stack = StackingClassifier(estimators=[('rf', rf), ('gb', gb)], final_estimator=lr, n_jobs=-1)

models = {'RandomForest': rf, 'HistGradientBoosting': gb, 'Stacking': stack}
results = {}

for name, model in models.items():
    start_time = time.time()
    model.fit(X_train_prep, y_train)
    inf_start = time.time()
    preds = model.predict(X_test_prep)
    probs = model.predict_proba(X_test_prep)[:, 1]
    inf_time = time.time() - inf_start
    
    results[name] = {
        'Precision': precision_score(y_test, preds),
        'Recall': recall_score(y_test, preds),
        'F1': f1_score(y_test, preds),
        'ROC_AUC': roc_auc_score(y_test, probs),
        'Inference_Time': inf_time
    }

print("Task 1 Results:", results)

# Task 2: Class Imbalance
print("Task 2: Class Imbalance (CV)...")
cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)

# 1. Class Weight (using RF)
rf_cw = RandomForestClassifier(n_estimators=200, min_samples_leaf=2, max_features='log2', max_depth=5, random_state=42, class_weight='balanced', n_jobs=-1)
pipe_cw = ImbPipeline([('model', rf_cw)])

# 2. Random Under Sampling
rus = RandomUnderSampler(random_state=42)
pipe_rus = ImbPipeline([('rus', rus), ('model', rf)])

# 3. SMOTE
smote = SMOTE(random_state=42)
pipe_smote = ImbPipeline([('smote', smote), ('model', rf)])

imb_pipelines = {'Class_Weight': pipe_cw, 'RandomUnderSampler': pipe_rus, 'SMOTE': pipe_smote}
imb_results = {}

for name, pipe in imb_pipelines.items():
    cv_res = cross_validate(pipe, X_train_prep, y_train, cv=cv, scoring='f1', n_jobs=-1)
    pipe.fit(X_train_prep, y_train)
    preds = pipe.predict(X_test_prep)
    imb_results[name] = {
        'CV_F1': cv_res['test_score'].mean(),
        'Holdout_F1': f1_score(y_test, preds)
    }

print("Task 2 Results:", imb_results)

# Best model selection: we will pick the Stacking model for the final pipeline, but the prompt asks to pick one approach for imbalance.
# Let's say Class_Weight is chosen.
final_model = imb_pipelines['Class_Weight'].named_steps['model']
final_pipeline = Pipeline([('preproc', base_preproc), ('model', final_model)])
print("Saving final pipeline...")
joblib.dump(final_pipeline, os.path.join(OUT_DIR, 'final_model_pipeline.joblib'))

# Task 3: Interpretability
print("Task 3: Interpretability...")
# Permutation Importance
pi = permutation_importance(final_model, X_test_prep[:1000], y_test.iloc[:1000], n_repeats=5, random_state=42, n_jobs=-1)
pi_df = pd.DataFrame({'Feature': feature_names, 'Importance': pi.importances_mean}).sort_values('Importance', ascending=False)
print("Top 8 features by permutation importance:\n", pi_df.head(8))

# Save results for report
with open(os.path.join(OUT_DIR, 'results.json'), 'w') as f:
    json.dump({'task1': results, 'task2': imb_results, 'top_features': pi_df.head(8).to_dict()}, f)

print("Script completed successfully.")
