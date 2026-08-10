import os
import joblib
import pandas as pd
import numpy as np
import sys

def create_engineered_features(X_df):
    X = X_df.copy()
    X['age_bucket'] = pd.cut(X['age'], bins=[0, 25, 35, 50, 65, 100], labels=['18-25', '26-35', '36-50', '51-65', '65+'], include_lowest=True)
    X['hours_bucket'] = pd.cut(X['hours-per-week'], bins=[0, 20, 40, 60, 100], labels=['Part-Time', 'Full-Time', 'Overtime', 'Extreme'], include_lowest=True)
    X['has_capital_gain'] = (X['capital-gain'] > 0).astype(int)
    X['log_capital_gain'] = np.log1p(X['capital-gain'].fillna(0))
    X['higher_education'] = X['education'].isin(['Bachelors', 'Masters', 'Doctorate', 'Prof-school']).astype(int)
    X['education_hours'] = X['education-num'] * X['hours-per-week']
    return X

# Fix for joblib unpickling when the function was saved from a different __main__
setattr(sys.modules['__main__'], 'create_engineered_features', create_engineered_features)

class InferenceModel:
    def __init__(self, model_path):
        """Load the pre-trained pipeline."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        self.pipeline = joblib.load(model_path)
        self.preprocessor = self.pipeline.named_steps['preproc']
        self.model = self.pipeline.named_steps['model']
        
        # Get feature names from preprocessor
        numeric_cols = ['age', 'fnlwgt', 'education-num', 'capital-gain', 'capital-loss', 'hours-per-week', 'log_capital_gain', 'education_hours']
        cat_cols = ['workclass', 'education', 'marital-status', 'occupation', 'relationship', 'race', 'sex', 'native-country', 'age_bucket', 'hours_bucket']
        binary_cols = ['has_capital_gain', 'higher_education']
        
        # The OneHotEncoder feature names
        ohe_features = list(self.preprocessor.named_steps['preproc'].named_transformers_['cat'].named_steps['onehot'].get_feature_names_out(cat_cols))
        self.feature_names = numeric_cols + ohe_features + binary_cols

    def predict_single(self, input_dict, threshold=0.5):
        """
        Predict for a single raw input row (dict).
        Returns probability, predicted class, and top-3 contributing features (approx using feature importances for now).
        """
        df = pd.DataFrame([input_dict])
        
        # Basic Validation
        required_cols = ['age', 'workclass', 'fnlwgt', 'education', 'education-num', 'marital-status',
                         'occupation', 'relationship', 'race', 'sex', 'capital-gain', 'capital-loss',
                         'hours-per-week', 'native-country']
        
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Predict
        prob = self.pipeline.predict_proba(df)[0][1]
        pred_class = 1 if prob >= threshold else 0
        
        # Top 3 features approximation (since full SHAP on pipeline is slow, we use base feature importances)
        # Note: In a real system we'd use shap.TreeExplainer on the transformed data.
        transformed_data = self.preprocessor.transform(df)
        
        # Using feature importances from Random Forest
        importances = self.model.feature_importances_
        # Multiply by the transformed values to get a rough local contribution
        contributions = importances * transformed_data[0]
        
        top_3_indices = np.argsort(np.abs(contributions))[-3:][::-1]
        top_3_features = [(self.feature_names[i], round(contributions[i], 4)) for i in top_3_indices]
        
        return {
            'probability': round(prob, 4),
            'prediction': pred_class,
            'top_3_features': top_3_features
        }

if __name__ == "__main__":
    # Example usage
    sample_data = {
        'age': 39,
        'workclass': 'State-gov',
        'fnlwgt': 77516,
        'education': 'Bachelors',
        'education-num': 13,
        'marital-status': 'Never-married',
        'occupation': 'Adm-clerical',
        'relationship': 'Not-in-family',
        'race': 'White',
        'sex': 'Male',
        'capital-gain': 2174,
        'capital-loss': 0,
        'hours-per-week': 40,
        'native-country': 'United-States'
    }
    
    try:
        infer = InferenceModel('final_model_pipeline.joblib')
        res = infer.predict_single(sample_data, threshold=0.55)
        print("Inference Result:", res)
    except Exception as e:
        print("Error:", e)
