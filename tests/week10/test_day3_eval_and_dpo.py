"""
tests/week10/test_day3_eval_and_dpo.py
======================================
Automated test suite for Week 10 Day 3:
- Task 1: Evaluation Harness & LLM Judge Calibration
- Task 2: Blind Human Evaluation Analysis
- Task 3: DPO Preference Dataset (500+ pairs)
- Task 4: DPO Alignment Artifacts & Notebook
- Task 5: Catastrophic Forgetting & Regression Suite
"""

import json
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

from src.data.schemas import ZaryaBankingAssistantResponse
from src.eval.evaluation_harness import (
    EvaluationHarness,
    LLMJudgeEngine,
    PolicyFaithfulnessDetector,
)
from src.eval.validate_llm_judge import (
    generate_calibration_dataset,
    calibrate_llm_judge,
)
from src.eval.human_eval_app import (
    generate_blind_samples,
    analyze_human_evaluation,
)
from src.data.generate_dpo_dataset import generate_dpo_dataset
from src.eval.regression_forgetting_check import (
    load_mmlu_hellaswag_subset,
    load_general_english_suite,
    load_out_of_domain_suite,
    run_regression_and_forgetting_suite,
)


class TestDay3EvaluationHarness:
    """Validates Task 1: Evaluation Harness & Calibration."""

    def test_evaluation_harness_summary_exists(self):
        summary_path = REPO_ROOT / "results" / "evaluation" / "evaluation_harness_summary.json"
        assert summary_path.exists(), f"Summary file missing at {summary_path}"
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "task_accuracy" in data
        assert "structured_output" in data
        assert "safety_and_refusal" in data
        assert "policy_faithfulness" in data
        assert "llm_judge_quality" in data
        assert data["structured_output"]["json_validity_rate_pct"] >= 95.0
        assert data["task_accuracy"]["intent_accuracy_pct"] >= 75.0

    def test_policy_faithfulness_detector(self):
        detector = PolicyFaithfulnessDetector()
        
        # Test clean compliant response
        good_resp = "Ji, ATM dispense failure ka masla 48 business hours ke andar SBP circular ke mutabiq hal hoga."
        faithful, violations = detector.audit_response(good_resp, "Complaints")
        assert faithful is True
        assert len(violations) == 0

        # Test hallucinated timeline (60 days)
        bad_resp = "Ji, ATM dispute mein 60 din lagtay hain."
        faithful, violations = detector.audit_response(bad_resp, "Complaints")
        assert faithful is False
        assert len(violations) > 0

    def test_llm_judge_engine(self):
        judge = LLMJudgeEngine()
        scores = judge.evaluate_sample(
            user_query="Mera Raast transfer phans gaya hai",
            response_text="Ji Janab, humein afsos hai. Aapka Raast transfer verify kar rahay hain.",
            intent="Transfers_Payments",
            is_security_query=False
        )
        assert "correctness" in scores
        assert "zarya_tone" in scores
        assert "urdulish_fluency" in scores
        assert 1.0 <= scores["overall_quality"] <= 5.0

    def test_judge_calibration_execution(self):
        samples = generate_calibration_dataset(num_samples=10)
        assert len(samples) == 10
        report = calibrate_llm_judge(samples)
        assert "correlation_metrics" in report
        assert "agreement_metrics" in report
        assert "error_metrics" in report

    def test_judge_calibration_report_file(self):
        report_path = REPO_ROOT / "results" / "evaluation" / "judge_calibration_report.json"
        assert report_path.exists()
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "correlation_metrics" in data
        assert "agreement_metrics" in data
        assert data["correlation_metrics"]["spearman_rho"] >= 0.70
        assert data["agreement_metrics"]["cohen_kappa_quadratic_weighted"] >= 0.50


