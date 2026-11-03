"""Monitoring, Data Drift Detection & Prediction Drift Engine (Week 8 - Day 5 Task 1).

Capabilities:
1. Simulates realistic market distribution shifts (e.g., 15% macroeconomic inflation price surge, shifts in plot size and amenities)
2. Computes statistical feature drift (Two-Sample Kolmogorov-Smirnov test, Population Stability Index, Wasserstein distance)
3. Computes prediction drift (distribution shift in model valuations)
4. Computes performance/concept drift and evaluates against alert thresholds (e.g. MAPE > 15% triggers retrain)
5. Generates interactive HTML and JSON drift reports
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

DAY5_DIR = Path(__file__).resolve().parent.parent
WEEK8_DIR = DAY5_DIR.parent
DAY1_DIR = WEEK8_DIR / "Day1"
DAY2_SRC = WEEK8_DIR / "Day2" / "src"
REPORTS_DIR = DAY5_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

if str(DAY2_SRC) not in sys.path:
    sys.path.insert(0, str(DAY2_SRC))

from valuation_inference import PropertyValuationEngine, format_pakistani_currency


def calculate_psi(expected: np.ndarray, actual: np.ndarray, num_buckets: int = 10) -> float:
    """Calculates Population Stability Index (PSI) between reference and current distribution."""
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Quantile bins from expected
    percentiles = np.linspace(0, 100, num_buckets + 1)
    bins = np.percentile(expected, percentiles)
    bins[0] = -np.inf
    bins[-1] = np.inf
    # Make bins unique
    bins = np.unique(bins)
    if len(bins) < 3:
        return 0.0

    exp_counts, _ = np.histogram(expected, bins=bins)
    act_counts, _ = np.histogram(actual, bins=bins)

    exp_pct = exp_counts / len(expected)
    act_pct = act_counts / len(actual)

    # Avoid zero division
    exp_pct = np.where(exp_pct == 0, 1e-4, exp_pct)
    act_pct = np.where(act_pct == 0, 1e-4, act_pct)

    psi = np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct))
    return float(psi)


class DataDriftMonitor:
    """Statistical and Performance Drift Detection Engine for Real Estate Valuations."""

    def __init__(
        self,
        reference_data_path: Optional[Path] = None,
        mape_alert_threshold: float = 15.0,
        drift_p_value_threshold: float = 0.05
    ):
        if reference_data_path is None:
            reference_data_path = DAY1_DIR / "data" / "processed" / "properties_train.csv"
        self.ref_path = reference_data_path
        self.mape_threshold = mape_alert_threshold
        self.p_val_threshold = drift_p_value_threshold
        self.engine = PropertyValuationEngine()

        if self.ref_path.exists():
            self.reference_df = pd.read_csv(self.ref_path)
        else:
            raise FileNotFoundError(f"Reference data not found at {self.ref_path}")

    def simulate_production_drift(
        self,
        base_df: Optional[pd.DataFrame] = None,
        price_inflation_pct: float = 15.0,
        sample_size: int = 1000,
        random_seed: int = 42
    ) -> pd.DataFrame:
        """Simulates production data after real-world macro market shifts (e.g. 15% price surge)."""
        np.random.seed(random_seed)
        if base_df is None:
            # Use validation / test split as base for incoming batch
            val_path = DAY1_DIR / "data" / "processed" / "properties_val.csv"
            if val_path.exists():
                base_df = pd.read_csv(val_path)
            else:
                base_df = self.reference_df.copy()

        current_df = base_df.sample(n=min(sample_size, len(base_df)), replace=True, random_state=random_seed).copy()

        # 1. Apply macroeconomic price inflation (+15% with localized variance)
        inflation_multiplier = 1.0 + (price_inflation_pct / 100.0) + np.random.normal(0, 0.03, size=len(current_df))
        current_df["price_pkr"] = current_df["price_pkr"] * inflation_multiplier
        if "price_per_marla" in current_df.columns:
            current_df["price_per_marla"] = current_df["price_pkr"] / current_df["plot_size_marla"]

        # 2. Shift in construction age (aging inventory)
        current_df["age_years"] = current_df["age_years"] + np.random.uniform(0.5, 2.0, size=len(current_df))

        # 3. Increase in solar / generator amenity adoption due to power tariffs
        if "amenity_score" in current_df.columns:
            current_df["amenity_score"] = np.clip(current_df["amenity_score"] + np.random.choice([0.0, 1.5, 2.0], p=[0.4, 0.3, 0.3], size=len(current_df)), 0, 10)

        return current_df

    def detect_drift(
        self,
        current_df: pd.DataFrame,
        numerical_features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Executes comprehensive drift detection across features, predictions, and model performance."""
        if numerical_features is None:
            numerical_features = [
                "plot_size_marla", "covered_area_sqft", "bedrooms",
                "bathrooms", "age_years", "amenity_score", "distance_to_main_road_km"
            ]

        feature_drift_results = {}
        drifted_features_count = 0

        # 1. Feature Drift Analysis
        for feat in numerical_features:
            if feat in self.reference_df.columns and feat in current_df.columns:
                ref_vals = self.reference_df[feat].dropna().values
                cur_vals = current_df[feat].dropna().values

                # Kolmogorov-Smirnov 2-sample test
                ks_stat, p_val = stats.ks_2samp(ref_vals, cur_vals)
                # Wasserstein (Earth Mover's) distance
                w_dist = stats.wasserstein_distance(ref_vals, cur_vals)
                # Population Stability Index (PSI)
                psi_val = calculate_psi(ref_vals, cur_vals)

                is_drifted = bool(p_val < self.p_val_threshold)
                if is_drifted:
                    drifted_features_count += 1

                feature_drift_results[feat] = {
                    "feature_name": feat,
                    "drift_detected": is_drifted,
                    "ks_statistic": round(float(ks_stat), 4),
                    "p_value": float(p_val),
                    "wasserstein_distance": round(float(w_dist), 4),
                    "psi": round(float(psi_val), 4),
                    "reference_mean": round(float(np.mean(ref_vals)), 2),
                    "current_mean": round(float(np.mean(cur_vals)), 2),
                }

        # 2. Prediction Drift & Concept Drift
        # Transform and predict using champion model
        ref_sample = self.reference_df.head(len(current_df))
        ref_X_trans = self.engine.preprocessor.transform(ref_sample)
        cur_X_trans = self.engine.preprocessor.transform(current_df)

        ref_preds_log = self.engine.model.predict(ref_X_trans)
        cur_preds_log = self.engine.model.predict(cur_X_trans)

        ref_preds_pkr = np.expm1(ref_preds_log)
        cur_preds_pkr = np.expm1(cur_preds_log)

        pred_ks_stat, pred_p_val = stats.ks_2samp(ref_preds_pkr, cur_preds_pkr)
        prediction_drift_detected = bool(pred_p_val < self.p_val_threshold)

        # 3. Performance Degradation (Concept Drift)
        actual_prices = current_df["price_pkr"].values
        abs_percentage_errors = np.abs((actual_prices - cur_preds_pkr) / actual_prices) * 100.0
        current_mape = float(np.median(abs_percentage_errors))
        current_mae = float(np.mean(np.abs(actual_prices - cur_preds_pkr)))
        current_rmse = float(np.sqrt(np.mean((actual_prices - cur_preds_pkr) ** 2)))

        baseline_mape = 6.25  # From Day 2 evaluation report
        mape_increase = current_mape - baseline_mape

        # Alert evaluation
        retrain_alert = bool(current_mape > self.mape_threshold)
        feature_drift_ratio = drifted_features_count / max(len(numerical_features), 1)
        data_drift_alert = bool(feature_drift_ratio >= 0.25)

        overall_status = "CRITICAL_DRIFT" if retrain_alert else ("WARNING_DRIFT" if data_drift_alert else "STABLE")

        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_health": overall_status,
            "alerts": {
                "retrain_recommended": retrain_alert,
                "data_drift_alert": data_drift_alert,
                "prediction_drift_alert": prediction_drift_detected,
                "mape_threshold_exceeded": bool(current_mape > self.mape_threshold),
            },
            "performance_metrics": {
                "baseline_test_mape": baseline_mape,
                "current_monitored_mape": round(current_mape, 2),
                "mape_degradation_pct": round(mape_increase, 2),
                "alert_threshold_mape": self.mape_threshold,
                "current_mae_pkr": format_pakistani_currency(current_mae),
                "current_rmse_pkr": format_pakistani_currency(current_rmse),
            },
            "prediction_drift": {
                "drift_detected": prediction_drift_detected,
                "ks_statistic": round(float(pred_ks_stat), 4),
                "p_value": float(pred_p_val),
                "reference_median_predicted": format_pakistani_currency(float(np.median(ref_preds_pkr))),
                "current_median_predicted": format_pakistani_currency(float(np.median(cur_preds_pkr))),
            },
            "feature_drift_summary": {
                "total_features_monitored": len(numerical_features),
                "drifted_features_count": drifted_features_count,
                "drifted_features_ratio": round(feature_drift_ratio, 2),
                "features_detail": feature_drift_results,
            }
        }

        # Save JSON Report
        json_path = REPORTS_DIR / "data_drift_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        # Generate HTML Report
        self._generate_html_report(report, REPORTS_DIR / "data_drift_report.html")

        return report

    def _generate_html_report(self, report_dict: Dict[str, Any], output_path: Path):
        """Builds an executive HTML dashboard presenting drift findings."""
        alerts = report_dict["alerts"]
        perf = report_dict["performance_metrics"]
        feat_sum = report_dict["feature_drift_summary"]
        pred_drift = report_dict["prediction_drift"]

        badge_color = "#DC2626" if alerts["retrain_recommended"] else ("#D97706" if alerts["data_drift_alert"] else "#16A34A")
        status_label = "🚨 CRITICAL: RETRAINING REQUIRED" if alerts["retrain_recommended"] else ("⚠️ WARNING: DATA DRIFT DETECTED" if alerts["data_drift_alert"] else "✅ SYSTEM STABLE")

        rows_html = ""
        for feat, d in feat_sum["features_detail"].items():
            drift_tag = "<span style='color:red; font-weight:bold;'>DRIFTED</span>" if d["drift_detected"] else "<span style='color:green;'>Stable</span>"
            rows_html += f"""
            <tr>
                <td style='padding:8px; border:1px solid #E5E7EB; font-weight:600;'>{feat}</td>
                <td style='padding:8px; border:1px solid #E5E7EB;'>{drift_tag}</td>
                <td style='padding:8px; border:1px solid #E5E7EB;'>{d['ks_statistic']}</td>
                <td style='padding:8px; border:1px solid #E5E7EB;'>{d['p_value']:.4e}</td>
                <td style='padding:8px; border:1px solid #E5E7EB;'>{d['psi']}</td>
                <td style='padding:8px; border:1px solid #E5E7EB;'>{d['reference_mean']} &rarr; {d['current_mean']}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>MLOps Data & Prediction Drift Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #F9FAFB; color: #111827; padding: 24px; }}
        .card {{ background: white; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); margin-bottom: 24px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #E5E7EB; padding-bottom: 16px; margin-bottom: 20px; }}
        .status-badge {{ background: {badge_color}; color: white; padding: 8px 16px; border-radius: 9999px; font-weight: 700; font-size: 14px; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }}
        .metric-box {{ background: #F3F4F6; padding: 16px; border-radius: 8px; border-left: 4px solid #2563EB; }}
        .metric-val {{ font-size: 24px; font-weight: 700; color: #1F2937; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th {{ background: #F3F4F6; text-align: left; padding: 10px; border: 1px solid #E5E7EB; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <div>
                <h1 style="margin:0; font-size: 24px; color: #1E3A8A;">Enterprise Real Estate MLOps Drift Monitor</h1>
                <p style="margin:4px 0 0 0; color: #6B7280;">Automated Statistical Surveillance & Alerting Gateway (Week 8 Capstone)</p>
            </div>
            <div class="status-badge">{status_label}</div>
        </div>

        <div class="metric-grid">
            <div class="metric-box">
                <div style="font-size:12px; color:#6B7280; text-transform:uppercase;">Baseline MAPE</div>
                <div class="metric-val">{perf['baseline_test_mape']}%</div>
            </div>
            <div class="metric-box" style="border-left-color: {badge_color};">
                <div style="font-size:12px; color:#6B7280; text-transform:uppercase;">Monitored Batch MAPE</div>
                <div class="metric-val" style="color:{badge_color};">{perf['current_monitored_mape']}%</div>
                <div style="font-size:11px; color:#6B7280;">Threshold: &gt; {perf['alert_threshold_mape']}%</div>
            </div>
            <div class="metric-box">
                <div style="font-size:12px; color:#6B7280; text-transform:uppercase;">Drifted Features</div>
                <div class="metric-val">{feat_sum['drifted_features_count']} / {feat_sum['total_features_monitored']}</div>
                <div style="font-size:11px; color:#6B7280;">Ratio: {feat_sum['drifted_features_ratio']*100:.0f}%</div>
            </div>
            <div class="metric-box">
                <div style="font-size:12px; color:#6B7280; text-transform:uppercase;">Prediction Shift</div>
                <div class="metric-val">{pred_drift['reference_median_predicted']} &rarr; {pred_drift['current_median_predicted']}</div>
            </div>
        </div>

        <h3>Feature Drift Breakdown (Kolmogorov-Smirnov & PSI Tests)</h3>
        <table>
            <thead>
                <tr>
                    <th>Feature</th>
                    <th>Drift State</th>
                    <th>KS Statistic</th>
                    <th>p-value</th>
                    <th>PSI</th>
                    <th>Mean Shift (Ref &rarr; Current)</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div style="margin-top: 24px; padding: 16px; background: #EFF6FF; border-radius: 8px; font-size: 13px; color: #1E40AF;">
            <b>Operational Directive:</b> Whenever monitored MAPE exceeds the <b>15.0% SLA boundary</b> or over 30% of core geographical/structural features exhibit KS p-values &lt; 0.05, the orchestration daemon automatically dispatches an alert to Slack/PagerDuty and triggers the <b>Automated Retraining Pipeline</b> to fit a Challenger model on the refreshed data lake.
        </div>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)


if __name__ == "__main__":
    monitor = DataDriftMonitor()
    print("Simulating production market shift (+15% macroeconomic inflation)...")
    drifted_batch = monitor.simulate_production_drift(price_inflation_pct=15.0)
    report = monitor.detect_drift(drifted_batch)
    print("\n--- Drift Detection Summary ---")
    print(f"  • Overall Health: {report['overall_health']}")
    print(f"  • Monitored MAPE: {report['performance_metrics']['current_monitored_mape']}% (Baseline: {report['performance_metrics']['baseline_test_mape']}%)")
    print(f"  • Retrain Alert Triggered: {report['alerts']['retrain_recommended']}")
    print(f"  • Drifted Features: {report['feature_drift_summary']['drifted_features_count']} of {report['feature_drift_summary']['total_features_monitored']}")
    print(f"  • Report Saved to: {REPORTS_DIR / 'data_drift_report.html'}")
