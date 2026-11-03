"""City Care Clinics - Deterministic Prescription Safety Engine.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Zero-hallucination pharmacological safety verification engine.
Executes rule-based audits across 5 critical vectors:
1. Allergy conflicts (e.g., Penicillin vs. Augmentin)
2. Drug-drug interactions (e.g., Warfarin + Aspirin)
3. Maximum 24-hour daily dose ceilings
4. Duplicate therapies (same generic or therapeutic subclass)
5. Special population contraindications (Pregnancy, Pediatric, Elderly / Beers Criteria)
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Reconfigure stdout for UTF-8 compatibility on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mcp_servers.drug_database_server import (
    DETERMINISTIC_INTERACTIONS,
    PAKISTANI_DRUG_DATABASE,
    _normalize_drug_name,
)


class ProposedMedication(BaseModel):
    """Single medication order from doctor or patient inquiry."""
    medication_name: str
    dose_mg: float
    frequency: str = Field(default="TDS", description="OD=1, BD=2, TDS=3, QDS=4")
    route: str = Field(default="Oral")


class PrescriptionSafetyReport(BaseModel):
    """Complete pharmacological safety audit report."""
    overall_status: str = Field(default="SAFE", description="SAFE, WARNING_MODERATE, CRITICAL_DANGER")
    is_safe: bool = Field(default=True)
    allergy_clashes: List[str] = Field(default_factory=list)
    drug_interactions: List[Dict[str, Any]] = Field(default_factory=list)
    dose_violations: List[str] = Field(default_factory=list)
    duplicate_therapies: List[str] = Field(default_factory=list)
    special_population_alerts: List[str] = Field(default_factory=list)
    physician_recommendations: List[str] = Field(default_factory=list)
    urdulish_patient_summary: str = Field(default="")


class PrescriptionSafetyEngine:
    """Production Deterministic Pharmacological Audit Engine."""

    def evaluate_prescription(
        self,
        proposed_meds: List[ProposedMedication],
        patient_allergies: List[str],
        active_medications: List[str],
        patient_age: int = 35,
        patient_weight_kg: float = 70.0,
        is_pregnant: bool = False
    ) -> PrescriptionSafetyReport:
        """Executes comprehensive rule-based audit on proposed prescription."""
        allergy_clashes: List[str] = []
        drug_interactions: List[Dict[str, Any]] = []
        dose_violations: List[str] = []
        duplicate_therapies: List[str] = []
        special_population_alerts: List[str] = []
        physician_recommendations: List[str] = []

        overall_severity = "SAFE"

        # Combine proposed meds with existing active meds for interaction checks
        all_drug_names = [m.medication_name for m in proposed_meds] + active_medications
        normalized_keys = []
        for d in all_drug_names:
            k = _normalize_drug_name(d)
            if k:
                normalized_keys.append(k)

        # -------------------------------------------------------------
        # 1. Allergy Conflict Checks
        # -------------------------------------------------------------
        for med in proposed_meds:
            key = _normalize_drug_name(med.medication_name)
            if not key:
                continue

            drug_data = PAKISTANI_DRUG_DATABASE.get(key, {})
            allergy_group = drug_data.get("allergy_group", key)

            for alg in patient_allergies:
                alg_lower = alg.strip().lower()
                if "none" in alg_lower:
                    continue

                if (
                    key in alg_lower or
                    allergy_group in alg_lower or
                    drug_data.get("generic", "").lower() in alg_lower or
                    ("penicillin" in alg_lower and allergy_group == "penicillin") or
                    ("sulfa" in alg_lower and (allergy_group == "sulfa" or "sulfa" in drug_data.get("generic", "").lower())) or
                    ("nsaid" in alg_lower and "nsaid" in drug_data.get("class", "").lower())
                ):
                    clash_msg = (
                        f"CRITICAL ALLERGY CONFLICT: Patient is allergic to '{alg}'. "
                        f"Prescribing '{med.medication_name}' ({drug_data.get('generic')}) risks severe anaphylaxis."
                    )
                    allergy_clashes.append(clash_msg)
                    overall_severity = "CRITICAL_DANGER"
                    physician_recommendations.append(f"Discontinue '{med.medication_name}'; switch to non-{alg} alternative.")

        # -------------------------------------------------------------
        # 2. Drug-Drug Interaction (DDI) Checks
        # -------------------------------------------------------------
        seen_pairs = set()
        for i in range(len(normalized_keys)):
            for j in range(i + 1, len(normalized_keys)):
                d1, d2 = normalized_keys[i], normalized_keys[j]
                pair_key = tuple(sorted([d1, d2]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                for item in DETERMINISTIC_INTERACTIONS:
                    if item["pair"] == set(pair_key):
                        drug_interactions.append(item)
                        if item["severity"] == "CRITICAL_DANGER":
                            overall_severity = "CRITICAL_DANGER"
                        elif item["severity"] == "WARNING_MODERATE" and overall_severity != "CRITICAL_DANGER":
                            overall_severity = "WARNING_MODERATE"
                        physician_recommendations.append(f"DDI Alert ({d1} + {d2}): {item['management']}")

        # -------------------------------------------------------------
        # 3. Maximum 24-Hour Dose Checks
        # -------------------------------------------------------------
        freq_multipliers = {"OD": 1, "ON": 1, "BD": 2, "TDS": 3, "QDS": 4, "PRN": 2, "SOS": 1}
        for med in proposed_meds:
            key = _normalize_drug_name(med.medication_name)
            if not key:
                continue

            drug_data = PAKISTANI_DRUG_DATABASE.get(key, {})
            mult = freq_multipliers.get(med.frequency.upper(), 3)
            daily_dose = med.dose_mg * mult

            # Pediatric limits
            if patient_age < 14:
                ped_max_per_kg = drug_data.get("max_pediatric_mg_kg_day", 0.0)
                if ped_max_per_kg <= 0.0:
                    special_population_alerts.append(f"PEDIATRIC CONTRAINDICATION: '{drug_data.get('generic')}' is contraindicated in children under 14.")
                    overall_severity = "CRITICAL_DANGER"
                else:
                    max_allowed = ped_max_per_kg * patient_weight_kg
                    if daily_dose > max_allowed:
                        dose_violations.append(
                            f"Pediatric Overdose: '{med.medication_name}' prescribed at {daily_dose}mg/day exceeds safe max of {max_allowed}mg/day ({ped_max_per_kg}mg/kg)."
                        )
                        overall_severity = "CRITICAL_DANGER"
            else:
                # Adult limits
                adult_max = drug_data.get("max_daily_dose_mg_adult", 4000.0)
                if daily_dose > adult_max:
                    dose_violations.append(
                        f"Adult Overdose: '{med.medication_name}' prescribed at {daily_dose}mg/day exceeds absolute ceiling of {adult_max}mg/day."
                    )
                    overall_severity = "CRITICAL_DANGER"
                    physician_recommendations.append(f"Reduce dose of '{med.medication_name}' to <= {adult_max}mg/day.")

        # -------------------------------------------------------------
        # 4. Duplicate Therapy Checks
        # -------------------------------------------------------------
        generic_counts: Dict[str, List[str]] = {}
        class_counts: Dict[str, List[str]] = {}
        for med in proposed_meds:
            key = _normalize_drug_name(med.medication_name)
            if not key:
                continue
            drug_data = PAKISTANI_DRUG_DATABASE[key]
            gen = drug_data["generic"]
            cls = drug_data["class"]

            generic_counts.setdefault(gen, []).append(med.medication_name)
            class_counts.setdefault(cls, []).append(med.medication_name)

        for gen, items in generic_counts.items():
            if len(items) > 1:
                duplicate_therapies.append(f"Duplicate Generic Therapy: Multiple products contain '{gen}' ({', '.join(items)}).")
                overall_severity = "CRITICAL_DANGER" if overall_severity == "CRITICAL_DANGER" else "WARNING_MODERATE"

        for cls, items in class_counts.items():
            if len(items) > 1 and "Analgesic" not in cls:
                duplicate_therapies.append(f"Duplicate Therapeutic Class: Multiple drugs belong to '{cls}' ({', '.join(items)}).")
                if overall_severity == "SAFE":
                    overall_severity = "WARNING_MODERATE"

        # -------------------------------------------------------------
        # 5. Special Population Checks (Pregnancy, Elderly)
        # -------------------------------------------------------------
        for med in proposed_meds:
            key = _normalize_drug_name(med.medication_name)
            if not key:
                continue
            drug_data = PAKISTANI_DRUG_DATABASE[key]

            # Pregnancy
            if is_pregnant:
                preg_cat = drug_data.get("pregnancy_category", "C")
                if "X" in preg_cat or "D" in preg_cat:
                    special_population_alerts.append(
                        f"PREGNANCY CONTRAINDICATION: '{drug_data['generic']}' is Category {preg_cat}. High risk of fetal teratogenicity or toxicity."
                    )
                    overall_severity = "CRITICAL_DANGER"

            # Elderly (> 65 years - Beers Criteria)
            if patient_age >= 65:
                elderly_caution = drug_data.get("elderly_caution")
                if elderly_caution:
                    special_population_alerts.append(f"Geriatric Caution (Age {patient_age}): '{drug_data['generic']}' — {elderly_caution}")
                    if overall_severity == "SAFE":
                        overall_severity = "WARNING_MODERATE"

        # Synthesize UrduLish Patient Summary
        urdulish_summary = self._synthesize_urdulish_summary(
            overall_severity,
            allergy_clashes,
            drug_interactions,
            dose_violations,
            special_population_alerts
        )

        return PrescriptionSafetyReport(
            overall_status=overall_severity,
            is_safe=(overall_severity == "SAFE"),
            allergy_clashes=allergy_clashes,
            drug_interactions=drug_interactions,
            dose_violations=dose_violations,
            duplicate_therapies=duplicate_therapies,
            special_population_alerts=special_population_alerts,
            physician_recommendations=physician_recommendations,
            urdulish_patient_summary=urdulish_summary
        )

    def _synthesize_urdulish_summary(
        self,
        severity: str,
        allergies: List[str],
        interactions: List[Dict[str, Any]],
        doses: List[str],
        specials: List[str]
    ) -> str:
        """Translates rule-based findings into compassionate, clear UrduLish."""
        if severity == "SAFE":
            return (
                "Aap ki tajweez karda medicines hamare pharmacy safety system ke mutabiq mehfooz hain. "
                "Koi allergy clash, muzir interaction, ya dose ki khilaf-warzi nahi mili."
            )

        lines = ["⚠️ DAWAI KI EHRTIYAT / PHARMACY SAFETY ALERT:"]
        if allergies:
            lines.append("• ALLERGY KHATRA: Aap ki allergy record ke sath dawai clash kar rahi hai.")
        if interactions:
            lines.append("• DRUG INTERACTION: Do mukhtalif medicines aapas mein mil kar nuqsan pohancha sakti hain.")
        if doses:
            lines.append("• DOSE ALERT: Dawai ki miqdaar (dose) safe limit se ziada record hui hai.")
        if specials:
            lines.append("• KHAS EHRTIYAT: Hamal (pregnancy) ya umar ke lehaaz se dawai mein ehrtiyat darkaar hai.")

        lines.append(
            "\nYeh prescription doctor ke review ke liye hold kar di gayi hai. "
            "Doctor sahab ki tasdeeq ke baghair yeh dawai hargiz shuru na karein."
        )
        return "\n".join(lines)


if __name__ == "__main__":
    engine = PrescriptionSafetyEngine()

    # Test Case: Clashing Prescription (Penicillin Allergy + Warfarin + Disprin + Paracetamol 6000mg)
    test_meds = [
        ProposedMedication(medication_name="Augmentin 625mg", dose_mg=625.0, frequency="BD"),
        ProposedMedication(medication_name="Disprin 300mg", dose_mg=300.0, frequency="BD"),
        ProposedMedication(medication_name="Panadol 500mg", dose_mg=2000.0, frequency="TDS")  # 6000mg/day!
    ]

    report = engine.evaluate_prescription(
        proposed_meds=test_meds,
        patient_allergies=["Penicillin Allergy"],
        active_medications=["Warfarin 5mg"],
        patient_age=68,
        patient_weight_kg=72.0,
        is_pregnant=False
    )

    print("=" * 70)
    print("PRESCRIPTION SAFETY ENGINE AUDIT RESULT")
    print("=" * 70)
    print(f"Overall Safety Status:     {report.overall_status}")
    print(f"Is Prescribable / Safe:    {report.is_safe}")
    print(f"Allergy Clashes Detected:  {len(report.allergy_clashes)}")
    print(f"Drug Interactions Flagged: {len(report.drug_interactions)}")
    print(f"Dose Limit Violations:     {len(report.dose_violations)}")
    print(f"Geriatric/Special Alerts:  {len(report.special_population_alerts)}")
    print("=" * 70)
    print("\n[PATIENT URDULISH SUMMARY]:")
    print(report.urdulish_patient_summary)
