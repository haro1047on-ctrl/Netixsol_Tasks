"""Automated Retraining Pipeline, Champion-Challenger Promotion Gate & Rollback Engine.

Week 8 — Day 5 Task 2:
1. Loads new incoming production/drifted batches
2. Retrains Challenger model on refreshed historical + new data pool
3. Evaluates Champion vs Challenger on held-out test set
4. Promotes Challenger only if it passes strict SLA performance gates
5. Creates zero-downtime rollback snapshots
6. Defines production execution schedules (Monthly Cron + Event-Driven on Drift)
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

DAY5_DIR = Path(__file__).resolve().parent.parent
WEEK8_DIR = DAY5_DIR.parent
DAY1_DIR = WEEK8_DIR / "Day1"
DAY2_DIR = WEEK8_DIR / "Day2"
DAY2_SRC = DAY2_DIR / "src"
ARCHIVE_DIR = DAY5_DIR / "models" / "archive"
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

CHAMPION_PATH = DAY2_DIR / "models" / "best_property_valuation_model.joblib"
TEST_DATA_PATH = DAY1_DIR / "data" / "processed" / "properties_test.csv"
TRAIN_DATA_PATH = DAY1_DIR / "data" / "processed" / "properties_train.csv"

# Non-feature columns
LEAKAGE_COLS = [
    "price_pkr", "price_pkr_normalized", "raw_price_str", "price_per_marla",
    "property_id", "listing_date", "plot_size_raw", "covered_area_raw",
    "area_society", "amenities"
]

RETRAINING_SCHEDULES = {
    "scheduled_cron": "0 2 1 * *",  # Monthly on 1st of month at 02:00 AM UTC
    "scheduled_description": "Monthly full-batch retraining on all accumulated listings from the past 30 days.",
    "event_driven_trigger": "MAPE_THRESHOLD_EXCEEDED (MAPE > 15.0%) OR FEATURE_DRIFT_RATIO > 0.30",
    "event_driven_description": "Automated trigger executed by DataDriftMonitor whenever macroeconomic shift violates SLA.",
}


class RetrainingPipeline:
    """Production Retraining Pipeline with Champion vs. Challenger Evaluation & Rollback."""

    def __init__(
        self,
        champion_path: Path = CHAMPION_PATH,
        archive_dir: Path = ARCHIVE_DIR
    ):
        self.champion_path = champion_path
        self.archive_dir = archive_dir
        if not self.champion_path.exists():
            raise FileNotFoundError(f"Champion model not found at {self.champion_path}")

        self.champion_bundle = joblib.load(self.champion_path)
        self.preprocessor = self.champion_bundle["preprocessor"]

    def evaluate_model_on_test(
        self,
        model: Any,
        test_df: pd.DataFrame
    ) -> Dict[str, float]:
        """Calculates standard test performance metrics on held-out dataset."""
        X_test_raw = test_df.drop(columns=LEAKAGE_COLS, errors="ignore")
        y_test = test_df["price_pkr"].values
        y_test_log = np.log1p(y_test)

        X_test_trans = self.preprocessor.transform(X_test_raw)
        preds_log = model.predict(X_test_trans)
        preds_pkr = np.expm1(preds_log)

        mae = float(np.mean(np.abs(y_test - preds_pkr)))
        rmse = float(np.sqrt(np.mean((y_test - preds_pkr) ** 2)))
        ss_res = np.sum((y_test - preds_pkr) ** 2)
        ss_tot = np.sum((y_test - np.mean(y_test)) ** 2)
        r2 = float(1.0 - (ss_res / ss_tot))
        mape = float(np.median(np.abs((y_test - preds_pkr) / y_test)) * 100.0)

        return {
            "r2": round(r2, 4),
            "mae_pkr": round(mae),
            "rmse_pkr": round(rmse),
            "mape_pct": round(mape, 2),
        }

    def train_challenger(
        self,
        training_df: pd.DataFrame,
        iterations: int = 250,
        learning_rate: float = 0.07,
        depth: int = 6
    ) -> CatBoostRegressor:
        """Fits a new Challenger CatBoost regressor on refreshed training pool."""
        X_train_raw = training_df.drop(columns=LEAKAGE_COLS, errors="ignore")
        y_train = training_df["price_pkr"].values
        y_train_log = np.log1p(y_train)

        X_train_trans = self.preprocessor.transform(X_train_raw)

        challenger = CatBoostRegressor(
            iterations=iterations,
            learning_rate=learning_rate,
            depth=depth,
            loss_function="RMSE",
            random_seed=42,
            verbose=0
        )
        challenger.fit(X_train_trans, y_train_log)
        return challenger

    def run_pipeline(
        self,
        new_batch_df: Optional[pd.DataFrame] = None,
        force_promote: bool = False
    ) -> Dict[str, Any]:
        """Executes full retraining, champion-challenger comparison, and promotion gate."""
        t0 = time.perf_counter()
        test_df = pd.read_csv(TEST_DATA_PATH)
        base_train_df = pd.read_csv(TRAIN_DATA_PATH)

        if new_batch_df is not None and not new_batch_df.empty:
            refreshed_train_df = pd.concat([base_train_df, new_batch_df], ignore_index=True)
            print(f"Refreshed training pool: {len(base_train_df)} base + {len(new_batch_df)} new = {len(refreshed_train_df)} rows")
        else:
            refreshed_train_df = base_train_df
            print(f"Retraining on base training pool ({len(base_train_df)} rows)...")

        # 1. Evaluate Current Champion
        champion_model = self.champion_bundle["model"]
        champion_metrics = self.evaluate_model_on_test(champion_model, test_df)

        # 2. Train Challenger
        print("Training Challenger CatBoost model...")
        challenger_model = self.train_challenger(refreshed_train_df)

        # 3. Evaluate Challenger
        challenger_metrics = self.evaluate_model_on_test(challenger_model, test_df)

        # 4. Promotion Gate: Challenger must improve or match MAPE without collapsing R²
        mape_improved = challenger_metrics["mape_pct"] <= champion_metrics["mape_pct"]
        r2_acceptable = challenger_metrics["r2"] >= (champion_metrics["r2"] - 0.005)
        promote = force_promote or (mape_improved and r2_acceptable)

        rollback_snapshot = None
        if promote:
            # Create timestamped rollback snapshot of Champion
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            rollback_snapshot = self.archive_dir / f"champion_backup_{ts}.joblib"
            shutil.copy2(self.champion_path, rollback_snapshot)

            # Update champion with Challenger
            new_bundle = {
                "model": challenger_model,
                "preprocessor": self.preprocessor,
                "metrics": challenger_metrics,
                "promoted_at": datetime.now(timezone.utc).isoformat(),
                "training_rows": len(refreshed_train_df),
                "model_name": "PropertyValuationModel_v1_retrained",
            }
            joblib.dump(new_bundle, self.champion_path)
            self.champion_bundle = new_bundle
            decision_text = "CHALLENGER_PROMOTED"
        else:
            decision_text = "CHAMPION_RETAINED (Challenger did not satisfy promotion criteria)"

        elapsed_sec = round(time.perf_counter() - t0, 2)

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision": decision_text,
            "promoted": promote,
            "duration_seconds": elapsed_sec,
            "champion_metrics": champion_metrics,
            "challenger_metrics": challenger_metrics,
            "rollback_snapshot": str(rollback_snapshot) if rollback_snapshot else None,
            "retraining_schedules": RETRAINING_SCHEDULES,
        }

        # Save record
        history_path = DAY5_DIR / "reports" / "retraining_history.json"
        history = []
        if history_path.exists():
            try:
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
        history.append(result)
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        return result

    def rollback_to_last_backup(self) -> Dict[str, Any]:
        """Restores the most recent archived Champion model."""
        backups = sorted(list(self.archive_dir.glob("champion_backup_*.joblib")))
        if not backups:
            raise FileNotFoundError("No archived model backups found in archive directory.")

        latest_backup = backups[-1]
        shutil.copy2(latest_backup, self.champion_path)
        self.champion_bundle = joblib.load(self.champion_path)

        return {
            "status": "ROLLBACK_SUCCESSFUL",
            "restored_from": str(latest_backup),
            "restored_at": datetime.now(timezone.utc).isoformat(),
        }


if __name__ == "__main__":
    pipeline = RetrainingPipeline()
    print("\n--- Running Automated Retraining Pipeline ---")
    res = pipeline.run_pipeline(force_promote=True)
    print(f"Decision: {res['decision']}")
    print(f"Champion MAPE: {res['champion_metrics']['mape_pct']}% | Challenger MAPE: {res['challenger_metrics']['mape_pct']}%")
    print(f"Rollback Backup Created: {res['rollback_snapshot']}")
    print(f"Retraining Schedule: {res['retraining_schedules']['scheduled_cron']} ({res['retraining_schedules']['scheduled_description']})")
