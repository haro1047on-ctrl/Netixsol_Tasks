"""Feature Engineering Module for Property Valuation and Lead Scoring.

Implements 12 domain-specific features with clear business justifications:
1. price_per_marla (unit rate for baseline analysis)
2. property_age_bucket (non-linear structural depreciation)
3. society_tier (prestige and municipal development index)
4. amenity_score (weighted utility value of luxury features)
5. distance_composite_index (holistic urban accessibility score)
6. covered_to_plot_ratio (construction density indicator)
7. bed_to_bath_ratio (en-suite layout modern design index)
8. lead_engagement_score (cumulative voice attention time)
9. response_speed_category (inbound response latency tier)
10. budget_to_market_ratio (buyer purchasing realism indicator)
11. interaction_intensity (touchpoint velocity per day)
12. objection_severity_score (ordinal friction barrier metric)
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import pandas as pd


# ---------------------------------------------------------
# MAPPINGS AND CONFIGURATIONS
# ---------------------------------------------------------

SOCIETY_TIER_MAPPING: Dict[str, str] = {
    # Tier 1 - Elite
    "DHA Phase 5": "Tier 1 - Elite",
    "DHA Phase 6": "Tier 1 - Elite",
    "Gulberg III": "Tier 1 - Elite",
    "Model Town": "Tier 1 - Elite",
    "Sector F-7": "Tier 1 - Elite",
    "Sector F-10": "Tier 1 - Elite",
    "DHA Phase 2": "Tier 1 - Elite",
    "Clifton Block 5": "Tier 1 - Elite",
    "DHA Phase 8": "Tier 1 - Elite",
    "DHA Phase 1": "Tier 1 - Elite",
    "Kohinoor City": "Tier 1 - Elite",

    # Tier 2 - Prime
    "Bahria Town Sector C": "Tier 2 - Prime",
    "Johar Town Phase 2": "Tier 2 - Prime",
    "Sector G-11": "Tier 2 - Prime",
    "Bahria Town Phase 7": "Tier 2 - Prime",
    "PECHS Block 6": "Tier 2 - Prime",
    "Gulshan-e-Iqbal Block 13": "Tier 2 - Prime",
    "Bahria Town Phase 4": "Tier 2 - Prime",
    "Chaklala Scheme 3": "Tier 2 - Prime",
    "Satellite Town": "Tier 2 - Prime",
    "Canal Road": "Tier 2 - Prime",
    "Madina Town": "Tier 2 - Prime",

    # Tier 3 - Developing / Budget
    "Wapda Town": "Tier 3 - Developing",
    "Lake City": "Tier 3 - Developing",
    "B-17 Multi Gardens": "Tier 3 - Developing",
    "Bahria Town Karachi": "Tier 3 - Developing",
    "North Nazimabad": "Tier 3 - Developing",
    "Gulraiz Housing Scheme": "Tier 3 - Developing",
    "Wapda City": "Tier 3 - Developing",
}

AMENITY_WEIGHTS: Dict[str, float] = {
    "Backup Generator": 2.0,       # Critical utility due to load-shedding
    "Solar System": 2.0,           # High electricity tariff hedge
    "Gated Security": 1.5,          # Safety premium
    "Servant Quarter": 1.5,        # Cultural norm for domestic help
    "Lawn": 1.0,                   # Green space amenity
    "Dedicated Parking": 1.0,      # Vehicle safety
    "Water Filtration Plant": 1.0, # Clean water availability
    "Swimming Pool": 1.5,          # Luxury status
}

OBJECTION_SEVERITY_MAP: Dict[str, int] = {
    "None": 0,
    "Waiting for family approval": 1,
    "Location too far": 2,
    "Legal document questions": 3,
    "Low trust in scheme/NOC": 4,
    "Price too high": 4,
    "No response / Call dropped": 5,
}


# ---------------------------------------------------------
# PROPERTY FEATURE ENGINEERING
# ---------------------------------------------------------

def engineer_property_features(df_in: pd.DataFrame) -> pd.DataFrame:
    """Computes engineered features for property listings."""
    df = df_in.copy()

    # 1. Price Per Marla (Note: Target derived; for analysis only, drop before model training)
    df["price_per_marla"] = df["price_pkr"] / df["plot_size_marla"]

    # 2. Property Age Bucket
    # [0-1 yr: Brand New], [2-5 yrs: Modern], [6-15 yrs: Established], [16+ yrs: Vintage]
    def age_to_bucket(age: float) -> str:
        if age <= 1.0:
            return "Brand New (0-1 yr)"
        elif age <= 5.0:
            return "Modern (2-5 yrs)"
        elif age <= 15.0:
            return "Established (6-15 yrs)"
        else:
            return "Vintage (16+ yrs)"

    df["property_age_bucket"] = df["age_years"].apply(age_to_bucket)

    # 3. Society Tier (Prestige index)
    df["society_tier"] = df["area_society_clean"].map(SOCIETY_TIER_MAPPING).fillna("Tier 2 - Prime")

    # 4. Amenity Score (Weighted utility index)
    def compute_amenity_score(amenities_str: any) -> float:
        if not isinstance(amenities_str, str):
            return 0.0
        score = 0.0
        for item, weight in AMENITY_WEIGHTS.items():
            if item.lower() in amenities_str.lower():
                score += weight
        return round(score, 1)

    df["amenity_score"] = df["amenities"].apply(compute_amenity_score)

    # 5. Distance Composite Index (Weighted accessibility metric)
    # Higher score = further away from urban amenities
    df["distance_composite_index"] = (
        0.40 * df["distance_to_main_road_km"] +
        0.30 * df["distance_to_hospital_km"] +
        0.30 * df["distance_to_school_km"]
    ).round(2)

    # 6. Covered-to-Plot Ratio (Building density indicator)
    # Plot size marla to sqft = marla * 225
    df["plot_area_sqft"] = df["plot_size_marla"] * 225.0
    df["covered_to_plot_ratio"] = (df["covered_area_sqft"] / df["plot_area_sqft"]).round(2)

    # 7. Bed-to-Bath Ratio (En-suite modern layout indicator)
    df["bed_to_bath_ratio"] = (df["bedrooms"] / (df["bathrooms"] + 0.001)).round(2)

    # 8. Luxury Plot Flag (Corner or Park Facing)
    df["is_luxury_plot"] = ((df["is_corner"] == "Yes") | (df["is_park_facing"] == "Yes")).astype(int)

    return df


# ---------------------------------------------------------
# LEADS FEATURE ENGINEERING
# ---------------------------------------------------------

def engineer_leads_features(df_in: pd.DataFrame, df_properties_ref: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Computes engineered features for CRM leads."""
    df = df_in.copy()

    # 1. Lead Engagement Score (Voice interaction depth)
    df["lead_engagement_score"] = (df["number_of_calls"] * df["avg_call_duration_mins"]).round(1)

    # 2. Response Speed Category
    def categorize_response(hours: float) -> str:
        if hours < 0.25:
            return "Immediate (<15m)"
        elif hours <= 1.0:
            return "Fast (15-60m)"
        elif hours <= 6.0:
            return "Standard (1-6h)"
        else:
            return "Delayed (>6h)"

    df["response_speed_category"] = df["response_time_hours"].apply(categorize_response)

    # 3. Interaction Intensity (Calls per day since inquiry)
    df["interaction_intensity"] = (df["number_of_calls"] / (df["days_since_first_contact"] + 1.0)).round(3)

    # 4. Objection Severity Score (Ordinal scale 0 to 5)
    df["objection_severity_score"] = df["objection_raised"].map(OBJECTION_SEVERITY_MAP).fillna(0).astype(int)

    # 5. Budget-to-Market-Price Ratio
    # Compute benchmark prices from properties if provided, else reasonable defaults
    if df_properties_ref is not None:
        market_benchmarks = df_properties_ref.groupby(["city", "property_type"])["price_pkr"].median().to_dict()
    else:
        # Fallback realistic defaults in PKR
        market_benchmarks = {
            ("Lahore", "House"): 35000000.0,
            ("Lahore", "Flat"): 12000000.0,
            ("Islamabad", "House"): 45000000.0,
            ("Islamabad", "Flat"): 15000000.0,
            ("Karachi", "House"): 40000000.0,
            ("Karachi", "Flat"): 14000000.0,
            ("Rawalpindi", "House"): 22000000.0,
            ("Rawalpindi", "Flat"): 8500000.0,
            ("Faisalabad", "House"): 18000000.0,
            ("Faisalabad", "Flat"): 7000000.0,
        }

    def compute_budget_ratio(row: pd.Series) -> float:
        city = row.get("preferred_city", "Lahore")
        ptype = row.get("property_type", "House")
        purpose = row.get("purpose", "Buy")
        budget = row.get("budget_pkr", 20000000.0)

        if purpose == "Rent":
            # Typical rental price benchmark is ~0.35% to 0.45% of property value per month
            base_prop_val = market_benchmarks.get((city, ptype), 25000000.0)
            expected_rent = base_prop_val * 0.0035
            return round(min(5.0, budget / (expected_rent + 1.0)), 2)
        else:
            expected_price = market_benchmarks.get((city, ptype), 25000000.0)
            return round(min(5.0, budget / (expected_price + 1.0)), 2)

    df["budget_to_market_ratio"] = df.apply(compute_budget_ratio, axis=1)

    # 6. High Intent Flag
    # Combines visit booked with high engagement or fast response
    df["is_high_intent"] = (
        (df["visit_booked"] == "Yes") &
        (df["lead_engagement_score"] >= 8.0)
    ).astype(int)

    return df


if __name__ == "__main__":
    PROC_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

    print("--- Engineering Properties Features ---")
    df_clean_props = pd.read_csv(PROC_DIR / "cleaned_properties.csv")
    df_feat_props = engineer_property_features(df_clean_props)
    df_feat_props.to_csv(PROC_DIR / "cleaned_properties.csv", index=False)
    print(f"Properties features added: {df_feat_props.columns.tolist()[-8:]}")

    print("\n--- Engineering Leads Features ---")
    df_clean_leads = pd.read_csv(PROC_DIR / "cleaned_leads.csv")
    df_feat_leads = engineer_leads_features(df_clean_leads, df_feat_props)
    df_feat_leads.to_csv(PROC_DIR / "cleaned_leads.csv", index=False)
    print(f"Leads features added: {df_feat_leads.columns.tolist()[-6:]}")
