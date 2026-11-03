"""Property Valuation Inference Engine with Prediction Intervals and Market Verdict (Week 8 - Day 2).

Implements Task 5:
- Point prediction (Fair Market Value)
- Quantile Prediction Intervals (10th and 90th percentiles)
- Market Verdict: Underpriced (Hot Deal) / Fair Market Price / Overpriced
- Formatted English and UrduLish consultation outputs for sales agents
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor

BASE_DIR = Path(__file__).resolve().parent.parent
DAY1_DIR = BASE_DIR.parent / "Day1"
PROC_DIR = DAY1_DIR / "data" / "processed"
MODEL_DIR = BASE_DIR / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

CHAMPION_PATH = MODEL_DIR / "best_property_valuation_model.joblib"
QUANTILE_PATH = MODEL_DIR / "quantile_models.joblib"

# Non-feature columns
LEAKAGE_COLS = [
    "price_pkr", "price_pkr_normalized", "raw_price_str", "price_per_marla",
    "property_id", "listing_date", "plot_size_raw", "covered_area_raw",
    "area_society", "amenities"
]


def format_pakistani_currency(price_pkr: float) -> str:
    """Formats numeric PKR into Pakistani financial units (crore, lac, thousand)."""
    if price_pkr >= 10000000.0:
        crores = price_pkr / 10000000.0
        return f"{crores:.2f} crore"
    elif price_pkr >= 100000.0:
        lacs = price_pkr / 100000.0
        return f"{lacs:.1f} lac"
    elif price_pkr >= 1000.0:
        k = price_pkr / 1000.0
        return f"{k:.0f} thousand"
    return f"{int(price_pkr)} PKR"


def train_quantile_models():
    """Trains 10th and 90th percentile Quantile Regressors for prediction intervals."""
    print("Training Quantile Regressors (alpha=0.10 and alpha=0.90) for prediction intervals...")
    train_df = pd.read_csv(PROC_DIR / "properties_train.csv")
    val_df = pd.read_csv(PROC_DIR / "properties_val.csv")
    preprocessor = joblib.load(DAY1_DIR / "models" / "property_preprocessor.joblib")

    X_train_raw = train_df.drop(columns=LEAKAGE_COLS, errors="ignore")
    y_train = train_df["price_pkr"]
    y_train_log = np.log1p(y_train)

    X_train = preprocessor.transform(X_train_raw)

    # 1. Lower Bound (10th percentile)
    q_low = CatBoostRegressor(
        loss_function="Quantile:alpha=0.10",
        iterations=220,
        learning_rate=0.08,
        depth=6,
        random_seed=42,
        verbose=0
    )
    q_low.fit(X_train, y_train_log)

    # 2. Upper Bound (90th percentile)
    q_high = CatBoostRegressor(
        loss_function="Quantile:alpha=0.90",
        iterations=220,
        learning_rate=0.08,
        depth=6,
        random_seed=42,
        verbose=0
    )
    q_high.fit(X_train, y_train_log)

    quantile_payload = {
        "q_low": q_low,
        "q_high": q_high,
    }
    joblib.dump(quantile_payload, QUANTILE_PATH)
    print(f"Quantile models saved to: {QUANTILE_PATH}")
    return quantile_payload


class PropertyValuationEngine:
    """Production Inference Engine for Fair Price Estimation, Uncertainty Bands & Verdicts."""

    def __init__(self):
        if not CHAMPION_PATH.exists():
            raise FileNotFoundError(f"Champion model not found at: {CHAMPION_PATH}")
        self.bundle = joblib.load(CHAMPION_PATH)
        self.model = self.bundle["model"]
        self.preprocessor = self.bundle["preprocessor"]

        if not QUANTILE_PATH.exists():
            train_quantile_models()
        self.quantile_bundle = joblib.load(QUANTILE_PATH)
        self.q_low = self.quantile_bundle["q_low"]
        self.q_high = self.quantile_bundle["q_high"]

    def _prepare_feature_row(self, input_data: Dict[str, Any]) -> pd.DataFrame:
        """Converts user input dictionary into preprocessor-compatible DataFrame."""
        row = {k: v for k, v in input_data.items() if v is not None}

        # Standard defaults for omitted architectural features
        city = row.get("city", "Lahore")
        society = row.get("area_society", "DHA Phase 5")
        ptype = row.get("property_type", "House")
        plot_marla = float(row.get("plot_size_marla", 10.0))
        bedrooms = int(row.get("bedrooms", 4))
        bathrooms = int(row.get("bathrooms", bedrooms))
        age_years = float(row.get("age_years", 2.0))
        floors = float(row.get("floors", 2.0 if ptype == "House" else 1.0))
        is_corner = row.get("is_corner", "No")
        is_park_facing = row.get("is_park_facing", "No")

        # Computed features
        cov_area = float(row.get("covered_area_sqft", plot_marla * 225.0 * 1.65))
        plot_sqft = plot_marla * 225.0
        cov_ratio = round(cov_area / plot_sqft, 2)
        bed_bath_ratio = round(bedrooms / (bathrooms + 0.001), 2)

        # Distances
        dist_road = float(row.get("distance_to_main_road_km", 0.8))
        dist_school = float(row.get("distance_to_school_km", 1.2))
        dist_hosp = float(row.get("distance_to_hospital_km", 2.0))
        dist_composite = round(0.4 * dist_road + 0.3 * dist_hosp + 0.3 * dist_school, 2)

        amenities_str = row.get("amenities", "Gated Security, Dedicated Parking")
        amenity_score = 0.0
        for item, w in [("generator", 2.0), ("solar", 2.0), ("security", 1.5), ("servant", 1.5), ("lawn", 1.0), ("parking", 1.0)]:
            if item in amenities_str.lower():
                amenity_score += w

        def age_bucket(a: float) -> str:
            if a <= 1.0:
                return "Brand New (0-1 yr)"
            elif a <= 5.0:
                return "Modern (2-5 yrs)"
            elif a <= 15.0:
                return "Established (6-15 yrs)"
            return "Vintage (16+ yrs)"

        # Society tier
        tier = "Tier 1 - Elite" if any(k in society.lower() for k in ["dha", "gulberg", "f-7", "f-10", "clifton", "model"]) else "Tier 2 - Prime"

        df_row = pd.DataFrame([{
            "city": city,
            "property_type": ptype,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "age_years": age_years,
            "floors": floors,
            "is_corner": is_corner,
            "is_park_facing": is_park_facing,
            "distance_to_main_road_km": dist_road,
            "distance_to_school_km": dist_school,
            "distance_to_hospital_km": dist_hosp,
            "area_society_clean": society,
            "plot_size_marla": plot_marla,
            "covered_area_sqft": cov_area,
            "plot_area_sqft": plot_sqft,
            "property_age_bucket": age_bucket(age_years),
            "society_tier": tier,
            "amenity_score": amenity_score,
            "distance_composite_index": dist_composite,
            "covered_to_plot_ratio": cov_ratio,
            "bed_to_bath_ratio": bed_bath_ratio,
            "is_luxury_plot": 1 if is_corner == "Yes" or is_park_facing == "Yes" else 0,
        }])
        return df_row

    def evaluate_property(
        self,
        property_details: Dict[str, Any],
        listed_price_pkr: Optional[float] = None
    ) -> Dict[str, Any]:
        """Performs property valuation, computes prediction interval, and generates market verdict."""
        df_row = self._prepare_feature_row(property_details)
        X_trans = self.preprocessor.transform(df_row)

        # Point prediction
        pred_log = self.model.predict(X_trans)[0]
        pred_pkr = float(np.expm1(pred_log))

        # Quantile interval (10th and 90th percentile)
        q_low_log = self.q_low.predict(X_trans)[0]
        q_high_log = self.q_high.predict(X_trans)[0]
        lower_range_pkr = float(np.expm1(q_low_log))
        upper_range_pkr = float(np.expm1(q_high_log))

        # Ensure logical bounds
        lower_range_pkr = min(lower_range_pkr, pred_pkr * 0.95)
        upper_range_pkr = max(upper_range_pkr, pred_pkr * 1.05)

        pred_fmt = format_pakistani_currency(pred_pkr)
        lower_fmt = format_pakistani_currency(lower_range_pkr)
        upper_fmt = format_pakistani_currency(upper_range_pkr)

        # Verdict logic
        verdict = "Fair Market Price"
        variance_pct = 0.0
        listed_fmt = None

        if listed_price_pkr is not None and listed_price_pkr > 0:
            listed_fmt = format_pakistani_currency(listed_price_pkr)
            variance_pct = ((listed_price_pkr - pred_pkr) / pred_pkr) * 100.0

            if listed_price_pkr < lower_range_pkr:
                verdict = "Underpriced (Hot Deal!)"
            elif listed_price_pkr > upper_range_pkr:
                verdict = "Overpriced"
            else:
                verdict = "Fair Market Price"

        # Construct English text
        if listed_fmt:
            if verdict == "Overpriced":
                en_summary = f"Predicted: {pred_fmt} (range {lower_fmt} to {upper_fmt}). Listed at {listed_fmt} -> Overpriced by ~{abs(variance_pct):.1f}%."
                ur_summary = f"Sahi market qeemat: {pred_fmt} (range {lower_fmt} se {upper_fmt} tak). Demand {listed_fmt} hai jo ke market se ~{abs(variance_pct):.1f}% mehngi (overpriced) hai."
            elif verdict == "Underpriced (Hot Deal!)":
                en_summary = f"Predicted: {pred_fmt} (range {lower_fmt} to {upper_fmt}). Listed at {listed_fmt} -> Underpriced by ~{abs(variance_pct):.1f}% (Hot Investment Deal!)."
                ur_summary = f"Sahi market qeemat: {pred_fmt} (range {lower_fmt} se {upper_fmt} tak). Demand {listed_fmt} hai jo ke market se ~{abs(variance_pct):.1f}% sasti (zabardast deal) hai!"
            else:
                en_summary = f"Predicted: {pred_fmt} (range {lower_fmt} to {upper_fmt}). Listed at {listed_fmt} -> Fair Market Price (within standard range)."
                ur_summary = f"Sahi market qeemat: {pred_fmt} (range {lower_fmt} se {upper_fmt} tak). Demand {listed_fmt} bilkul munasib aur market ke mutabiq hai."
        else:
            en_summary = f"Fair Market Valuation: {pred_fmt} (expected range: {lower_fmt} to {upper_fmt})."
            ur_summary = f"Is property ki sahi market qeemat: {pred_fmt} hai (expected range: {lower_fmt} se {upper_fmt} tak)."

        return {
            "predicted_price_pkr": round(pred_pkr),
            "predicted_price_formatted": pred_fmt,
            "lower_range_pkr": round(lower_range_pkr),
            "lower_range_formatted": lower_fmt,
            "upper_range_pkr": round(upper_range_pkr),
            "upper_range_formatted": upper_fmt,
            "listed_price_pkr": listed_price_pkr,
            "listed_price_formatted": listed_fmt,
            "verdict": verdict,
            "variance_pct": round(variance_pct, 1),
            "english_summary": en_summary,
            "urdulish_summary": ur_summary,
        }


if __name__ == "__main__":
    train_quantile_models()
    engine = PropertyValuationEngine()

    # Test Sample Case 1: Overpriced Listing
    test_prop_1 = {
        "city": "Lahore",
        "area_society": "DHA Phase 5",
        "property_type": "House",
        "plot_size_marla": 10.0,
        "bedrooms": 4,
        "bathrooms": 4,
        "age_years": 2.0,
        "is_corner": "Yes",
    }
    result_1 = engine.evaluate_property(test_prop_1, listed_price_pkr=49000000.0)
    print("\nTest Case 1 (Listed 4.9 Crore):")
    print(f"  English:  {result_1['english_summary']}")
    print(f"  UrduLish: {result_1['urdulish_summary']}")

    # Test Sample Case 2: Direct prompt question: "Is plot ki sahi qeemat kya honi chahiye?"
    test_prop_2 = {
        "city": "Islamabad",
        "area_society": "Sector F-7",
        "property_type": "House",
        "plot_size_marla": 20.0,  # 1 Kanal
        "bedrooms": 5,
        "bathrooms": 6,
        "age_years": 1.0,
    }
    result_2 = engine.evaluate_property(test_prop_2)
    print("\nTest Case 2 ('Is plot ki sahi qeemat kya honi chahiye?'):")
    print(f"  English:  {result_2['english_summary']}")
    print(f"  UrduLish: {result_2['urdulish_summary']}")
