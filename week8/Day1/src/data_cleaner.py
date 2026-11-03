"""Data Cleaning & Standardization Pipeline for Real Estate and CRM Leads.

Implements:
1. Missing value imputation with rigorous domain justifications
2. Deduplication of multi-agent and multi-inquiry records
3. Pakistani currency normalization ('crore', 'lac', numeric -> PKR)
4. Land area normalization (marla, kanal, sq ft, sq yd -> standardized marla & sq ft)
5. Outlier detection using IQR and domain-informed bounds
6. Location name fuzzy and regex standardization
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


# ---------------------------------------------------------
# REGEX & STRING NORMALIZATION HELPERS
# ---------------------------------------------------------

def normalize_price(price_str: any) -> Optional[float]:
    """Converts Pakistani colloquial price strings to numeric PKR float.
    
    Examples:
        '1.5 Crore' -> 15,000,000.0
        '85 Lac' -> 8,500,000.0
        '45 Lacs' -> 4,500,000.0
        '55 Thousand' -> 55,000.0
        '25,000,000' -> 25,000,000.0
    """
    if pd.isna(price_str):
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)

    s = str(price_str).strip().replace(",", "")

    # Check for Crore / Cr
    crore_match = re.search(r"([\d\.]+)\s*(?:crore|cr|crores)", s, re.IGNORECASE)
    if crore_match:
        val = float(crore_match.group(1))
        return val * 10000000.0

    # Check for Lac / Lakh / Lacs
    lac_match = re.search(r"([\d\.]+)\s*(?:lac|lakh|lacs|lakhs)", s, re.IGNORECASE)
    if lac_match:
        val = float(lac_match.group(1))
        return val * 100000.0

    # Check for Thousand / K
    k_match = re.search(r"([\d\.]+)\s*(?:thousand|k)", s, re.IGNORECASE)
    if k_match:
        val = float(k_match.group(1))
        return val * 1000.0

    # Pure numeric
    num_match = re.search(r"^[\d\.]+$", s)
    if num_match:
        return float(num_match.group(0))

    # General digit extraction fallback
    digits = re.findall(r"[\d\.]+", s)
    if digits:
        return float(digits[0])

    return None


def normalize_area_to_marla(area_str: any) -> Optional[float]:
    """Converts any Pakistani land area representation into standard Marla (225 sq ft).
    
    Equivalences:
        1 Kanal = 20 Marla
        1 Marla = 1 Marla = 225 sq ft
        1 Sq. Yd = 9 sq ft = 9 / 225 = 0.04 Marla
        1 Sq. Ft = 1 / 225 Marla
    """
    if pd.isna(area_str):
        return None
    if isinstance(area_str, (int, float)):
        return float(area_str)

    s = str(area_str).strip().replace(",", "")

    # Kanal
    kanal_match = re.search(r"([\d\.]+)\s*(?:kanal|kanals)", s, re.IGNORECASE)
    if kanal_match:
        return float(kanal_match.group(1)) * 20.0

    # Marla
    marla_match = re.search(r"([\d\.]+)\s*(?:marla|marlas)", s, re.IGNORECASE)
    if marla_match:
        return float(marla_match.group(1))

    # Sq Yard / Yards / Gaz
    sqyd_match = re.search(r"([\d\.]+)\s*(?:sq\.?\s*yd\.?|sq\.?\s*yards?|guz|yards?)", s, re.IGNORECASE)
    if sqyd_match:
        sq_yds = float(sqyd_match.group(1))
        # 1 sq yd = 9 sq ft -> 9 / 225 = 0.04 marla
        return sq_yds * (9.0 / 225.0)

    # Sq Ft / Sq. Ft.
    sqft_match = re.search(r"([\d\.]+)\s*(?:sq\.?\s*ft\.?|sqft|feet)", s, re.IGNORECASE)
    if sqft_match:
        sq_ft = float(sqft_match.group(1))
        return sq_ft / 225.0

    # Fallback to direct number as marla
    digits = re.findall(r"[\d\.]+", s)
    if digits:
        return float(digits[0])

    return None


def normalize_covered_area_to_sqft(area_str: any) -> Optional[float]:
    """Converts covered area string to numeric Square Feet (Sq. Ft.)."""
    if pd.isna(area_str):
        return None
    if isinstance(area_str, (int, float)):
        return float(area_str)

    s = str(area_str).strip().replace(",", "")

    sqft_match = re.search(r"([\d\.]+)\s*(?:sq\.?\s*ft\.?|sqft|feet)?", s, re.IGNORECASE)
    if sqft_match:
        return float(sqft_match.group(1))

    digits = re.findall(r"[\d\.]+", s)
    if digits:
        return float(digits[0])

    return None


# ---------------------------------------------------------
# LOCATION STANDARDIZATION MAPPING
# ---------------------------------------------------------

LOCATION_CANONICAL_MAP: Dict[str, str] = {
    # Lahore
    r"dha\s*(?:phase\s*|ph\s*|-)?5\b": "DHA Phase 5",
    r"dha\s*(?:phase\s*|ph\s*|-)?v\b": "DHA Phase 5",
    r"dha\s*(?:phase\s*|ph\s*|-)?6\b": "DHA Phase 6",
    r"dha\s*(?:phase\s*|ph\s*|-)?vi\b": "DHA Phase 6",
    r"gulberg\s*(?:-|iii|3|\b)": "Gulberg III",
    r"bahria\s*(?:town\s*)?(?:sector\s*|sec\s*)?c\b": "Bahria Town Sector C",
    r"johar\s*town\s*(?:phase\s*|ph\s*|-)?2\b": "Johar Town Phase 2",
    r"model\s*town.*": "Model Town",
    r"wapda\s*town.*": "Wapda Town",
    r"lake\s*city.*": "Lake City",

    # Islamabad
    r"(?:sector\s*)?f[- ]?7\b": "Sector F-7",
    r"(?:sector\s*)?f[- ]?10\b": "Sector F-10",
    r"(?:sector\s*)?g[- ]?11\b": "Sector G-11",
    r"dha\s*(?:phase\s*|ph\s*|-)?2.*": "DHA Phase 2",
    r"bahria\s*(?:town\s*)?(?:phase\s*|ph\s*|-)?7\b": "Bahria Town Phase 7",
    r"(?:b[- ]?17|multi\s*gardens).*": "B-17 Multi Gardens",

    # Karachi
    r"clifton.*": "Clifton Block 5",
    r"dha\s*(?:phase\s*|ph\s*|-)?8\b": "DHA Phase 8",
    r"dha\s*(?:phase\s*|ph\s*|-)?viii\b": "DHA Phase 8",
    r"pechs.*": "PECHS Block 6",
    r"gulshan.*": "Gulshan-e-Iqbal Block 13",
    r"(?:bahria\s*town\s*karachi|btk).*": "Bahria Town Karachi",
    r"north\s*nazimabad.*|n\s*nazimabad.*": "North Nazimabad",

    # Rawalpindi
    r"bahria\s*(?:town\s*)?(?:phase\s*|ph\s*|-)?4\b": "Bahria Town Phase 4",
    r"dha\s*(?:phase\s*|ph\s*|-)?1.*": "DHA Phase 1",
    r"chaklala.*": "Chaklala Scheme 3",
    r"satellite\s*town.*": "Satellite Town",
    r"gulraiz.*": "Gulraiz Housing Scheme",

    # Faisalabad
    r"canal\s*(?:road|expressway|villas).*": "Canal Road",
    r"madina\s*town.*": "Madina Town",
    r"kohinoor.*": "Kohinoor City",
    r"wapda\s*city.*": "Wapda City",
}


def standardize_location(raw_loc: str) -> str:
    """Standardizes messy Pakistani location strings to canonical society names."""
    if not isinstance(raw_loc, str):
        return "Unknown"
    loc_clean = raw_loc.strip()

    for pattern, canonical in LOCATION_CANONICAL_MAP.items():
        if re.search(pattern, loc_clean, re.IGNORECASE):
            return canonical

    return loc_clean


# ---------------------------------------------------------
# CORE DATA CLEANING FUNCTIONS
# ---------------------------------------------------------

def clean_properties(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, any]]:
    """Cleans raw property listings data, handling missing values, duplicates,
    normalization, location standardization, and outlier removal.
    """
    df = df_raw.copy()
    report: Dict[str, any] = {"initial_rows": len(df)}

    # 1. Standardize location names
    df["area_society_clean"] = df["area_society"].apply(standardize_location)
    report["unique_raw_societies"] = df["area_society"].nunique()
    report["unique_clean_societies"] = df["area_society_clean"].nunique()

    # 2. Normalize Area Units to standard marla and covered area to sq ft
    df["plot_size_marla"] = df["plot_size_raw"].apply(normalize_area_to_marla)
    df["covered_area_sqft"] = df["covered_area_raw"].apply(normalize_covered_area_to_sqft)

    # 3. Normalize Price Strings to numeric PKR
    df["price_pkr_normalized"] = df["raw_price_str"].apply(normalize_price)
    # Prefer normalized price from raw string; fallback to original numeric price if missing
    df["price_pkr"] = df["price_pkr_normalized"].fillna(df["price_pkr"])

    # 4. Handle Missing Values with Domain Imputation
    missing_before = df.isnull().sum().to_dict()
    report["missing_values_before"] = missing_before

    # Impute missing covered_area_sqft:
    # Use median ratio of covered_area to (plot_size_marla * 225) grouped by property_type
    df["plot_area_sqft"] = df["plot_size_marla"] * 225.0
    coverage_ratio_by_type = (df["covered_area_sqft"] / df["plot_area_sqft"]).groupby(df["property_type"]).median()
    overall_median_ratio = 1.6  # typical double storey coverage ratio

    for ptype, ratio in coverage_ratio_by_type.items():
        mask = (df["property_type"] == ptype) & (df["covered_area_sqft"].isna())
        r = ratio if not pd.isna(ratio) else overall_median_ratio
        df.loc[mask, "covered_area_sqft"] = df.loc[mask, "plot_area_sqft"] * r

    # Impute bathrooms:
    # Group by property_type and bedrooms, take median
    median_baths = df.groupby(["property_type", "bedrooms"])["bathrooms"].transform("median")
    df["bathrooms"] = df["bathrooms"].fillna(median_baths).fillna(df["bedrooms"])

    # Impute floors:
    # Floors default: Flats/Portions = 1, Houses = 2, Farmhouse = 1
    type_floor_defaults = {"House": 2.0, "Flat": 1.0, "Upper Portion": 1.0, "Lower Portion": 1.0, "Farmhouse": 1.0, "Penthouse": 1.0}
    df["floors"] = df["floors"].fillna(df["property_type"].map(type_floor_defaults)).fillna(2.0)

    # Impute distance_to_hospital_km:
    # Use median distance within the same city and clean society
    median_hosp_dist = df.groupby(["city", "area_society_clean"])["distance_to_hospital_km"].transform("median")
    overall_hosp_median = df["distance_to_hospital_km"].median()
    df["distance_to_hospital_km"] = df["distance_to_hospital_km"].fillna(median_hosp_dist).fillna(overall_hosp_median)

    # 5. Remove Duplicates
    # Real estate listings are duplicated when same property (same city, clean society, property type, plot size, bedrooms, price) is posted multiple times
    dedup_cols = ["city", "area_society_clean", "property_type", "plot_size_marla", "bedrooms", "price_pkr"]
    initial_count = len(df)
    df = df.drop_duplicates(subset=dedup_cols, keep="first")
    report["duplicates_removed"] = initial_count - len(df)

    # 6. Outlier Detection and Removal (IQR + Domain bounds)
    # Target: price_per_marla
    df["price_per_marla"] = df["price_pkr"] / df["plot_size_marla"]
    
    # Absolute domain sanity filters for Pakistani real estate:
    # 1. Price per marla cannot be lower than 200,000 PKR (even in rural/periphery, 1 marla > 2 lac)
    # 2. Price per marla cannot exceed 25,000,000 PKR (even in F-7 or Clifton prime commercial)
    # 3. Absolute property price must be at least 800,000 PKR
    valid_domain_mask = (
        (df["price_per_marla"] >= 200000.0) &
        (df["price_per_marla"] <= 25000000.0) &
        (df["price_pkr"] >= 800000.0) &
        (df["price_pkr"] <= 1500000000.0)  # max 150 Crore
    )
    domain_outliers_count = (~valid_domain_mask).sum()

    df_filtered = df[valid_domain_mask].copy()

    # Statistical IQR filtering per (city, property_type)
    rows_before_iqr = len(df_filtered)
    keep_mask = pd.Series(True, index=df_filtered.index)
    for (city_val, ptype_val), group in df_filtered.groupby(["city", "property_type"]):
        if len(group) >= 15:
            q1 = group["price_per_marla"].quantile(0.10)
            q3 = group["price_per_marla"].quantile(0.90)
            iqr = q3 - q1
            lower_bound = q1 - 2.5 * iqr
            upper_bound = q3 + 2.5 * iqr
            outliers = (group["price_per_marla"] < lower_bound) | (group["price_per_marla"] > upper_bound)
            keep_mask.loc[group[outliers].index] = False

    df_cleaned = df_filtered[keep_mask].copy()
    iqr_outliers_count = rows_before_iqr - len(df_cleaned)

    report["domain_outliers_removed"] = int(domain_outliers_count)
    report["iqr_outliers_removed"] = int(iqr_outliers_count)
    report["final_cleaned_rows"] = len(df_cleaned)

    return df_cleaned.reset_index(drop=True), report


def clean_leads(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, any]]:
    """Cleans raw CRM leads data, handling missing values, duplicates,
    budget normalization, and target encoding preparation.
    """
    df = df_raw.copy()
    report: Dict[str, any] = {"initial_rows": len(df)}

    # 1. Normalize Budget string to numeric PKR
    df["budget_pkr_normalized"] = df["budget_raw"].apply(normalize_price)
    df["budget_pkr"] = df["budget_pkr_normalized"].fillna(df["budget_pkr"])

    # 2. Missing Value Imputation
    # response_time_hours: impute with median response time for each lead_source
    resp_median_by_source = df.groupby("lead_source")["response_time_hours"].transform("median")
    df["response_time_hours"] = df["response_time_hours"].fillna(resp_median_by_source).fillna(df["response_time_hours"].median())

    # objection_raised: impute missing with "None"
    df["objection_raised"] = df["objection_raised"].fillna("None")

    # 3. Deduplication
    # A lead inquiry is considered duplicate if same phone, city, and purpose submitted multiple times
    dedup_cols = ["phone", "preferred_city", "purpose", "property_type"]
    initial_count = len(df)
    df = df.drop_duplicates(subset=dedup_cols, keep="first")
    report["duplicates_removed"] = initial_count - len(df)

    # 4. Standardize Target Variable
    df["converted_binary"] = df["converted"].map({"Yes": 1, "No": 0, 1: 1, 0: 0}).fillna(0).astype(int)

    report["final_cleaned_rows"] = len(df)
    report["conversion_rate"] = float(df["converted_binary"].mean())

    return df.reset_index(drop=True), report


if __name__ == "__main__":
    RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
    PROC_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    print("--- Cleaning Properties Dataset ---")
    df_raw_props = pd.read_csv(RAW_DIR / "raw_properties.csv")
    df_clean_props, props_report = clean_properties(df_raw_props)
    df_clean_props.to_csv(PROC_DIR / "cleaned_properties.csv", index=False)
    print("Properties Cleaning Report:", props_report)

    print("\n--- Cleaning Leads Dataset ---")
    df_raw_leads = pd.read_csv(RAW_DIR / "raw_leads.csv")
    df_clean_leads, leads_report = clean_leads(df_raw_leads)
    df_clean_leads.to_csv(PROC_DIR / "cleaned_leads.csv", index=False)
    print("Leads Cleaning Report:", leads_report)
