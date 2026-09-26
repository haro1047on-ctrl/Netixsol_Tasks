"""Batch-retrain the intent classifier from every call logged so far.

Run this periodically (nightly/weekly cron, Task Scheduler, or a manual
`python -m learning.train_intent_classifier`) — NOT on every call. See
learning/README.md for scheduling instructions.

What it does:
    1. Loads every (utterance -> intent) example logged by the live agent
       since the last run (learning/data/intent_training_log.jsonl).
    2. Trains a small TF-IDF + Logistic Regression pipeline (handles the
       mixed English / Roman Urdu / Urdu-script text the agent already
       deals with; no GPU, trains in seconds even on tens of thousands
       of rows).
    3. Evaluates it on a held-out split.
    4. Only "promotes" the new model (i.e. makes it the one the live agent
       uses) if it is at least as accurate as the currently promoted
       model, OR if there is no promoted model yet. A regression never
       gets shipped automatically.
    5. Every trained model is kept on disk with a timestamp, so you can
       always roll back by editing learning/models/current_model.json.
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # allow `python learning/train_intent_classifier.py`

from learning.dataset import dataset_stats, has_enough_data, load_dataset

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)
POINTER_PATH = MODELS_DIR / "current_model.json"

MIN_TOTAL_EXAMPLES = 40
MIN_PER_CLASS = 3


def _load_pointer() -> Dict[str, Any] | None:
    if not POINTER_PATH.exists():
        return None
    try:
        return json.loads(POINTER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def train() -> Dict[str, Any]:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import train_test_split
        from sklearn.pipeline import Pipeline
        from sklearn.metrics import accuracy_score, classification_report
        import joblib
    except ImportError as exc:
        print(f"[train_intent_classifier] scikit-learn / joblib not installed: {exc}")
        print("Run: pip install scikit-learn joblib")
        return {"status": "skipped", "reason": "missing_dependencies"}

    stats = dataset_stats()
    print(f"[train_intent_classifier] Dataset: {stats['total_examples']} examples "
          f"across {len(stats['label_counts'])} intents -> {stats['label_counts']}")

    if not has_enough_data(MIN_TOTAL_EXAMPLES, MIN_PER_CLASS):
        print(f"[train_intent_classifier] Not enough data yet "
              f"(need >= {MIN_TOTAL_EXAMPLES} total and >= {MIN_PER_CLASS} for at least 2 classes). "
              f"Keep the agent running to collect more real calls, then re-run this script.")
        return {"status": "skipped", "reason": "insufficient_data", "stats": stats}

    rows = load_dataset()
    texts = [r["text"] for r in rows]
    labels = [r["intent"] for r in rows]

    # If a class has too few examples to stratify, fall back to a plain split.
    label_counts = stats["label_counts"]
    can_stratify = all(c >= 2 for c in label_counts.values()) and len(rows) >= 10
    split_kwargs = {"test_size": 0.2, "random_state": 42}
    if can_stratify:
        split_kwargs["stratify"] = labels

    X_train, X_test, y_train, y_test = train_test_split(texts, labels, **split_kwargs)

    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 2),
            min_df=1,
            lowercase=True,
            analyzer="word",
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            class_weight="balanced",
        )),
    ])

    pipeline.fit(X_train, y_train)

    if X_test:
        y_pred = pipeline.predict(X_test)
        new_accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, zero_division=0)
    else:
        # Too little data for a held-out set — fit on everything, report train accuracy.
        new_accuracy = pipeline.score(X_train, y_train)
        report = "(dataset too small for a held-out test split; reporting train accuracy)"

    print(f"[train_intent_classifier] New model accuracy: {new_accuracy:.3f}")
    print(report)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = MODELS_DIR / f"intent_clf_{timestamp}.joblib"
    joblib.dump(pipeline, model_path)

    previous = _load_pointer()
    previous_accuracy = previous.get("accuracy", -1.0) if previous else -1.0

    promoted = False
    if new_accuracy >= previous_accuracy:
        pointer = {
            "model_path": str(model_path),
            "accuracy": round(float(new_accuracy), 4),
            "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "n_examples": len(rows),
            "label_counts": label_counts,
            "previous_accuracy": previous_accuracy if previous else None,
        }
        POINTER_PATH.write_text(json.dumps(pointer, indent=2), encoding="utf-8")
        promoted = True
        print(f"[train_intent_classifier] Promoted new model ({new_accuracy:.3f} >= {previous_accuracy:.3f}).")
    else:
        print(f"[train_intent_classifier] Kept previous model: new accuracy {new_accuracy:.3f} "
              f"is worse than current {previous_accuracy:.3f}. New model saved to disk but NOT promoted.")

    return {
        "status": "trained",
        "promoted": promoted,
        "new_accuracy": new_accuracy,
        "previous_accuracy": previous_accuracy,
        "model_path": str(model_path),
        "n_examples": len(rows),
    }


if __name__ == "__main__":
    result = train()
    print(json.dumps(result, indent=2, default=str))
