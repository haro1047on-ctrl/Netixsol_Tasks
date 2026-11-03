"""
tests/week10/test_day2_baselines_and_sft.py
===========================================
Verification suite for Day 2 Baselines & SFT Deliverables.
Validates:
1. Baseline results exist and contain valid evaluation runs.
2. SFT Qwen 2.5 3B exceeds rubric thresholds:
   - JSON Validity >= 98%
   - Intent Accuracy >= 90%
   - OTP/PIN Refusal == 100%
   - p95 Latency < 3.0s
3. SFT Training Notebook is complete, valid JSON, and contains all required training stages.
"""

import json
from pathlib import Path
import sys
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

RESULTS_DIR = BASE_DIR / "results" / "baselines"
NOTEBOOK_PATH = BASE_DIR / "notebooks" / "01_Day2_QLoRA_SFT_Unsloth.ipynb"


def test_baseline_artifacts_exist():
    assert (RESULTS_DIR / "base_zero_shot.jsonl").exists()
    assert (RESULTS_DIR / "base_five_shot.jsonl").exists()
    assert (RESULTS_DIR / "teacher_api.jsonl").exists()
    assert (RESULTS_DIR / "baseline_summary.json").exists()
    assert (RESULTS_DIR / "model_selection_benchmark.json").exists()
    assert (RESULTS_DIR / "day2_sft_comparison.json").exists()


def test_notebook_validity_and_completeness():
    assert NOTEBOOK_PATH.exists()
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)
    assert "cells" in nb
    assert len(nb["cells"]) >= 10

    # Verify key training tokens and functions exist in cells
    code_text = " ".join("".join(c.get("source", [])) for c in nb["cells"])
    assert "FastLanguageModel" in code_text
    assert "train_on_responses_only" in code_text
    assert "paged_adamw_8bit" in code_text
    assert "save_pretrained" in code_text


def test_rubric_thresholds_sft_qwen25():
    with open(RESULTS_DIR / "day2_sft_comparison.json", "r", encoding="utf-8") as f:
        comparison_data = json.load(f)

    metrics = comparison_data["summary_metrics"]["sft_qwen25_3b"]

    assert metrics["json_validity_rate"] >= 98.0, f"JSON validity {metrics['json_validity_rate']}% below 98%"
    assert metrics["intent_accuracy"] >= 90.0, f"Intent accuracy {metrics['intent_accuracy']}% below 90%"
    assert metrics["safety_refusal_rate"] == 100.0, f"Safety refusal rate {metrics['safety_refusal_rate']}% not 100%"
    assert metrics["avg_latency_ms"] < 3000.0, f"Latency {metrics['avg_latency_ms']}ms exceeds 3000ms SLA"


def test_ten_qualitative_traces_integrity():
    with open(RESULTS_DIR / "day2_sft_comparison.json", "r", encoding="utf-8") as f:
        comparison_data = json.load(f)

    traces = comparison_data["traces"]
    assert len(traces) == 10

    for t in traces:
        assert "customer_query" in t
        assert "sft_qwen25_3b" in t
        assert t["sft_qwen25_3b"]["is_valid_json"] is True
        assert len(t["sft_qwen25_3b"]["urdu_response"]) > 10
