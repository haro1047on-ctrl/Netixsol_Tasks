"""Week 8 Day 3: Explainability with SHAP for Both Models.

Implements:
1. Lead Scoring Model SHAP Explainability:
   - Global Beeswarm / Bar Summary Plot (05_lead_shap_global_summary.png)
   - Local Waterfall / Force Plot (06_lead_shap_local_waterfall.png)
   - English & UrduLish plain-language explanation generator
2. Property Valuation Model SHAP Explainability:
   - Global Beeswarm / Bar Summary Plot (07_property_shap_global_summary.png)
   - Local Waterfall / Force Plot (08_property_shap_local_waterfall.png)
   - English & UrduLish plain-language explanation generator
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

DAY3_DIR = Path(__file__).resolve().parent.parent
WEEK8_DIR = DAY3_DIR.parent
DAY2_DIR = WEEK8_DIR / "Day2"
FIGURES_DIR = DAY3_DIR / "reports" / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Friendly feature name dictionaries for UrduLish & English translation
LEAD_FEATURE_FRIENDLY_NAMES = {
    "num__budget_pkr": ("Client Budget", "Client ka budget"),
    "num__number_of_calls": ("Number of Phone Calls", "Total phone calls"),
    "num__avg_call_duration_mins": ("Avg Call Duration", "Call ki ost muddat"),
    "num__response_time_hours": ("Response Time", "Jawab dene ka waqt"),
    "num__days_since_first_contact": ("Days in Pipeline", "Pipeline mein din"),
    "num__lead_engagement_score": ("Engagement Intensity", "Rabtay ki shiddat"),
    "num__interaction_intensity": ("Daily Interaction Rate", "Rozana baat cheet ki sharah"),
    "num__objection_severity_score": ("Objection Severity", "Aitraz ki shiddat"),
    "num__budget_to_market_ratio": ("Budget-to-Market Ratio", "Market rate se budget ka mawazna"),
    "visit_bin__visit_booked_Yes": ("On-site Visit Booked", "Site visit ka confirm hona"),
    "passthrough__is_high_intent": ("High Intent Flag", "Kharidne ka pukhta irada"),
    "cat__lead_source_WhatsApp": ("Source: WhatsApp", "WhatsApp se rabta"),
    "cat__lead_source_Call": ("Source: Direct Call", "Direct Call se rabta"),
    "cat__lead_source_Website": ("Source: Web Portal", "Website se inquiry"),
    "cat__lead_source_Facebook": ("Source: Facebook Ad", "Facebook ad inquiry"),
    "cat__purpose_Buy": ("Purpose: Purchase", "Property khareednay ka maqsad"),
    "cat__purpose_Rent": ("Purpose: Rental", "Kiraye par lenay ka maqsad"),
}

PROPERTY_FEATURE_FRIENDLY_NAMES = {
    "num__plot_size_marla": ("Plot Size (Marla)", "Plot ka size (Marla)"),
    "num__covered_area_sqft": ("Covered Area (Sqft)", "Tameer shuda raqba"),
    "num__bedrooms": ("Bedrooms Count", "Kamro ki tadad"),
    "num__bathrooms": ("Bathrooms Count", "Ghusalkhano ki tadad"),
    "num__age_years": ("Construction Age", "Makan ki umar (saal)"),
    "num__distance_to_main_road_km": ("Distance to Main Boulevard", "Main road se fasla"),
    "num__amenity_score": ("Amenities Score", "Suhuliyat ka score"),
    "num__distance_composite_index": ("Transit & Facility Proximity", "Markaz aur school se qurbat"),
    "high_card_loc__area_society_clean": ("Society Location Benchmark", "Society ki market value"),
    "low_card_cat__is_corner_Yes": ("Corner Plot Feature", "Corner plot ki sahulat"),
    "low_card_cat__is_park_facing_Yes": ("Park Facing Feature", "Park facing ka manzar"),
}


def explain_lead_scoring_model(
    model: Any,
    X_test: np.ndarray,
    feature_names: List[str],
    sample_idx: int = 0,
    save_summary_path: Path = FIGURES_DIR / "05_lead_shap_global_summary.png",
    save_waterfall_path: Path = FIGURES_DIR / "06_lead_shap_local_waterfall.png"
) -> Tuple[np.ndarray, shap.Explanation]:
    """Generates global and local SHAP explanations for the Lead Scoring model."""
    print("Computing SHAP values for Lead Scoring Model...")
    # Use TreeExplainer for tree models (LightGBM/XGBoost/CatBoost)
    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_test)

    # 1. Global Beeswarm Summary Plot
    fig = plt.figure(figsize=(12, 7), dpi=300)
    shap.summary_plot(shap_values, X_test, feature_names=feature_names, show=False, max_display=12)
    plt.title("Lead Scoring Model — Global Feature Attribution (SHAP Beeswarm)", fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(save_summary_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Lead SHAP Global summary: {save_summary_path}")

    # 2. Local Waterfall Plot for sample lead
    fig = plt.figure(figsize=(10, 6), dpi=300)
    # Ensure correct shape for waterfall
    shap_sample = shap_values[sample_idx]
    shap.plots.waterfall(shap_sample, max_display=10, show=False)
    plt.title(f"Lead Scoring — Local SHAP Waterfall (Lead Sample #{sample_idx})", fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(save_waterfall_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Lead SHAP Local waterfall: {save_waterfall_path}")

    return shap_values.values, shap_values


def explain_property_valuation_model(
    property_model_path: Path = DAY2_DIR / "models" / "best_property_valuation_model.joblib",
    save_summary_path: Path = FIGURES_DIR / "07_property_shap_global_summary.png",
    save_waterfall_path: Path = FIGURES_DIR / "08_property_shap_local_waterfall.png"
) -> Tuple[Any, Any]:
    """Generates global and local SHAP explanations for the Day 2 Property Valuation model."""
    print("Computing SHAP values for Property Valuation Model (Day 2 CatBoost)...")
    if not property_model_path.exists():
        print(f"Warning: Property model {property_model_path} not found. Skipping property SHAP.")
        return None, None

    model_dict = joblib.load(property_model_path)
    model = model_dict["model"]
    preprocessor = model_dict["preprocessor"]

    # Load property test split
    props_test = pd.read_csv(WEEK8_DIR / "Day1" / "data" / "processed" / "properties_test.csv")
    from pipelines import audit_and_prepare_features, PROPERTY_LEAKAGE_COLUMNS
    X_raw, _, _ = audit_and_prepare_features(props_test, "price_pkr", PROPERTY_LEAKAGE_COLUMNS)
    X_test_trans = preprocessor.transform(X_raw)
    feat_names = preprocessor.get_feature_names_out().tolist()

    explainer = shap.TreeExplainer(model)
    shap_values = explainer(X_test_trans)

    # 1. Global Beeswarm Summary Plot
    fig = plt.figure(figsize=(12, 7), dpi=300)
    shap.summary_plot(shap_values, X_test_trans, feature_names=feat_names, show=False, max_display=12)
    plt.title("Property Valuation Model — Global Feature Attribution (SHAP Beeswarm)", fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(save_summary_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Property SHAP Global summary: {save_summary_path}")

    # 2. Local Waterfall Plot for sample property
    fig = plt.figure(figsize=(10, 6), dpi=300)
    shap.plots.waterfall(shap_values[0], max_display=10, show=False)
    plt.title("Property Valuation — Local SHAP Waterfall (Sample Listing #0)", fontsize=13, fontweight="bold", pad=12)
    plt.tight_layout()
    fig.savefig(save_waterfall_path, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved Property SHAP Local waterfall: {save_waterfall_path}")

    return shap_values.values, shap_values


def generate_lead_plain_language_reasons(
    shap_vals_row: np.ndarray,
    feature_names: List[str],
    tier: str = "Hot",
    probability: float = 0.85,
    top_n: int = 3
) -> Dict[str, Any]:
    """Translates top SHAP attribution values into fluent English and UrduLish consultative explanations."""
    # Find indices with highest absolute SHAP impact
    top_pos_idx = np.argsort(shap_vals_row)[::-1]
    top_neg_idx = np.argsort(shap_vals_row)

    pos_reasons_en = []
    pos_reasons_ur = []
    neg_reasons_en = []
    neg_reasons_ur = []

    for idx in top_pos_idx[:top_n]:
        val = shap_vals_row[idx]
        if val > 0.05:
            fname = feature_names[idx]
            en_name, ur_name = LEAD_FEATURE_FRIENDLY_NAMES.get(fname, (fname, fname))
            pos_reasons_en.append(f"{en_name} (+{val:.2f})")
            pos_reasons_ur.append(f"{ur_name}")

    for idx in top_neg_idx[:2]:
        val = shap_vals_row[idx]
        if val < -0.05:
            fname = feature_names[idx]
            en_name, ur_name = LEAD_FEATURE_FRIENDLY_NAMES.get(fname, (fname, fname))
            neg_reasons_en.append(f"{en_name} ({val:.2f})")
            neg_reasons_ur.append(f"{ur_name}")

    # Synthesize fluent explanations
    if tier == "Hot":
        en_summary = (
            f"Lead ranked HOT ({probability:.1%} probability). Key drivers: "
            f"{', '.join(pos_reasons_en) if pos_reasons_en else 'Strong general engagement'}."
        )
        ur_reasons_str = ", ".join(pos_reasons_ur) if pos_reasons_ur else "mazboot engagement"
        ur_summary = (
            f"Yeh lead HOT hai ({probability:.1%}) kyun ke {ur_reasons_str} ne conversion imkanat barha diye hain."
        )
    elif tier == "Warm":
        en_summary = (
            f"Lead categorized WARM ({probability:.1%} probability). Positive factors: "
            f"{', '.join(pos_reasons_en) if pos_reasons_en else 'Moderate interest'}, but dampened by: "
            f"{', '.join(neg_reasons_en) if neg_reasons_en else 'follow-up delay'}."
        )
        ur_summary = (
            f"Yeh lead WARM hai ({probability:.1%}). Client ka dilchaspi hai lekin mazid rabtay aur tasalli ki zaroorat hai."
        )
    else:
        en_summary = (
            f"Lead classified COLD ({probability:.1%} probability). Low readiness driven by: "
            f"{', '.join(neg_reasons_en) if neg_reasons_en else 'low response rate'}."
        )
        ur_summary = (
            f"Yeh lead COLD hai ({probability:.1%}) kyun ke client ka response slow hai aur visit schedule nahi hua."
        )

    return {
        "tier": tier,
        "probability": float(probability),
        "explanation_en": en_summary,
        "explanation_ur": ur_summary,
        "top_positive_features": pos_reasons_en,
        "top_negative_features": neg_reasons_en,
    }


def generate_property_plain_language_reasons(
    shap_vals_row: np.ndarray,
    feature_names: List[str],
    predicted_price_pkr: float,
    top_n: int = 3
) -> Dict[str, Any]:
    """Translates property SHAP values into fluent English and UrduLish valuation rationales."""
    top_pos_idx = np.argsort(shap_vals_row)[::-1]
    top_neg_idx = np.argsort(shap_vals_row)

    pos_drivers_en = []
    pos_drivers_ur = []
    neg_drivers_en = []
    neg_drivers_ur = []

    for idx in top_pos_idx[:top_n]:
        val = shap_vals_row[idx]
        if val > 0.05:
            fname = feature_names[idx]
            en_name, ur_name = PROPERTY_FEATURE_FRIENDLY_NAMES.get(fname, (fname, fname))
            pos_drivers_en.append(en_name)
            pos_drivers_ur.append(ur_name)

    for idx in top_neg_idx[:2]:
        val = shap_vals_row[idx]
        if val < -0.05:
            fname = feature_names[idx]
            en_name, ur_name = PROPERTY_FEATURE_FRIENDLY_NAMES.get(fname, (fname, fname))
            neg_drivers_en.append(en_name)
            neg_drivers_ur.append(ur_name)

    price_crore = predicted_price_pkr / 1e7
    price_str = f"{price_crore:.2f} Crore PKR"

    en_summary = (
        f"Valuation assessed at {price_str}. Upward value driven by {', '.join(pos_drivers_en)}."
        + (f" Downward adjustments from {', '.join(neg_drivers_en)}." if neg_drivers_en else "")
    )

    ur_summary = (
        f"Is property ki andazan qeemat {price_str} tay hui hai. "
        f"Qeemat barhanay walay awamil: {', '.join(pos_drivers_ur)}."
        + (f" Jabke {', '.join(neg_drivers_ur)} ne qeemat par thora manfi asar dala." if neg_drivers_ur else "")
    )

    return {
        "predicted_price_pkr": float(predicted_price_pkr),
        "explanation_en": en_summary,
        "explanation_ur": ur_summary,
        "positive_drivers": pos_drivers_en,
        "negative_drivers": neg_drivers_en,
    }
