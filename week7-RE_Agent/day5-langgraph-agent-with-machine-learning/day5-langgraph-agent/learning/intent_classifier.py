"""Loads whatever model `train_intent_classifier.py` last promoted, and
serves predictions to `nodes/intent_detection_node.py`.

Fails soft everywhere: if scikit-learn isn't installed, or no model has
been trained yet, or the model file is missing, `predict()` returns
(None, 0.0) and the caller is expected to fall back to the rule engine.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("LangGraphAgent")

MODELS_DIR = Path(__file__).resolve().parent / "models"
POINTER_PATH = MODELS_DIR / "current_model.json"

_lock = threading.Lock()
_cached_model = None
_cached_model_path: Optional[str] = None


def _load_model():
    global _cached_model, _cached_model_path
    with _lock:
        if not POINTER_PATH.exists():
            return None
        try:
            pointer = json.loads(POINTER_PATH.read_text(encoding="utf-8"))
            model_path = pointer.get("model_path")
        except Exception as exc:
            logger.warning(f"[learning.intent_classifier] bad pointer file: {exc}")
            return None

        if not model_path or not Path(model_path).exists():
            return None

        if _cached_model is not None and _cached_model_path == model_path:
            return _cached_model

        try:
            import joblib
            _cached_model = joblib.load(model_path)
            _cached_model_path = model_path
            logger.info(f"[learning.intent_classifier] loaded model {model_path}")
            return _cached_model
        except ImportError:
            logger.warning("[learning.intent_classifier] scikit-learn/joblib not installed; ML fallback disabled.")
            return None
        except Exception as exc:
            logger.warning(f"[learning.intent_classifier] failed to load model: {exc}")
            return None


def predict(text: str, min_confidence: float = 0.55) -> Tuple[Optional[str], float]:
    """Predict an intent for `text`. Returns (None, 0.0) if unavailable or
    below `min_confidence` — callers should treat that as "no opinion".
    """
    text = (text or "").strip()
    if not text:
        return None, 0.0

    model = _load_model()
    if model is None:
        return None, 0.0

    try:
        proba = model.predict_proba([text])[0]
        classes = model.classes_
        best_idx = proba.argmax()
        confidence = float(proba[best_idx])
        intent = str(classes[best_idx])
        if confidence < min_confidence:
            return None, confidence
        return intent, confidence
    except Exception as exc:
        logger.warning(f"[learning.intent_classifier] prediction failed: {exc}")
        return None, 0.0


def model_info() -> Optional[dict]:
    """Small helper for a status endpoint / debugging."""
    if not POINTER_PATH.exists():
        return None
    try:
        return json.loads(POINTER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