class TestDay3HumanEvaluation:
    """Validates Task 2: Blind Human Evaluation App & Pairwise Win-Rates."""

    def test_human_eval_summary_exists(self):
        summary_path = REPO_ROOT / "results" / "human_eval" / "human_eval_summary.json"
        assert summary_path.exists()
        with open(summary_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "pairwise_head_to_head" in data
        # Target: >= 70% win rate vs base
        win_rate_vs_base = data["pairwise_head_to_head"]["sft_vs_base_win_rate_pct"]
        assert win_rate_vs_base >= 70.0, f"Expected >= 70% win rate vs base, got {win_rate_vs_base}%"

    def test_blind_eval_samples_structure(self):
        samples_path = REPO_ROOT / "results" / "human_eval" / "blind_eval_50_samples.json"
        assert samples_path.exists()
        with open(samples_path, "r", encoding="utf-8") as f:
            samples = json.load(f)
        assert len(samples) == 50
        sample = samples[0]
        assert "sample_id" in sample
        assert "customer_query" in sample
        assert "options" in sample
        assert "Model_A" in sample["options"]
        assert "Model_B" in sample["options"]
        assert "Model_C" in sample["options"]


class TestDay3DPODataset:
    """Validates Task 3: DPO Preference Dataset."""

    def test_dpo_file_exists_and_count(self):
        dpo_path = REPO_ROOT / "data" / "dpo" / "preference_pairs_500.jsonl"
        assert dpo_path.exists(), f"DPO dataset missing at {dpo_path}"
        
        records = []
        with open(dpo_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        
        assert len(records) >= 500, f"Expected >= 500 DPO pairs, found {len(records)}"

    def test_dpo_records_schema_and_contrast(self):
        dpo_path = REPO_ROOT / "data" / "dpo" / "preference_pairs_500.jsonl"
        with open(dpo_path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if idx >= 50:  # Check first 50
                    break
                record = json.loads(line)
                assert "prompt" in record
                assert "chosen" in record
                assert "rejected" in record
                assert "domain_category" in record

                # Verify chosen response strictly parses against ZaryaBankingAssistantResponse
                chosen_content = record["chosen"][0]["content"]
                parsed = ZaryaBankingAssistantResponse.model_validate_json(chosen_content)
                assert parsed.response_urdu_lish is not None
                
                # Check for polite honorifics in chosen response
                urdu_text = parsed.response_urdu_lish
                assert any(h in urdu_text for h in ["Ji", "Aap", "Mohtaram", "Janab", "Shukriya"])

                # Check that rejected is non-empty and different
                rejected_content = record["rejected"][0]["content"]
                assert chosen_content != rejected_content


class TestDay3DPOArtifactsAndNotebook:
    """Validates Task 4: DPO Alignment Notebook & Theory Doc."""

    def test_notebook_exists_and_valid_json(self):
        nb_path = REPO_ROOT / "notebooks" / "02_Day3_DPO_Alignment_Unsloth.ipynb"
        assert nb_path.exists(), f"DPO notebook missing at {nb_path}"
        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        assert "cells" in nb
        assert len(nb["cells"]) >= 10
        # Check for key DPO components in notebook
        text_content = json.dumps(nb)
        assert "PatchDPOTrainer" in text_content
        assert "DPOTrainer" in text_content
        assert "beta" in text_content
        assert "FastLanguageModel" in text_content

    def test_theory_doc_exists_and_content(self):
        theory_path = REPO_ROOT / "docs" / "day3_dpo_theory_and_results.md"
        assert theory_path.exists()
        with open(theory_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Bradley-Terry" in content
        assert "Rafailov" in content
        assert "beta" in content or "\\beta" in content
        assert "PPO" in content


class TestDay3CatastrophicForgetting:
    """Validates Task 5: Catastrophic Forgetting & Regression Suite."""

    def test_benchmark_suites_loading(self):
        reasoning = load_mmlu_hellaswag_subset()
        english = load_general_english_suite()
        ood = load_out_of_domain_suite()

        assert len(reasoning) == 50
        assert len(english) == 25
        assert len(ood) == 25

    def test_regression_report_generated(self):
        report_path = REPO_ROOT / "results" / "evaluation" / "regression_forgetting_report.json"
        assert report_path.exists()
        with open(report_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "reasoning_benchmarks" in data
        assert data["reasoning_benchmarks"]["passed_forgetting_threshold"] is True
        assert data["reasoning_benchmarks"]["degradation_pct_points"] < 2.5

    def test_lm_eval_config_exists(self):
        config_path = REPO_ROOT / "configs" / "lm_eval_zarya_config.yaml"
        assert config_path.exists()
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "mmlu" in content
        assert "hellaswag" in content
        assert "gsm8k" in content
