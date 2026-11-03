"""Data Generator for Real Estate Property Valuation and Lead Scoring.

Generates realistic Pakistani real estate listings and CRM inbound leads data
with realistic noise, Pakistani price representations ('crore', 'lac'),
mixed area units ('marla', 'kanal', 'sq ft', 'sq yd'), location spelling variations,
missing values, duplicate listings, and outliers.
"""
from __future__ import annotations

import datetime
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd

# Set fixed random seed for reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# CONSTANTS & METADATA FOR PAKISTANI REAL ESTATE
# ---------------------------------------------------------

CITIES = ["Lahore", "Islamabad", "Karachi", "Rawalpindi", "Faisalabad"]

# Base price per marla ranges in PKR by city and society
SOCIETIES_CONFIG: Dict[str, Dict[str, Dict[str, any]]] = {
    "Lahore": {
        "DHA Phase 5": {"base_ppm": 4200000, "tier": "Tier 1 - Elite", "variations": ["DHA Phase 5", "DHA Ph 5", "DHA-5", "DHA Phase V"]},
        "DHA Phase 6": {"base_ppm": 3800000, "tier": "Tier 1 - Elite", "variations": ["DHA Phase 6", "DHA Ph 6", "DHA-6"]},
        "Gulberg III": {"base_ppm": 5500000, "tier": "Tier 1 - Elite", "variations": ["Gulberg III", "Gulberg 3", "Gulberg-3", "Gulberg"]},
        "Bahria Town Sector C": {"base_ppm": 2100000, "tier": "Tier 2 - Prime", "variations": ["Bahria Town Sector C", "Bahria Town Sec C", "Bahria Sec C"]},
        "Johar Town Phase 2": {"base_ppm": 2600000, "tier": "Tier 2 - Prime", "variations": ["Johar Town Phase 2", "Johar Town Ph 2", "Johar Town 2"]},
        "Model Town": {"base_ppm": 4500000, "tier": "Tier 1 - Elite", "variations": ["Model Town", "Model Town Block C", "Model Town Society"]},
        "Wapda Town": {"base_ppm": 1900000, "tier": "Tier 3 - Developing", "variations": ["Wapda Town", "Wapda Town Phase 1", "Wapda Town Ph 1"]},
        "Lake City": {"base_ppm": 1800000, "tier": "Tier 3 - Developing", "variations": ["Lake City", "Lake City Sector M"]},
    },
    "Islamabad": {
        "Sector F-7": {"base_ppm": 7000000, "tier": "Tier 1 - Elite", "variations": ["Sector F-7", "F-7", "F 7", "Sector F7"]},
        "Sector F-10": {"base_ppm": 5200000, "tier": "Tier 1 - Elite", "variations": ["Sector F-10", "F-10", "F 10", "Sector F10"]},
        "Sector G-11": {"base_ppm": 3100000, "tier": "Tier 2 - Prime", "variations": ["Sector G-11", "G-11", "G 11", "Sector G11"]},
        "DHA Phase 2": {"base_ppm": 3600000, "tier": "Tier 1 - Elite", "variations": ["DHA Phase 2", "DHA Ph 2", "DHA-2 Islamabad"]},
        "Bahria Town Phase 7": {"base_ppm": 2400000, "tier": "Tier 2 - Prime", "variations": ["Bahria Town Phase 7", "Bahria Town Ph 7", "Bahria Phase 7"]},
        "B-17 Multi Gardens": {"base_ppm": 1300000, "tier": "Tier 3 - Developing", "variations": ["B-17 Multi Gardens", "B-17", "Multi Gardens B-17"]},
    },
    "Karachi": {
        "Clifton Block 5": {"base_ppm": 6800000, "tier": "Tier 1 - Elite", "variations": ["Clifton Block 5", "Clifton Blk 5", "Clifton Block V", "Clifton"]},
        "DHA Phase 8": {"base_ppm": 5000000, "tier": "Tier 1 - Elite", "variations": ["DHA Phase 8", "DHA Ph 8", "DHA Phase VIII", "DHA-8"]},
        "PECHS Block 6": {"base_ppm": 3300000, "tier": "Tier 2 - Prime", "variations": ["PECHS Block 6", "PECHS Blk 6", "PECHS"]},
        "Gulshan-e-Iqbal Block 13": {"base_ppm": 2200000, "tier": "Tier 2 - Prime", "variations": ["Gulshan-e-Iqbal Block 13", "Gulshan e Iqbal 13", "Gulshan Block 13"]},
        "Bahria Town Karachi": {"base_ppm": 1400000, "tier": "Tier 3 - Developing", "variations": ["Bahria Town Karachi", "BTK", "Bahria Town Precinct 10"]},
        "North Nazimabad": {"base_ppm": 1900000, "tier": "Tier 3 - Developing", "variations": ["North Nazimabad", "North Nazimabad Block H", "N Nazimabad"]},
    },
    "Rawalpindi": {
        "Bahria Town Phase 4": {"base_ppm": 2300000, "tier": "Tier 2 - Prime", "variations": ["Bahria Town Phase 4", "Bahria Town Ph 4", "Bahria Phase 4"]},
        "DHA Phase 1": {"base_ppm": 3200000, "tier": "Tier 1 - Elite", "variations": ["DHA Phase 1", "DHA Ph 1", "DHA-1 Rawalpindi"]},
        "Chaklala Scheme 3": {"base_ppm": 2800000, "tier": "Tier 2 - Prime", "variations": ["Chaklala Scheme 3", "Chaklala Scheme III", "Scheme 3"]},
        "Satellite Town": {"base_ppm": 2500000, "tier": "Tier 2 - Prime", "variations": ["Satellite Town", "Satellite Town Block C"]},
        "Gulraiz Housing Scheme": {"base_ppm": 1200000, "tier": "Tier 3 - Developing", "variations": ["Gulraiz Housing Scheme", "Gulraiz", "Gulraiz Phase 2"]},
    },
    "Faisalabad": {
        "Canal Road": {"base_ppm": 2200000, "tier": "Tier 2 - Prime", "variations": ["Canal Road", "Canal Expressway", "Canal Villas"]},
        "Madina Town": {"base_ppm": 2400000, "tier": "Tier 2 - Prime", "variations": ["Madina Town", "Madina Town Block X"]},
        "Kohinoor City": {"base_ppm": 2900000, "tier": "Tier 1 - Elite", "variations": ["Kohinoor City", "Kohinoor City Block A"]},
        "Wapda City": {"base_ppm": 1100000, "tier": "Tier 3 - Developing", "variations": ["Wapda City", "Wapda City Phase 1"]},
    },
}

