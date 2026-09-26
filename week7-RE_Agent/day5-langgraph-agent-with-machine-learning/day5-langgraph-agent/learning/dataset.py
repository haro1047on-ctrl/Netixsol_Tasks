"""Append-only training log: every real call turn becomes a future training example.

This is intentionally decoupled from `logger.py`'s execution traces (those are
for debugging a single session). This file is the durable, ever-growing
dataset the intent classifier is retrained on.
"""
from __future__ import annotations

import datetime
import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger("LangGraphAgent")

_LEARNING_DIR = Path(__file__).resolve().parent
DATA_DIR = _LEARNING_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

TRAINING_LOG_PATH = DATA_DIR / "intent_training_log.jsonl"

# A turn is only worth training on if the classification was reasonably
# confident/unambiguous. We still log everything (for audit), but tag rows
# so the trainer can filter noisy examples.
_WRITE_LOCK = threading.Lock()

# Keep this list in sync with the intents `_classify_intent` can return.
VALID_INTENTS = {
    "greeting", "recommendation", "rag", "booking", "rescheduling",
    "cancellation", "email", "goodbye", "off_topic", "clarification",
}


def log_training_example(
    text: str,
    intent: str,
    *,
    session_id: str = "default_session",
    clarification_needed: bool = False,
    source: str = "rule_engine",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Append one labeled (utterance -> intent) example to the training log.

    Never raises: a logging failure must never break a live call.
    """
    try:
        text = (text or "").strip()
        if not text or intent not in VALID_INTENTS:
            return

        row = {
            "text": text,
            "intent": intent,
            "session_id": session_id,
            "clarification_needed": bool(clarification_needed),
            "source": source,  # who produced this label: rule_engine | human_correction | ml_model
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        if extra:
            row["extra"] = extra

        with _WRITE_LOCK:
            with TRAINING_LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as exc:  # pragma: no cover - defensive, must never break the agent
        logger.warning(f"[learning.dataset] failed to log training example: {exc}")


def load_dataset(min_len: int = 2) -> List[Dict[str, Any]]:
    """Load every logged row. Drops empty/too-short/malformed rows."""
    if not TRAINING_LOG_PATH.exists():
        return []

    rows: List[Dict[str, Any]] = []
    with TRAINING_LOG_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            text = row.get("text", "")
            intent = row.get("intent")
            if len(text) >= min_len and intent in VALID_INTENTS:
                rows.append(row)
    return rows


def dataset_stats() -> Dict[str, Any]:
    """Quick summary used by the training script and can be surfaced in a dashboard."""
    rows = load_dataset()
    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["intent"]] = counts.get(r["intent"], 0) + 1
    return {
        "total_examples": len(rows),
        "label_counts": counts,
        "log_path": str(TRAINING_LOG_PATH),
    }


def has_enough_data(min_total: int = 40, min_per_class: int = 3) -> bool:
    """Cheap gate the training script (and a status endpoint) can use."""
    stats = dataset_stats()
    if stats["total_examples"] < min_total:
        return False
    return sum(1 for c in stats["label_counts"].values() if c >= min_per_class) >= 2
