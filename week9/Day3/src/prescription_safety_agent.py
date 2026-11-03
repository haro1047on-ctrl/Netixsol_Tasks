"""City Care Clinics - Prescription Safety Specialist Agent.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Acts as the final pharmacological defense gate before prescription dispensing.
Takes a doctor's draft prescription orders and executes zero-hallucination audits:
1. Patient Drug Allergy Conflicts (e.g. Penicillin vs Amoxicillin/Augmentin)
2. Drug-Drug Interactions (e.g. Warfarin + Aspirin, ACEi + Potassium-sparing)
3. Maximum 24-Hour Dose Ceilings (e.g. Paracetamol > 4,000 mg/day)
4. Duplicate Therapeutic Redundancies (e.g. Panadol + Calpol)
5. Special Populations (Pregnancy teratogenicity, Pediatric contraindications)

Example Doctor Warning:
"⚠️ Patient ko Penicillin se allergy hai — Amoxicillin contraindicated hai."
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Reconfigure stdout for UTF-8 compatibility
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
WEEK9_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
for p in [SRC_DIR, DAY2_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from mcp_servers.patient_records_server import (
    get_patient_allergies,
    get_patient_medications,
    get_patient_profile,
)
from prescription_safety_engine import (
    PrescriptionSafetyEngine,
    PrescriptionSafetyReport,
    ProposedMedication,
)


class DoctorPrescriptionReview(BaseModel):
    """Safety evaluation response for attending physician."""
    patient_id: str
    patient_name: str
    overall_status: str = Field(description="SAFE, WARNING_MODERATE, or CRITICAL_DANGER")
    is_safe_to_dispense: bool
    doctor_alert_warnings: List[str] = Field(default_factory=list)
    actionable_alternatives: List[str] = Field(default_factory=list)
    patient_urdulish_explanation: str = ""
    underlying_report: PrescriptionSafetyReport


class PrescriptionSafetyAgent:
    """Production Prescription Safety Specialist Agent."""

    def __init__(self, engine: Optional[PrescriptionSafetyEngine] = None):
        self.engine = engine or PrescriptionSafetyEngine()

    def audit_draft_prescription(
        self,
        patient_id: str,
        proposed_meds: List[ProposedMedication],
        is_pregnant_override: Optional[bool] = None,
        patient_weight_kg: float = 70.0
    ) -> DoctorPrescriptionReview:
        """Executes full pharmacological safety verification against patient EHR."""
        profile = get_patient_profile(patient_id)
        patient_name = profile.get("full_name", "Valued Patient")
        patient_age = profile.get("age", 35)

        # Retrieve active allergies and medications from EHR
        allergies_data = get_patient_allergies(patient_id)
        patient_allergies = [a.get("substance", "") for a in allergies_data]

        meds_data = get_patient_medications(patient_id)
        active_medications = [m.get("medication_name", "") for m in meds_data]

        # Determine pregnancy status (override or female adult check)
        is_pregnant = is_pregnant_override if is_pregnant_override is not None else False

        # Run Day 2 Deterministic Safety Engine
        safety_report = self.engine.evaluate_prescription(
            proposed_meds=proposed_meds,
            patient_allergies=patient_allergies,
            active_medications=active_medications,
            patient_age=patient_age,
            patient_weight_kg=patient_weight_kg,
            is_pregnant=is_pregnant
        )

        doctor_alerts = []
        actionable_alternatives = []

        # 1. Format Allergy Warnings for Physician
        for clash in safety_report.allergy_clashes:
            # Example format: "⚠️ Patient ko Penicillin se allergy hai — Amoxicillin contraindicated hai."
            doctor_alerts.append(f"⚠️ {clash}")

        # 2. Format Drug-Drug Interaction Warnings
        for ddi in safety_report.drug_interactions:
            sev = ddi.get("severity", "MODERATE")
            pair = list(ddi.get("pair", []))
            pair_str = " + ".join(pair).title() if pair else "Drug Combination"
            clinical_effect = ddi.get("clinical_effect", "Adverse pharmacological interaction")
            mgmt = ddi.get("management", "Review combination")
            doctor_alerts.append(f"⚠️ [{sev} DDI] Interaction ({pair_str}): {clinical_effect}. Action: {mgmt}")

        # 3. Format Overdose Warnings
        for dose in safety_report.dose_violations:
            doctor_alerts.append(f"⚠️ [DOSE CEILING]: {dose}")

        # 4. Format Duplicate Therapies
        for dup in safety_report.duplicate_therapies:
            doctor_alerts.append(f"⚠️ [DUPLICATE THERAPY]: {dup}")

        # 5. Special Population Alerts
        for pop in safety_report.special_population_alerts:
            doctor_alerts.append(f"⚠️ [SPECIAL POPULATION]: {pop}")

        # Physician Recommendations
        for rec in safety_report.physician_recommendations:
            actionable_alternatives.append(rec)

        # UrduLish Patient Explanation
        if safety_report.is_safe:
            urdulish_patient = (
                f"{patient_name} Janab ke liye yeh nuskhah mehfooz hai. "
                f"Kisi qisam ka allergy clash ya muzir interaction nahi paya gaya."
            )
        else:
            urdulish_patient = (
                f"Khabardaar: {patient_name} Janab ki dawaiyon mein tibbi khatraat samne aye hain. "
                f"Doctor sahib is nuskhay ka jaiza le rahe hain."
            )

        return DoctorPrescriptionReview(
            patient_id=patient_id,
            patient_name=patient_name,
            overall_status=safety_report.overall_status,
            is_safe_to_dispense=safety_report.is_safe,
            doctor_alert_warnings=doctor_alerts,
            actionable_alternatives=actionable_alternatives,
            patient_urdulish_explanation=urdulish_patient,
            underlying_report=safety_report
        )
