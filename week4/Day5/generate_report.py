import os
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

def create_report():
    out_path = r"d:\Netixsol\week5\Capstone\executive_report.pdf"
    results_path = r"d:\Netixsol\week5\Capstone\results.json"
    
    metrics = {}
    if os.path.exists(results_path):
        with open(results_path, 'r') as f:
            metrics = json.load(f)
            
    c = canvas.Canvas(out_path, pagesize=letter)
    width, height = letter
    
    # Page 1
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "Capstone Executive Report")
    
    c.setFont("Helvetica", 12)
    y = height - 90
    
    text1 = (
        "Business Goal:\n"
        "The objective of this project is to accurately predict whether an individual earns >50K "
        "annually using demographic and employment data. A robust predictive model allows the "
        "business to better target marketing campaigns and optimize resource allocation for "
        "high-value customers."
    )
    for line in text1.split('\n'):
        lines = simpleSplit(line, "Helvetica", 12, width - 100)
        for l in lines:
            c.drawString(50, y, l)
            y -= 15
    y -= 15
    
    text2 = (
        "Data Used:\n"
        "We used the Adult Census Income dataset containing approximately 48,000 records. "
        "The dataset suffers from a significant class imbalance, with only ~24% of individuals "
        "falling into the >50K category. A robust preprocessing pipeline was applied to handle "
        "missing values, one-hot encode categorical variables, and scale numeric features."
    )
    for line in text2.split('\n'):
        lines = simpleSplit(line, "Helvetica", 12, width - 100)
        for l in lines:
            c.drawString(50, y, l)
            y -= 15
    y -= 15
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Task 1: Ensemble Models & Task 2: Class Imbalance")
    y -= 20
    c.setFont("Helvetica", 12)
    
    text3 = (
        "We trained and compared Random Forest, HistGradientBoosting, and a Stacking Ensemble. "
        "To handle class imbalance, we evaluated Class Weighting, Random Under-Sampling, and "
        "SMOTE using 3-fold cross-validation."
    )
    for line in text3.split('\n'):
        lines = simpleSplit(line, "Helvetica", 12, width - 100)
        for l in lines:
            c.drawString(50, y, l)
            y -= 15
    y -= 15
    
    if 'task2' in metrics:
        c.drawString(50, y, "Imbalance Strategy Performance (F1 Score):")
        y -= 15
        for strat, res in metrics['task2'].items():
            c.drawString(70, y, f"- {strat}: CV = {res['CV_F1']:.4f}, Holdout = {res['Holdout_F1']:.4f}")
            y -= 15
    y -= 15
    
    text4 = (
        "Chosen Model & Deployment Artifact:\n"
        "The Random Forest model with 'balanced' class weights provided the most stable "
        "F1-score across CV folds without the heavy computational overhead of SMOTE. "
        "This model was bundled with the preprocessing steps into 'final_model_pipeline.joblib'."
    )
    for line in text4.split('\n'):
        lines = simpleSplit(line, "Helvetica", 12, width - 100)
        for l in lines:
            c.drawString(50, y, l)
            y -= 15
            
    c.showPage()
    
    # Page 2
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Task 3: Interpretability & Fairness Findings")
    y -= 20
    c.setFont("Helvetica", 12)
    
    text5 = (
        "Global Explanations:\n"
        "Permutation Importance and SHAP values revealed the most influential features. "
        "The top drivers for predicting high income are capital-gain, education-num, age, "
        "marital-status, and hours-per-week. Local SHAP explanations successfully isolated "
        "why specific individuals were classified as True Positives or False Negatives."
    )
    for line in text5.split('\n'):
        lines = simpleSplit(line, "Helvetica", 12, width - 100)
        for l in lines:
            c.drawString(50, y, l)
            y -= 15
    y -= 15
    
    if 'top_features' in metrics:
        c.drawString(50, y, "Top Features (Permutation Importance):")
        y -= 15
        top_feats = metrics['top_features']['Feature']
        for i, feat in enumerate(top_feats.values()):
            c.drawString(70, y, f"{i+1}. {feat}")
            y -= 15
    y -= 15
    
    text6 = (
        "Fairness Observations:\n"
        "A check across protected groups (sex, race) shows disparities in the raw data, "
        "which the model reflects. Women and minority groups have lower >50K predictions "
        "due to historical biases present in the training set. Mitigations include threshold "
        "adjustments per group in production."
    )
    for line in text6.split('\n'):
        lines = simpleSplit(line, "Helvetica", 12, width - 100)
        for l in lines:
            c.drawString(50, y, l)
            y -= 15
    y -= 15
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Recommended Next Steps & Monitoring")
    y -= 20
    c.setFont("Helvetica", 12)
    
    text7 = (
        "1. Deploy inference.py behind a REST API for real-time scoring.\n"
        "2. A/B Test Plan: Route 10% of marketing traffic to the model's predictions and "
        "compare conversion rates against the baseline strategy.\n"
        "3. Monitoring Strategy:\n"
        "   - Monitor Data Drift (e.g. shifts in age/education histograms).\n"
        "   - Monitor Label Distribution (alert if predicted >50K ratio exceeds 30%).\n"
        "   - Retrain model quarterly or when performance degrades."
    )
    for line in text7.split('\n'):
        lines = simpleSplit(line, "Helvetica", 12, width - 100)
        for l in lines:
            c.drawString(50, y, l)
            y -= 15
            
    c.save()

if __name__ == "__main__":
    create_report()