PROPERTY_TYPES = [
    ("House", 0.60),
    ("Flat", 0.22),
    ("Upper Portion", 0.08),
    ("Lower Portion", 0.06),
    ("Farmhouse", 0.02),
    ("Penthouse", 0.02),
]

ALL_AMENITIES = [
    "Gated Security",
    "Servant Quarter",
    "Backup Generator",
    "Lawn",
    "Solar System",
    "Swimming Pool",
    "Dedicated Parking",
    "Water Filtration Plant",
]

OBJECTIONS = [
    "None",
    "Price too high",
    "Location too far",
    "Waiting for family approval",
    "Low trust in scheme/NOC",
    "Legal document questions",
    "No response / Call dropped",
]


def format_pakistani_price(price: float) -> str:
    """Formats float price into realistic Pakistani format (crore, lac, numeric)."""
    r = random.random()
    if r < 0.55:
        # Format as Crore if >= 1 Crore (10,000,000)
        if price >= 10000000:
            crores = round(price / 10000000, 2)
            unit = random.choice(["Crore", "crore", "Cr", "Crores"])
            return f"{crores} {unit}"
        else:
            lacs = round(price / 100000, 1)
            unit = random.choice(["Lac", "lac", "Lakh", "Lacs"])
            return f"{lacs} {unit}"
    elif r < 0.85:
        # Format as Lac if under 5 Crore
        if price < 50000000:
            lacs = round(price / 100000, 1)
            unit = random.choice(["Lac", "lac", "Lakh", "Lacs"])
            return f"{lacs} {unit}"
        else:
            crores = round(price / 10000000, 2)
            return f"{crores} Crore"
    else:
        # Numeric string (with or without comma formatting)
        if random.random() < 0.5:
            return f"{int(price):,}"
        return str(int(price))


