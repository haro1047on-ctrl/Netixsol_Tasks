"""City Care Clinics - Patient Records Specialist Agent.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Answers patient and physician clinical queries directly from the FHIR EHR database:
- Demographic profile and emergency contacts
- Active drug allergies & environmental sensitivities
- Chronic conditions and ICD-10 problem lists
- Current and past medication regimens
- Longitudinal laboratory observations (HbA1c, CBC, Lipid panel, LFT, RFT)
Every answer is strictly grounded in patient chart data with zero hallucination.
"""
from __future__ import annotations

import os
import re
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
    get_full_patient_chart,
    get_patient_allergies,
    get_patient_conditions,
    get_patient_medications,
    get_patient_observations,
    get_patient_profile,
)
from llm_client import UnifiedLLMClient


class RecordsQueryResponse(BaseModel):
    """Structured response to a patient records query."""
    patient_id: str
    query_category: str = Field(description="ALLERGIES, MEDICATIONS, CONDITIONS, LABS, PROFILE, or GENERAL")
    answer_text: str
    grounding_sources: List[str] = Field(default_factory=list)
    has_critical_alerts: bool = False
    critical_alerts: List[str] = Field(default_factory=list)


RECORDS_AGENT_PROMPT = """You are the Clinical Records Coordinator at City Care Clinics.
Your job is to answer questions about a patient's medical file accurately and politely in clear English and UrduLish.

STRICT CLINICAL RULES:
1. ONLY cite facts that exist in the provided Patient Chart data below.
2. DO NOT invent lab values, dosages, or allergies.
3. When discussing lab tests, always mention the test date, numeric value, unit, and whether it was within or outside the normal reference range.
4. If the requested information is not in the patient's record, state clearly: 'Yeh maloomat aapke medical record mein maujood nahi hain.'
5. Highlight drug allergies with a safety warning emoji (⚠️).
"""


