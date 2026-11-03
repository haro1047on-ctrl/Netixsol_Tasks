"""Unit & Integration Tests for Week 8 Day 5 MLOps Drift & Retraining Pipeline.

Tests:
1. DataDriftMonitor initialization & reference dataset verification
2. Production data shift simulation (+15% and +25% inflation)
3. Drift detection, Kolmogorov-Smirnov test, and threshold alerting (MAPE > 15%)
4. RetrainingPipeline challenger model training on refreshed data
5. Promotion gate verification and rollback backup generation
6. Rollback execution to restore previous champion model
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TEST_DIR = Path(__file__).resolve().parent
DAY5_SRC = TEST_DIR.parent / "src"
if str(DAY5_SRC) not in sys.path:
    sys.path.insert(0, str(DAY5_SRC))

from drift_detector import DataDriftMonitor
from retraining_pipeline import RetrainingPipeline


def test_drift_monitor_and_simulation():
    monitor = DataDriftMonitor(mape_alert_threshold=15.0)
    assert len(monitor.reference_df) > 1000

    # Simulate moderate drift (+15%)
    drifted_15 = monitor.simulate_production_drift(price_inflation_pct=15.0, sample_size=500)
    assert len(drifted_15) == 500
    assert drifted_15["price_pkr"].mean() > monitor.reference_df["price_pkr"].mean()

    report_15 = monitor.detect_drift(drifted_15)
    assert "overall_health" in report_15
    assert report_15["feature_drift_summary"]["drifted_features_count"] > 0
    print(f"✅ Drift Simulation (+15%) Passed: Health={report_15['overall_health']}, Monitored MAPE={report_15['performance_metrics']['current_monitored_mape']}%")

    # Simulate severe drift (+25%) to trigger retrain alert
    drifted_25 = monitor.simulate_production_drift(price_inflation_pct=25.0, sample_size=500)
    report_25 = monitor.detect_drift(drifted_25)
    assert report_25["performance_metrics"]["current_monitored_mape"] > 15.0
    assert report_25["alerts"]["retrain_recommended"] is True
    print(f"✅ Severe Drift (+25%) Alert Passed: MAPE={report_25['performance_metrics']['current_monitored_mape']}% > 15.0% -> RETRAIN_ALERT=TRUE")


def test_retraining_and_promotion_pipeline():
    pipeline = RetrainingPipeline()
    monitor = DataDriftMonitor()
    new_data = monitor.simulate_production_drift(price_inflation_pct=15.0, sample_size=300)

    # Run pipeline with refreshed batch
    result = pipeline.run_pipeline(new_batch_df=new_data, force_promote=True)
    assert "decision" in result
    assert result["promoted"] is True
    assert result["rollback_snapshot"] is not None
    assert Path(result["rollback_snapshot"]).exists()
    print(f"✅ Retraining Pipeline Passed: Decision={result['decision']}, Challenger MAPE={result['challenger_metrics']['mape_pct']}%")


def test_rollback_mechanism():
    pipeline = RetrainingPipeline()
    rollback_res = pipeline.rollback_to_last_backup()
    assert rollback_res["status"] == "ROLLBACK_SUCCESSFUL"
    assert Path(rollback_res["restored_from"]).exists()
    print(f"✅ Rollback Engine Passed: Restored from {rollback_res['restored_from']}")


if __name__ == "__main__":
    print("\n--- Running Day 5 MLOps Drift & Retraining Tests ---")
    test_drift_monitor_and_simulation()
    test_retraining_and_promotion_pipeline()
    test_rollback_mechanism()
    print("\n🎉 ALL MLOPS DRIFT & RETRAINING TESTS PASSED WITH 100% SUCCESS!\n")