def generate_plot_size_raw() -> Tuple[str, float]:
    """Generates raw plot size string and its normalized marla equivalent."""
    # Standard sizes: 3, 5, 7, 10, 20 (1 Kanal), 40 (2 Kanal) marlas
    size_choices = [
        (3.0, 0.08),
        (5.0, 0.40),
        (7.0, 0.07),
        (10.0, 0.28),
        (20.0, 0.14),  # 1 Kanal
        (40.0, 0.03),  # 2 Kanal
    ]
    marla_values, weights = zip(*size_choices)
    marla = random.choices(marla_values, weights=weights, k=1)[0]

    fmt_type = random.random()
    if marla == 20.0:
        if fmt_type < 0.70:
            raw_str = random.choice(["1 Kanal", "1 kanal", "1-Kanal", "1Kanal"])
        elif fmt_type < 0.85:
            raw_str = random.choice(["20 Marla", "20 marla", "20-Marla"])
        else:
            raw_str = random.choice(["500 Sq. Yd.", "500 Sq Yd", "4500 Sq. Ft."])
    elif marla == 40.0:
        if fmt_type < 0.75:
            raw_str = random.choice(["2 Kanal", "2 kanal", "2-Kanal"])
        else:
            raw_str = random.choice(["40 Marla", "1000 Sq. Yd.", "9000 Sq. Ft."])
    elif marla == 5.0:
        if fmt_type < 0.65:
            raw_str = random.choice(["5 Marla", "5 marla", "5-Marla", "5Marla"])
        elif fmt_type < 0.85:
            raw_str = random.choice(["125 Sq. Yd.", "125 Sq Yd", "125 Sq. Yards"])
        else:
            raw_str = random.choice(["1125 Sq. Ft.", "1125 Sq Ft", "1125 SqFt"])
    elif marla == 10.0:
        if fmt_type < 0.65:
            raw_str = random.choice(["10 Marla", "10 marla", "10-Marla", "10Marla"])
        elif fmt_type < 0.85:
            raw_str = random.choice(["250 Sq. Yd.", "250 Sq Yd", "250 Sq. Yards"])
        else:
            raw_str = random.choice(["2250 Sq. Ft.", "2250 Sq Ft"])
    else:
        raw_str = f"{int(marla)} Marla"

    return raw_str, marla


# ---------------------------------------------------------
# DATASET A: PROPERTY LISTINGS GENERATOR
# ---------------------------------------------------------