class RecordsAgent:
    """Production Patient Records Specialist Agent."""

    def __init__(self, llm_client: Optional[UnifiedLLMClient] = None):
        self.llm = llm_client or UnifiedLLMClient()

    def identify_query_category(self, question: str) -> str:
        """Classifies the focus of the clinical question."""
        q = question.lower()
        if any(w in q for w in ["allergy", "allergies", "reaction", "penicillin", "sulfa"]):
            return "ALLERGIES"
        if any(w in q for w in ["medicine", "medicines", "dawa", "dawain", "medication", "pill", "tablet", "dose", "panadol"]):
            return "MEDICATIONS"
        if any(w in q for w in ["sugar", "diabetes", "bp", "blood pressure", "hypertension", "bimari", "condition", "asthma", "heart"]):
            return "CONDITIONS"
        if any(w in q for w in ["lab", "test", "report", "hba1c", "cbc", "cholesterol", "lipid", "creatinine", "alt", "platelet", "hemoglobin", "wbc"]):
            return "LABS"
        if any(w in q for w in ["profile", "cnic", "phone", "address", "age", "contact", "name"]):
            return "PROFILE"
        return "GENERAL"

    def answer_records_query(
        self,
        patient_id: str,
        question: str,
        use_llm: bool = True
    ) -> RecordsQueryResponse:
        """Answers a clinical query against patient EHR chart."""
        chart = get_full_patient_chart(patient_id)
        if chart.get("status") == "NOT_FOUND":
            return RecordsQueryResponse(
                patient_id=patient_id,
                query_category="GENERAL",
                answer_text=f"Record not found: Patient '{patient_id}' does not exist in City Care Clinics database.",
                grounding_sources=["EHR Database - Patient Registry"]
            )

        category = self.identify_query_category(question)
        profile = chart.get("profile", {})
        allergies = chart.get("allergies", [])
        conditions = chart.get("conditions", [])
        medications = chart.get("medications", [])
        observations = chart.get("observations", [])

        grounding_sources = []
        critical_alerts = []

        # Identify critical allergy alerts
        if allergies:
            for a in allergies:
                critical_alerts.append(f"Allergy Alert: {a.get('substance')} ({a.get('manifestation')})")

        # Deterministic formatting
        deterministic_answer = self._format_deterministic_answer(
            category=category,
            question=question,
            profile=profile,
            allergies=allergies,
            conditions=conditions,
            medications=medications,
            observations=observations,
            grounding_sources=grounding_sources
        )

        if not use_llm:
            return RecordsQueryResponse(
                patient_id=patient_id,
                query_category=category,
                answer_text=deterministic_answer,
                grounding_sources=grounding_sources,
                has_critical_alerts=len(critical_alerts) > 0,
                critical_alerts=critical_alerts
            )

        # Enhance with LLM synthesis
        context_str = (
            f"Patient: {profile.get('full_name')} (Age: {profile.get('age')}, Gender: {profile.get('gender')})\n"
            f"Active Allergies: {allergies}\n"
            f"Chronic Conditions: {conditions}\n"
            f"Current Medications: {medications}\n"
            f"Lab Observations: {observations}\n"
        )

        user_prompt = f"""Patient Chart Data:
{context_str}

User Question:
"{question}"

Please provide a clear, clinically accurate, and helpful response. If speaking about medications or labs, mention the specific dates and reference ranges.
"""
        try:
            llm_text = self.llm.generate_text(prompt=user_prompt, system_instruction=RECORDS_AGENT_PROMPT)
            final_text = llm_text if llm_text and len(llm_text.strip()) > 20 else deterministic_answer
        except Exception:
            final_text = deterministic_answer

        return RecordsQueryResponse(
            patient_id=patient_id,
            query_category=category,
            answer_text=final_text,
            grounding_sources=grounding_sources or ["EHR Chart Database"],
            has_critical_alerts=len(critical_alerts) > 0,
            critical_alerts=critical_alerts
        )

    def _format_deterministic_answer(
        self,
        category: str,
        question: str,
        profile: Dict[str, Any],
        allergies: List[Dict[str, Any]],
        conditions: List[Dict[str, Any]],
        medications: List[Dict[str, Any]],
        observations: List[Dict[str, Any]],
        grounding_sources: List[str]
    ) -> str:
        """Builds structured answer directly from DB records."""
        name = profile.get("full_name", "Patient")

        if category == "ALLERGIES":
            grounding_sources.append("EHR AllergyIntolerance Repository")
            if not allergies:
                return f"{name} ke record mein koi active drug allergy darj nahi hai (No Known Drug Allergies - NKDA)."
            items = [f"⚠️ {a.get('substance')}: {a.get('manifestation')} (Criticality: {a.get('criticality')})" for a in allergies]
            return f"{name} ke record mein mundarja zail allergies darj hain:\n" + "\n".join(items)

        if category == "MEDICATIONS":
            grounding_sources.append("EHR MedicationRequest Repository")
            if not medications:
                return f"{name} ke record mein filhal koi active prescription medicine darj nahi hai."
            items = [f"• {m.get('medication_name')} ({m.get('generic_name')}) — {m.get('dose_mg')} mg, {m.get('frequency')}, Route: {m.get('route')}" for m in medications]
            return f"{name} ke record mein mundarja zail medicines shamil hain:\n" + "\n".join(items)

        if category == "CONDITIONS":
            grounding_sources.append("EHR Condition Problem List")
            if not conditions:
                return f"{name} ke record mein koi chronic condition darj nahi hai."
            items = [f"• {c.get('display_name')} (ICD-10: {c.get('icd10_code')}) — Status: {c.get('clinical_status')}, Severity: {c.get('severity')}" for c in conditions]
            return f"{name} ke active medical problem list mein yeh conditions shamil hain:\n" + "\n".join(items)

        if category == "LABS":
            grounding_sources.append("EHR Diagnostic Observation Repository")
            if not observations:
                return f"{name} ke record mein koi lab report darj nahi hai."
            items = []
            for o in observations:
                items.append(
                    f"• {o.get('display_name')}: {o.get('value_numeric')} {o.get('unit')} "
                    f"(Normal range: {o.get('reference_range')}) — Result: {o.get('interpretation')}, Date: {o.get('effective_datetime')}"
                )
            return f"{name} ke lab results mundarja zail hain:\n" + "\n".join(items)

        # General summary
        grounding_sources.append("EHR Longitudinal Patient Chart")
        cond_str = ", ".join([c.get("display_name", "") for c in conditions]) or "None"
        med_str = ", ".join([m.get("medication_name", "") for m in medications]) or "None"
        alg_str = ", ".join([a.get("substance", "") for a in allergies]) or "None (NKDA)"

        return (
            f"Patient Chart Summary for {name} (Age: {profile.get('age')}, City: {profile.get('city')}):\n"
            f"- Conditions: {cond_str}\n"
            f"- Current Medications: {med_str}\n"
            f"- Allergies: {alg_str}\n"
            f"- Lab Tests on record: {len(observations)} tests available."
        )
