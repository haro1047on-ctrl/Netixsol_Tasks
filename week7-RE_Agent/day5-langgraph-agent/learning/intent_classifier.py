import os
import pickle
import logging
from typing import Tuple, Optional
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from learning.dataset import get_training_data

logger = logging.getLogger("IntentClassifier")

MODEL_PATH = Path(__file__).resolve().parent / "model.pkl"
_pipeline: Optional[Pipeline] = None

def _load_model() -> None:
    """Load the model from disk if it exists."""
    global _pipeline
    if _pipeline is None and MODEL_PATH.exists():
        try:
            with open(MODEL_PATH, "rb") as f:
                _pipeline = pickle.load(f)
            logger.info("Loaded ML intent classifier from disk.")
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")

def predict(text: str) -> Tuple[Optional[str], float]:
    """Predict the intent of a text using the trained ML model."""
    _load_model()
    if _pipeline is None or not text.strip():
        return None, 0.0

    try:
        # Get probability distribution
        probas = _pipeline.predict_proba([text])[0]
        # Get best class
        best_idx = probas.argmax()
        confidence = probas[best_idx]
        intent = _pipeline.classes_[best_idx]
        return intent, confidence
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        return None, 0.0

def train(save: bool = True) -> Optional[dict]:
    """Train the classifier using data from SQLite."""
    global _pipeline
    df = get_training_data()
    
    if len(df) < 10:
        logger.warning("Not enough training data (need at least 10 examples). Skipping training.")
        return None
        
    X = df["user_message"]
    y = df["intent"]
    
    # Needs more than 1 class to train LogisticRegression
    if len(y.unique()) < 2:
        logger.warning("Need at least 2 distinct intents to train the model. Skipping.")
        return None

    # Train test split for evaluation
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Create and train pipeline
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), min_df=2)),
        ('clf', LogisticRegression(class_weight='balanced', random_state=42))
    ])
    
    pipeline.fit(X_train, y_train)
    
    # Evaluate
    score = pipeline.score(X_test, y_test)
    report = classification_report(X_test, y_test, output_dict=True, zero_division=0)
    
    # Update global model
    _pipeline = pipeline
    
    if save:
        try:
            with open(MODEL_PATH, "wb") as f:
                pickle.dump(pipeline, f)
            logger.info(f"Model saved to {MODEL_PATH}")
        except Exception as e:
            logger.error(f"Failed to save model: {e}")
            
    return {
        "accuracy": score,
        "report": report,
        "n_samples": len(df)
    }