def generate_property_listings(num_rows: int = 6000) -> pd.DataFrame:
    """Generates realistic Pakistani property listings with noise and inconsistencies."""
    data = []
    start_date = datetime.date(2025, 1, 1)

    for i in range(num_rows):
        prop_id = f"PK-PROP-{100000 + i}"
        city = random.choice(CITIES)
        society_dict = SOCIETIES_CONFIG[city]
        canonical_society = random.choice(list(society_dict.keys()))
        society_meta = society_dict[canonical_society]

        # Use spelling/format variation for raw data
        area_society = random.choice(society_meta["variations"])
        base_ppm = society_meta["base_ppm"]

        # Property type
        prop_types, prop_weights = zip(*PROPERTY_TYPES)
        property_type = random.choices(prop_types, weights=prop_weights, k=1)[0]

        # Plot size
        plot_size_raw, plot_size_marla = generate_plot_size_raw()

        # Property type modifications
        if property_type == "Flat":
            if plot_size_marla > 10.0:
                plot_size_marla = random.choice([3.0, 5.0, 7.0])
                plot_size_raw = f"{int(plot_size_marla * 225)} Sq. Ft."
            floors = random.choice([1, 1, 1, 2])
        elif property_type in ["Upper Portion", "Lower Portion"]:
            floors = 1
        elif property_type == "Farmhouse":
            plot_size_marla = random.choice([20.0, 40.0, 60.0])
            plot_size_raw = f"{int(plot_size_marla / 20)} Kanal"
            floors = random.choice([1, 2])
        elif property_type == "Penthouse":
            plot_size_marla = random.choice([7.0, 10.0, 15.0])
            plot_size_raw = f"{int(plot_size_marla * 225)} Sq. Ft."
            floors = random.choice([1, 2])
        else:  # House
            floors = random.choices([1, 2, 3], weights=[0.20, 0.70, 0.10], k=1)[0]

        # Covered area calculation based on plot size & floors
        # 1 marla = 225 sq ft
        ground_footprint = plot_size_marla * 225.0 * random.uniform(0.70, 0.85)
        covered_area_sqft = round(ground_footprint * floors * random.uniform(0.90, 1.05))
        covered_area_raw = f"{covered_area_sqft} Sq. Ft."

        # Bedrooms & bathrooms
        if plot_size_marla <= 3.0:
            bedrooms = random.choice([1, 2])
            bathrooms = random.choice([1, 2])
        elif plot_size_marla <= 5.0:
            bedrooms = random.choices([2, 3, 4], weights=[0.2, 0.6, 0.2], k=1)[0]
            bathrooms = bedrooms + random.choice([0, 1, -1])
            bathrooms = max(1, min(5, bathrooms))
        elif plot_size_marla <= 10.0:
            bedrooms = random.choices([3, 4, 5, 6], weights=[0.1, 0.4, 0.4, 0.1], k=1)[0]
            bathrooms = bedrooms + random.choice([0, 1])
        else:  # 1 Kanal+
            bedrooms = random.choices([4, 5, 6, 7], weights=[0.2, 0.5, 0.2, 0.1], k=1)[0]
            bathrooms = bedrooms + random.choice([0, 1, 2])

        # Age of property (years)
        age_years = round(random.choices(
            [random.uniform(0, 1), random.uniform(1, 5), random.uniform(5, 15), random.uniform(15, 30)],
            weights=[0.30, 0.35, 0.25, 0.10],
            k=1
        )[0], 1)

        # Corner and park facing
        is_corner = random.choices(["Yes", "No"], weights=[0.18, 0.82], k=1)[0]
        is_park_facing = random.choices(["Yes", "No"], weights=[0.14, 0.86], k=1)[0]

        # Amenities
        num_amenities = random.choices([1, 2, 3, 4, 5, 6], weights=[0.15, 0.25, 0.30, 0.15, 0.10, 0.05], k=1)[0]
        amenities = random.sample(ALL_AMENITIES, num_amenities)
        amenities_str = ", ".join(amenities)

        # Distances (in km)
        dist_main_road = round(random.uniform(0.1, 4.5), 2)
        dist_school = round(random.uniform(0.2, 6.0), 2)
        dist_hospital = round(random.uniform(0.3, 8.5), 2)

        # Listing date
        list_days_ago = random.randint(1, 450)
        listing_date = (datetime.date.today() - datetime.timedelta(days=list_days_ago)).isoformat()

        # BASE PRICE COMPUTATION (Realistic Valuation Model)
        # Price = Plot Size * Base PPM * Type Multiplier * Age Depreciation * Features
        type_multiplier = {
            "House": 1.0,
            "Flat": 0.65,
            "Upper Portion": 0.40,
            "Lower Portion": 0.48,
            "Farmhouse": 1.45,
            "Penthouse": 1.25,
        }[property_type]

        # Age depreciation: drops ~1.2% per year up to 30% max
        age_factor = max(0.68, 1.0 - (age_years * 0.012))

        # Premium factors
        corner_premium = 1.08 if is_corner == "Yes" else 1.0
        park_premium = 1.07 if is_park_facing == "Yes" else 1.0
        amenity_bonus = 1.0 + (len(amenities) * 0.018)

        # Proximity discount
        distance_factor = max(0.85, 1.0 - (dist_main_road * 0.02) - (dist_hospital * 0.01))

        # Intrinsic market valuation
        market_price = (
            plot_size_marla * base_ppm * type_multiplier * age_factor *
            corner_premium * park_premium * amenity_bonus * distance_factor
        )

        # Add realistic market noise (+/- 10%)
        noise_pct = random.gauss(0, 0.07)
        final_price = market_price * (1.0 + noise_pct)
        final_price = max(800000.0, round(final_price, -4))  # rounded to nearest 10,000 PKR

        raw_price_str = format_pakistani_price(final_price)

        row = {
            "property_id": prop_id,
            "city": city,
            "area_society": area_society,
            "property_type": property_type,
            "plot_size_raw": plot_size_raw,
            "covered_area_raw": covered_area_raw,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "age_years": age_years,
            "floors": floors,
            "is_corner": is_corner,
            "is_park_facing": is_park_facing,
            "amenities": amenities_str,
            "distance_to_main_road_km": dist_main_road,
            "distance_to_school_km": dist_school,
            "distance_to_hospital_km": dist_hospital,
            "listing_date": listing_date,
            "raw_price_str": raw_price_str,
            "price_pkr": final_price,
        }
        data.append(row)

    df = pd.DataFrame(data)

    # ---------------------------------------------------------
    # INJECT REALISTIC MESSY DATA ANOMALIES
    # ---------------------------------------------------------
    # 1. Missing values (~3-5% on bathrooms, floors, covered_area_raw, distance_to_hospital_km)
    mask_bath = np.random.rand(len(df)) < 0.04
    df.loc[mask_bath, "bathrooms"] = np.nan

    mask_floors = np.random.rand(len(df)) < 0.05
    df.loc[mask_floors, "floors"] = np.nan

    mask_cov = np.random.rand(len(df)) < 0.035
    df.loc[mask_cov, "covered_area_raw"] = np.nan

    mask_hosp = np.random.rand(len(df)) < 0.04
    df.loc[mask_hosp, "distance_to_hospital_km"] = np.nan

    # 2. Duplicate listings (simulate multiple agents listing same properties, ~180 duplicates)
    dup_indices = np.random.choice(df.index, size=180, replace=False)
    duplicates = df.loc[dup_indices].copy()
    # vary listing id and price slightly for duplicates
    duplicates["property_id"] = [f"PK-PROP-DUP-{1000 + k}" for k in range(len(duplicates))]
    df = pd.concat([df, duplicates], ignore_index=True)

    # 3. Inject extreme outliers / typos (e.g. 50,000 PKR instead of 5 Crore, or 999 Crore typo)
    typo_indices = np.random.choice(df.index, size=25, replace=False)
    for idx in typo_indices[:12]:
        # Underpriced typo (missing zeros)
        df.loc[idx, "price_pkr"] = 55000.0
        df.loc[idx, "raw_price_str"] = "55 Thousand"
    for idx in typo_indices[12:]:
        # Absurdly overpriced typo (fake price)
        df.loc[idx, "price_pkr"] = 9990000000.0
        df.loc[idx, "raw_price_str"] = "999 Crore"

    return df


