"""City Care Clinics - Drug Database & Pharmacological Safety MCP Server.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Exposes verified drug database, deterministic drug-drug interactions,
allergy contraindications, and dose limit verifications over Model Context Protocol (FastMCP).
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Comprehensive Pakistani Outpatient Formulary (Brand + Generic + Pharmacological Rules)
PAKISTANI_DRUG_DATABASE: Dict[str, Dict[str, Any]] = {
    "paracetamol": {
        "generic": "Paracetamol",
        "brands": ["Panadol", "Calpol", "Disprol", "Febrol"],
        "class": "Analgesic / Antipyretic",
        "max_daily_dose_mg_adult": 4000.0,
        "max_pediatric_mg_kg_day": 60.0,
        "contraindications": ["Severe hepatic impairment", "Acute liver failure"],
        "pregnancy_category": "B (Safe in standard therapeutic doses)",
        "elderly_caution": "Max 3000mg/day recommended in frail elderly"
    },
    "aspirin": {
        "generic": "Aspirin",
        "brands": ["Disprin", "Ascard", "Loprin"],
        "class": "NSAID / Antiplatelet",
        "max_daily_dose_mg_adult": 3000.0,
        "max_pediatric_mg_kg_day": 0.0,  # Absolute contraindication in children (Reye's syndrome)
        "contraindications": ["Active peptic ulcer", "Bleeding disorders", "Dengue fever", "Children under 16 (Reye's syndrome)"],
        "pregnancy_category": "D (Third trimester contraindication)",
        "elderly_caution": "High risk of gastrointestinal hemorrhage"
    },
    "ibuprofen": {
        "generic": "Ibuprofen",
        "brands": ["Brufen", "Profen", "Advil"],
        "class": "NSAID",
        "max_daily_dose_mg_adult": 2400.0,
        "max_pediatric_mg_kg_day": 40.0,
        "contraindications": ["Active peptic ulcer", "Severe renal impairment", "Third trimester pregnancy", "Dengue fever"],
        "pregnancy_category": "D (Third trimester contraindication)",
        "elderly_caution": "Increased risk of renal failure and GI bleeding"
    },
    "amoxicillin": {
        "generic": "Amoxicillin",
        "brands": ["Amoxil", "Moxatag"],
        "class": "Aminopenicillin Antibiotic",
        "allergy_group": "penicillin",
        "max_daily_dose_mg_adult": 3000.0,
        "max_pediatric_mg_kg_day": 90.0,
        "contraindications": ["Documented Penicillin Allergy", "Infectious mononucleosis"],
        "pregnancy_category": "B",
        "elderly_caution": "Dose adjustment required in severe renal impairment"
    },
    "amoxicillin / clavulanate": {
        "generic": "Amoxicillin / Clavulanate",
        "brands": ["Augmentin", "Curam", "Klavox"],
        "class": "Aminopenicillin + Beta-Lactamase Inhibitor",
        "allergy_group": "penicillin",
        "max_daily_dose_mg_adult": 2000.0,
        "max_pediatric_mg_kg_day": 90.0,
        "contraindications": ["Documented Penicillin Allergy", "History of amoxicillin-clavulanate associated jaundice"],
        "pregnancy_category": "B",
        "elderly_caution": "Higher incidence of cholestatic jaundice in elderly males"
    },
    "ciprofloxacin": {
        "generic": "Ciprofloxacin",
        "brands": ["Ciproxin", "Novidat", "Mercip"],
        "class": "Fluoroquinolone Antibiotic",
        "allergy_group": "quinolone",
        "max_daily_dose_mg_adult": 1500.0,
        "max_pediatric_mg_kg_day": 0.0,  # Generally avoided in children due to arthropathy
        "contraindications": ["Myasthenia gravis", "QT prolongation", "Concurrent tizanidine"],
        "pregnancy_category": "C (Avoid in pregnancy)",
        "elderly_caution": "High risk of tendonitis, tendon rupture, and CNS toxicities"
    },
    "warfarin": {
        "generic": "Warfarin",
        "brands": ["Coumadin", "Warf"],
        "class": "Vitamin K Antagonist Anticoagulant",
        "max_daily_dose_mg_adult": 10.0,
        "max_pediatric_mg_kg_day": 0.2,
        "contraindications": ["Active major bleeding", "Pregnancy (Teratogenic)", "Uncontrolled malignant hypertension"],
        "pregnancy_category": "X (Strictly Teratogenic)",
        "elderly_caution": "Extreme fall/bleeding risk; mandatory INR monitoring"
    },
    "metformin": {
        "generic": "Metformin",
        "brands": ["Glucophage", "Neodipar"],
        "class": "Biguanide Antidiabetic",
        "max_daily_dose_mg_adult": 2550.0,
        "max_pediatric_mg_kg_day": 0.0,
        "contraindications": ["Severe renal failure (eGFR < 30 mL/min)", "Acute metabolic acidosis", "Severe hypoxia"],
        "pregnancy_category": "B",
        "elderly_caution": "Monitor renal function regularly for lactic acidosis risk"
    },
    "lisinopril": {
        "generic": "Lisinopril",
        "brands": ["Zestril", "Prinivil"],
        "class": "ACE Inhibitor",
        "allergy_group": "ace_inhibitor",
        "max_daily_dose_mg_adult": 40.0,
        "max_pediatric_mg_kg_day": 0.6,
        "contraindications": ["Pregnancy", "History of ACE-inhibitor angioedema", "Bilateral renal artery stenosis"],
        "pregnancy_category": "D (Strictly contraindicated in 2nd and 3rd trimesters)",
        "elderly_caution": "Risk of severe hypotension and hyperkalemia"
    },
    "atorvastatin": {
        "generic": "Atorvastatin",
        "brands": ["Lipiget", "Lipitor", "Atova"],
        "class": "HMG-CoA Reductase Inhibitor (Statin)",
        "max_daily_dose_mg_adult": 80.0,
        "max_pediatric_mg_kg_day": 0.0,
        "contraindications": ["Active liver disease", "Pregnancy & Lactation"],
        "pregnancy_category": "X (Contraindicated in pregnancy)",
        "elderly_caution": "Monitor for myopathy and rhabdomyolysis"
    },
    "omeprazole": {
        "generic": "Omeprazole",
        "brands": ["Risek", "Omega", "Prilosec"],
        "class": "Proton Pump Inhibitor (PPI)",
        "max_daily_dose_mg_adult": 40.0,
        "max_pediatric_mg_kg_day": 1.0,
        "contraindications": ["Known hypersensitivity to PPIs"],
        "pregnancy_category": "C",
        "elderly_caution": "Long-term use associated with bone fractures and hypomagnesemia"
    },
    "esomeprazole": {
        "generic": "Esomeprazole",
        "brands": ["Nexum", "Esita"],
        "class": "Proton Pump Inhibitor (PPI)",
        "max_daily_dose_mg_adult": 40.0,
        "max_pediatric_mg_kg_day": 1.0,
        "contraindications": ["Known hypersensitivity to PPIs"],
        "pregnancy_category": "C",
        "elderly_caution": "Long-term use associated with bone fractures"
    },
    "co-trimoxazole": {
        "generic": "Sulfamethoxazole / Trimethoprim",
        "brands": ["Septran", "Septran DS", "Bactrim"],
        "class": "Sulfonamide Antibiotic",
        "allergy_group": "sulfa",
        "max_daily_dose_mg_adult": 1920.0,
        "max_pediatric_mg_kg_day": 40.0,
        "contraindications": ["Documented Sulfa Allergy", "Severe hepatic damage", "G6PD deficiency", "Late pregnancy"],
        "pregnancy_category": "D",
        "elderly_caution": "Risk of severe hyperkalemia and bone marrow suppression"
    }
}

# Deterministic Drug-Drug Interaction Matrix
DETERMINISTIC_INTERACTIONS: List[Dict[str, Any]] = [
    {
        "pair": {"warfarin", "aspirin"},
        "severity": "CRITICAL_DANGER",
        "mechanism": "Concurrent antiplatelet and anticoagulant therapy causes profound synergism in bleeding pathways.",
        "clinical_effect": "Extremely high risk of fatal major gastrointestinal or intracranial hemorrhage.",
        "management": "Avoid combination unless strictly indicated under specialist cardiologist supervision with close INR monitoring."
    },
    {
        "pair": {"warfarin", "ibuprofen"},
        "severity": "CRITICAL_DANGER",
        "mechanism": "NSAIDs inhibit platelet function and induce gastrointestinal mucosal damage while warfarin inhibits clotting factor synthesis.",
        "clinical_effect": "Severe gastrointestinal bleeding and ulceration.",
        "management": "Contraindicated. Use Paracetamol for pain relief in patients taking Warfarin."
    },
    {
        "pair": {"ciprofloxacin", "aspirin"},
        "severity": "WARNING_MODERATE",
        "mechanism": "Fluoroquinolones combined with high-dose NSAIDs can enhance central nervous system stimulation.",
        "clinical_effect": "Increased risk of tremors, CNS excitation, and convulsions.",
        "management": "Monitor patient for neurological signs or select an alternative analgesic."
    },
    {
        "pair": {"lisinopril", "ibuprofen"},
        "severity": "WARNING_MODERATE",
        "mechanism": "NSAIDs inhibit renal prostaglandins, attenuating the antihypertensive effect of ACE inhibitors and worsening renal hemodynamics.",
        "clinical_effect": "Loss of blood pressure control and acute kidney injury (triple whammy risk).",
        "management": "Avoid chronic NSAIDs; monitor renal function and potassium levels."
    },
    {
        "pair": {"omeprazole", "esomeprazole"},
        "severity": "DUPLICATE_THERAPY",
        "mechanism": "Simultaneous prescription of two proton pump inhibitors.",
        "clinical_effect": "Therapeutic duplication with no clinical benefit and increased risk of hypomagnesemia.",
        "management": "Discontinue one agent."
    }
]

mcp_drug_database = FastMCP(
    name="pharmacy-safety-server",
    instructions="Deterministic pharmacological safety verification engine for City Care Clinics. Checks allergies, DDIs, dose limits, and contraindications."
)


def _normalize_drug_name(name: str) -> Optional[str]:
    """Resolves brand names or generic variations to normalized drug database key."""
    clean = name.strip().lower()
    for key, data in PAKISTANI_DRUG_DATABASE.items():
        if key in clean or data["generic"].lower() in clean:
            return key
        for b in data["brands"]:
            if b.lower() in clean:
                return key
    return None


@mcp_drug_database.tool()
def lookup_drug(drug_name: str) -> Dict[str, Any]:
    """Looks up drug information, brand names, generic class, max doses, and contraindications.

    Args:
        drug_name: Brand name (e.g. Panadol, Augmentin, Risek) or generic name (e.g. Paracetamol).
    """
    key = _normalize_drug_name(drug_name)
    if not key:
        return {"status": "NOT_FOUND", "message": f"Drug '{drug_name}' not found in clinic formulary."}

    data = PAKISTANI_DRUG_DATABASE[key]
    return {
        "status": "FOUND",
        "query": drug_name,
        "generic_name": data["generic"],
        "class": data["class"],
        "common_brands_pk": data["brands"],
        "max_daily_dose_mg_adult": data["max_daily_dose_mg_adult"],
        "max_pediatric_mg_kg_day": data["max_pediatric_mg_kg_day"],
        "contraindications": data["contraindications"],
        "pregnancy_category": data["pregnancy_category"],
        "elderly_caution": data["elderly_caution"]
    }


@mcp_drug_database.tool()
def check_drug_interaction(drug_a: str, drug_b: str) -> Dict[str, Any]:
    """Deterministically checks for adverse drug-drug interactions between two medications.

    Args:
        drug_a: First medication name.
        drug_b: Second medication name.
    """
    key_a = _normalize_drug_name(drug_a)
    key_b = _normalize_drug_name(drug_b)

    if not key_a or not key_b:
        return {
            "status": "UNKNOWN_DRUG",
            "message": f"One or both drugs could not be normalized ({drug_a}, {drug_b})."
        }

    pair_set = {key_a, key_b}
    for item in DETERMINISTIC_INTERACTIONS:
        if item["pair"] == pair_set:
            return {
                "status": "INTERACTION_DETECTED",
                "severity": item["severity"],
                "drug_a": key_a,
                "drug_b": key_b,
                "mechanism": item["mechanism"],
                "clinical_effect": item["clinical_effect"],
                "management": item["management"]
            }

    return {
        "status": "SAFE",
        "message": f"No documented severe adverse interaction between {drug_a} and {drug_b} in clinic database."
    }


@mcp_drug_database.tool()
def check_allergy_conflict(drug_name: str, patient_allergies: List[str]) -> Dict[str, Any]:
    """Cross-references a proposed drug against known patient allergies.

    Args:
        drug_name: Medication being prescribed.
        patient_allergies: List of patient's recorded drug allergies.
    """
    key = _normalize_drug_name(drug_name)
    if not key:
        return {"status": "UNKNOWN_DRUG", "message": f"Drug '{drug_name}' not in database."}

    drug_data = PAKISTANI_DRUG_DATABASE[key]
    allergy_group = drug_data.get("allergy_group", key)

    for alg in patient_allergies:
        alg_clean = alg.strip().lower()
        if "none" in alg_clean:
            continue

        # Check direct name match or chemical class match
        if (
            key in alg_clean or
            allergy_group in alg_clean or
            drug_data["generic"].lower() in alg_clean or
            ("penicillin" in alg_clean and allergy_group == "penicillin") or
            ("nsaid" in alg_clean and "nsaid" in drug_data["class"].lower())
        ):
            return {
                "status": "ALLERGY_CLASH_DETECTED",
                "severity": "CRITICAL_DANGER",
                "drug": drug_name,
                "generic": drug_data["generic"],
                "patient_allergy": alg,
                "warning": (
                    f"CRITICAL CONTRAINDICATION: Patient has documented allergy to '{alg}'. "
                    f"Prescribing '{drug_name}' ({drug_data['generic']}) risks immediate severe anaphylaxis."
                )
            }

    return {"status": "SAFE", "message": f"No allergy contraindications detected for '{drug_name}'."}


@mcp_drug_database.tool()
def verify_daily_dose(
    drug_name: str,
    dose_mg_per_intake: float,
    frequency: str,
    patient_age: int = 30,
    patient_weight_kg: float = 70.0
) -> Dict[str, Any]:
    """Calculates total 24-hour dose and flags overdoses against adult and pediatric ceilings.

    Args:
        drug_name: Medication name.
        dose_mg_per_intake: Milligrams per single intake.
        frequency: Dosing frequency (OD = 1x, BD = 2x, TDS = 3x, QDS = 4x).
        patient_age: Age in years.
        patient_weight_kg: Weight in kilograms (critical for pediatric doses).
    """
    key = _normalize_drug_name(drug_name)
    if not key:
        return {"status": "UNKNOWN_DRUG", "message": f"Drug '{drug_name}' not in database."}

    data = PAKISTANI_DRUG_DATABASE[key]

    freq_multipliers = {"OD": 1, "ON": 1, "BD": 2, "TDS": 3, "QDS": 4, "PRN": 2, "SOS": 1}
    mult = freq_multipliers.get(frequency.upper(), 3)
    total_daily_dose = dose_mg_per_intake * mult

    # Pediatric Evaluation (< 14 years)
    if patient_age < 14:
        ped_max_per_kg = data.get("max_pediatric_mg_kg_day", 0.0)
        if ped_max_per_kg <= 0.0:
            return {
                "status": "PEDIATRIC_CONTRAINDICATION",
                "severity": "CRITICAL_DANGER",
                "message": f"'{data['generic']}' is CONTRAINDICATED in pediatric patients (Age {patient_age})."
            }

        max_ped_daily_allowed = ped_max_per_kg * patient_weight_kg
        if total_daily_dose > max_ped_daily_allowed:
            return {
                "status": "DOSE_EXCEEDED",
                "severity": "CRITICAL_DANGER",
                "calculated_daily_dose_mg": total_daily_dose,
                "max_allowed_mg": max_ped_daily_allowed,
                "message": (
                    f"Pediatric daily dose limit exceeded! Prescribed: {total_daily_dose}mg/day. "
                    f"Max safe limit ({ped_max_per_kg}mg/kg for {patient_weight_kg}kg): {max_ped_daily_allowed}mg/day."
                )
            }

    # Adult Evaluation
    adult_max = data.get("max_daily_dose_mg_adult", 4000.0)
    if total_daily_dose > adult_max:
        return {
            "status": "DOSE_EXCEEDED",
            "severity": "CRITICAL_DANGER",
            "calculated_daily_dose_mg": total_daily_dose,
            "max_allowed_mg": adult_max,
            "message": (
                f"Maximum adult daily dose exceeded! Prescribed: {total_daily_dose}mg/day. "
                f"Absolute safe ceiling is {adult_max}mg/day."
            )
        }

    return {
        "status": "SAFE",
        "calculated_daily_dose_mg": total_daily_dose,
        "max_allowed_mg": adult_max if patient_age >= 14 else (data.get("max_pediatric_mg_kg_day", 0.0) * patient_weight_kg),
        "message": f"Total daily dose of {total_daily_dose}mg is within safe pharmacological limits."
    }


if __name__ == "__main__":
    mcp_drug_database.run()
