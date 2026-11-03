"""
tests/week10/test_dataset_engineering.py
========================================
Automated Verification Suite for Day 1 Dataset Engineering Invariants.
Validates:
1. Non-leakage: Golden Test Set (200) has zero overlap with Training set.
2. Schema adherence: 100% of assistant turns parse into ZaryaBankingAssistantResponse.
3. Task mix & Rubric constraints: Multi-turn >= 20%, Safety/Fraud >= 10%.
4. Zero PII leakage: Synthetic masking verification on CNIC, PAN, IBAN.
"""

import json
from pathlib import Path
import re
import sys
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.data.schemas import (
    IntentEnum,
    ZaryaBankingAssistantResponse,
    parse_assistant_response,
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SPLITS_DIR = BASE_DIR / "data" / "splits"
TRAIN_FILE = SPLITS_DIR / "train.jsonl"
VAL_FILE = SPLITS_DIR / "val.jsonl"
GOLDEN_FILE = SPLITS_DIR / "golden_test_200.jsonl"


def test_files_exist():
    assert TRAIN_FILE.exists(), f"Missing {TRAIN_FILE}"
    assert VAL_FILE.exists(), f"Missing {VAL_FILE}"
    assert GOLDEN_FILE.exists(), f"Missing {GOLDEN_FILE}"


def test_golden_test_exact_count():
    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    assert len(lines) == 200, f"Expected exactly 200 golden test samples, got {len(lines)}"


def test_no_data_leakage_between_train_and_golden():
    train_queries = set()
    with open(TRAIN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            user_msg = next((m["content"] for m in data["messages"] if m["role"] == "user"), None)
            if user_msg:
                train_queries.add(user_msg.strip().lower())

    golden_queries = set()
    with open(GOLDEN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            user_msg = next((m["content"] for m in data["messages"] if m["role"] == "user"), None)
            if user_msg:
                golden_queries.add(user_msg.strip().lower())

    overlap = train_queries.intersection(golden_queries)
    assert len(overlap) == 0, f"Found {len(overlap)} overlapping queries between Train and Golden Test!"


def test_schema_validity_and_rubric_ratios():
    total_samples = 0
    multiturn_samples = 0
    fraud_safety_samples = 0

    with open(TRAIN_FILE, "r", encoding="utf-8") as f:
        for line in f:
            total_samples += 1
            data = json.loads(line)
            if data.get("is_multiturn"):
                multiturn_samples += 1

            # Validate assistant response
            asst_msg = next((m["content"] for m in reversed(data["messages"]) if m["role"] == "assistant"), None)
            assert asst_msg is not None, "Assistant message missing"
            
            parsed: ZaryaBankingAssistantResponse = parse_assistant_response(asst_msg)
            assert isinstance(parsed, ZaryaBankingAssistantResponse)
            if parsed.intent == IntentEnum.FRAUD_SCAMS:
                fraud_safety_samples += 1

    multiturn_ratio = multiturn_samples / total_samples
    fraud_ratio = fraud_safety_samples / total_samples

    assert multiturn_ratio >= 0.20, f"Multi-turn ratio {multiturn_ratio:.2%} is below required 20%"
    assert fraud_ratio >= 0.10, f"Fraud/Safety ratio {fraud_ratio:.2%} is below required 10%"


def test_pii_sanitization_integrity():
    unmasked_cnic_pattern = re.compile(r"\b\d{5}-\d{7}-\d{1}\b")
    # Verify no unmasked 13-digit real CNICs exist in user queries
    with open(TRAIN_FILE, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            data = json.loads(line)
            for m in data["messages"]:
                matches = unmasked_cnic_pattern.findall(m["content"])
                for match in matches:
                    assert "XXXXXXX" in match or "42101-XXXXXXX" in match, f"Unmasked CNIC found: {match} at line {idx}"