# ---------------------------------------------------------
# DATASET B: LEADS CLASSIFICATION GENERATOR
# ---------------------------------------------------------

FIRST_NAMES = ["Muhammad", "Ahmed", "Ali", "Usman", "Bilal", "Zubair", "Hamza", "Fahad", "Saad", "Omer", "Tariq", "Imran", "Fatima", "Ayesha", "Zainab", "Sana", "Mariam", "Hina"]
LAST_NAMES = ["Khan", "Malik", "Chaudhry", "Sheikh", "Bhatti", "Qureshi", "Siddiqui", "Raza", "Abbasi", "Mirza", "Shah", "Dar", "Butt", "Javed"]

def generate_leads_dataset(num_rows: int = 3600) -> pd.DataFrame:
    """Generates realistic inbound real estate leads data reflecting CRM interactions."""
    data = []

    for i in range(num_rows):
        lead_id = f"LEAD-{2025000 + i}"
        client_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        phone = f"+92-3{random.randint(10, 49)}-{random.randint(1000000, 9999999)}"

        lead_source = random.choices(
            ["WhatsApp", "Call", "Website", "Facebook"],
            weights=[0.35, 0.30, 0.20, 0.15],
            k=1
        )[0]

        preferred_city = random.choice(CITIES)
        property_type = random.choices(["House", "Flat", "Plot", "Commercial"], weights=[0.55, 0.25, 0.15, 0.05], k=1)[0]
        purpose = random.choices(["Buy", "Rent", "Invest"], weights=[0.60, 0.25, 0.15], k=1)[0]

        # Budget calculation based on purpose and city
        if purpose == "Rent":
            budget_pkr = random.choice([35000, 50000, 75000, 120000, 200000, 350000])
        else:
            budget_pkr = random.choices(
                [8500000, 15000000, 25000000, 40000000, 75000000, 120000000],
                weights=[0.20, 0.30, 0.25, 0.15, 0.07, 0.03],
                k=1
            )[0]

        budget_raw = format_pakistani_price(budget_pkr)

        # Engagement metrics
        number_of_calls = random.choices([1, 2, 3, 4, 5, 6, 8, 10], weights=[0.35, 0.25, 0.15, 0.10, 0.07, 0.04, 0.02, 0.02], k=1)[0]
        avg_call_duration_mins = round(random.choices(
            [random.uniform(0.5, 2.5), random.uniform(2.5, 6.0), random.uniform(6.0, 15.0)],
            weights=[0.40, 0.45, 0.15],
            k=1
        )[0], 1)

        response_time_hours = round(random.choices(
            [random.uniform(0.1, 0.5), random.uniform(0.5, 3.0), random.uniform(3.0, 12.0), random.uniform(12.0, 48.0)],
            weights=[0.30, 0.40, 0.20, 0.10],
            k=1
        )[0], 2)

        visit_booked = random.choices(["Yes", "No"], weights=[0.22, 0.78], k=1)[0]
        days_since_first_contact = random.randint(1, 90)

        # Objection raised
        objection_weights = [0.35, 0.20, 0.12, 0.14, 0.07, 0.05, 0.07]
        objection_raised = random.choices(OBJECTIONS, weights=objection_weights, k=1)[0]

        # CONVERSION PROBABILITY LOGIC (Ground truth scoring logic)
        # In real estate, baseline conversion is ~15%
        log_odds = -2.2  # baseline ~10%

        # Source factor
        if lead_source == "WhatsApp":
            log_odds += 0.45
        elif lead_source == "Call":
            log_odds += 0.35
        elif lead_source == "Facebook":
            log_odds -= 0.50

        # Purpose factor
        if purpose == "Buy":
            log_odds += 0.25
        elif purpose == "Invest":
            log_odds += 0.35
        elif purpose == "Rent":
            log_odds -= 0.20

        # Engagement factors
        log_odds += (number_of_calls - 1) * 0.28
        log_odds += (avg_call_duration_mins - 3.0) * 0.14
        log_odds -= math.log1p(response_time_hours) * 0.35

        # In-person visit booked is the strongest signal!
        if visit_booked == "Yes":
            log_odds += 1.65

        # Objections
        if objection_raised == "None":
            log_odds += 0.60
        elif objection_raised in ["Price too high", "Low trust in scheme/NOC"]:
            log_odds -= 0.85
        elif objection_raised == "No response / Call dropped":
            log_odds -= 1.80

        # Convert to probability
        prob = 1.0 / (1.0 + math.exp(-log_odds))
        converted = "Yes" if random.random() < prob else "No"

        row = {
            "lead_id": lead_id,
            "client_name": client_name,
            "phone": phone,
            "lead_source": lead_source,
            "budget_raw": budget_raw,
            "budget_pkr": budget_pkr,
            "preferred_city": preferred_city,
            "property_type": property_type,
            "purpose": purpose,
            "number_of_calls": number_of_calls,
            "avg_call_duration_mins": avg_call_duration_mins,
            "response_time_hours": response_time_hours,
            "visit_booked": visit_booked,
            "days_since_first_contact": days_since_first_contact,
            "objection_raised": objection_raised,
            "converted": converted,
        }
        data.append(row)

    df = pd.DataFrame(data)

    # ---------------------------------------------------------
    # INJECT REALISTIC MESSY DATA ANOMALIES
    # ---------------------------------------------------------
    # 1. Missing values (~3-4% on response_time_hours, objection_raised)
    mask_resp = np.random.rand(len(df)) < 0.035
    df.loc[mask_resp, "response_time_hours"] = np.nan

    mask_obj = np.random.rand(len(df)) < 0.04
    df.loc[mask_obj, "objection_raised"] = np.nan

    # 2. Inbound lead duplicates (~90 duplicates from multi-channel queries)
    dup_indices = np.random.choice(df.index, size=90, replace=False)
    duplicates = df.loc[dup_indices].copy()
    duplicates["lead_id"] = [f"LEAD-DUP-{3000 + k}" for k in range(len(duplicates))]
    df = pd.concat([df, duplicates], ignore_index=True)

    return df


if __name__ == "__main__":
    print("Generating Dataset A (Property Listings)...")
    df_props = generate_property_listings(num_rows=6000)
    props_path = OUTPUT_DIR / "raw_properties.csv"
    df_props.to_csv(props_path, index=False)
    print(f"Saved {len(df_props)} property listings to {props_path}")

    print("\nGenerating Dataset B (CRM Leads)...")
    df_leads = generate_leads_dataset(num_rows=3600)
    leads_path = OUTPUT_DIR / "raw_leads.csv"
    df_leads.to_csv(leads_path, index=False)
    print(f"Saved {len(df_leads)} leads to {leads_path}")
    print(f"Conversion distribution:\n{df_leads['converted'].value_counts(normalize=True)}")
