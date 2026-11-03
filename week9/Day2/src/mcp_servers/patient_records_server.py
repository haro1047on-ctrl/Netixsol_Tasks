"""City Care Clinics - Patient Records MCP Server.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Exposes FHIR Patient, Condition, AllergyIntolerance, MedicationRequest,
and Observation data over Model Context Protocol (FastMCP).
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

# Add parent dir to sys.path to access db_models
SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from db_models import (
    AllergyIntoleranceModel,
    ConditionModel,
    MedicationRequestModel,
    ObservationModel,
    PatientModel,
    get_db_engine,
    init_db,
)

mcp_patient_records = FastMCP(
    name="patient-records-server",
    instructions="Provides authorized read-access to City Care Clinics patient charts, histories, allergies, and lab results."
)

engine = get_db_engine()
session_factory = init_db(engine)


@mcp_patient_records.tool()
def get_patient_profile(identifier: str) -> Dict[str, Any]:
    """Retrieves patient demographic and contact summary by Patient ID, Phone, or CNIC.

    Args:
        identifier: Patient ID (e.g. PT_0001), Phone (e.g. 0300-1234567), or CNIC.
    """
    session = session_factory()
    try:
        pt = session.query(PatientModel).filter(
            (PatientModel.id == identifier) |
            (PatientModel.phone == identifier) |
            (PatientModel.cnic == identifier)
        ).first()

        if not pt:
            return {"status": "NOT_FOUND", "message": f"Patient '{identifier}' not found in clinic records."}

        return {
            "status": "FOUND",
            "patient_id": pt.id,
            "full_name": pt.full_name,
            "gender": pt.gender,
            "age": pt.age,
            "birth_date": pt.birth_date,
            "is_pediatric": pt.is_pediatric,
            "phone": pt.phone,
            "cnic": pt.cnic,
            "address": pt.address,
            "city": pt.city,
            "emergency_contact": pt.emergency_contact
        }
    finally:
        session.close()


@mcp_patient_records.tool()
def get_patient_allergies(patient_id: str) -> List[Dict[str, Any]]:
    """Retrieves active drug and environmental allergies for a patient.

    Args:
        patient_id: Unique Patient ID (e.g. PT_0001).
    """
    session = session_factory()
    try:
        allergies = session.query(AllergyIntoleranceModel).filter_by(patient_id=patient_id).all()
        return [
            {
                "allergy_id": a.id,
                "substance": a.substance,
                "clinical_status": a.clinical_status,
                "criticality": a.criticality,
                "manifestation": a.manifestation,
                "recorded_date": a.recorded_date
            }
            for a in allergies
        ]
    finally:
        session.close()


@mcp_patient_records.tool()
def get_patient_conditions(patient_id: str) -> List[Dict[str, Any]]:
    """Retrieves active chronic medical conditions and ICD-10 problem list.

    Args:
        patient_id: Unique Patient ID.
    """
    session = session_factory()
    try:
        conditions = session.query(ConditionModel).filter_by(patient_id=patient_id).all()
        return [
            {
                "condition_id": c.id,
                "icd10_code": c.code,
                "display_name": c.display_name,
                "clinical_status": c.clinical_status,
                "severity": c.severity
            }
            for c in conditions
        ]
    finally:
        session.close()


@mcp_patient_records.tool()
def get_patient_medications(patient_id: str) -> List[Dict[str, Any]]:
    """Retrieves active and historical prescribed medications.

    Args:
        patient_id: Unique Patient ID.
    """
    session = session_factory()
    try:
        meds = session.query(MedicationRequestModel).filter_by(patient_id=patient_id).all()
        return [
            {
                "medication_id": m.id,
                "medication_name": m.medication_name,
                "generic_name": m.generic_name,
                "dose_mg": m.dose_mg,
                "frequency": m.frequency,
                "route": m.route,
                "status": m.status,
                "authored_on": m.authored_on
            }
            for m in meds
        ]
    finally:
        session.close()


@mcp_patient_records.tool()
def get_patient_observations(patient_id: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves diagnostic lab observations (HbA1c, CBC, Lipid, LFT, RFT).

    Args:
        patient_id: Unique Patient ID.
        category: Optional filter by panel (e.g. HbA1c, CBC, Lipid, LFT, RFT).
    """
    session = session_factory()
    try:
        query = session.query(ObservationModel).filter_by(patient_id=patient_id)
        if category:
            query = query.filter_by(test_category=category)
        obs = query.all()

        return [
            {
                "observation_id": o.id,
                "test_category": o.test_category,
                "code": o.code,
                "display_name": o.display_name,
                "value_numeric": o.value_numeric,
                "unit": o.unit,
                "reference_range": f"{o.reference_low} - {o.reference_high}",
                "interpretation": o.interpretation,
                "effective_datetime": o.effective_datetime
            }
            for o in obs
        ]
    finally:
        session.close()


@mcp_patient_records.tool()
def get_full_patient_chart(patient_id: str) -> Dict[str, Any]:
    """Aggregates longitudinal patient chart: demographics, allergies, chronic conditions, meds, and recent labs.

    Args:
        patient_id: Unique Patient ID.
    """
    profile = get_patient_profile(patient_id)
    if profile.get("status") == "NOT_FOUND":
        return profile

    allergies = get_patient_allergies(patient_id)
    conditions = get_patient_conditions(patient_id)
    medications = get_patient_medications(patient_id)
    observations = get_patient_observations(patient_id)

    return {
        "status": "SUCCESS",
        "profile": profile,
        "allergies": allergies,
        "conditions": conditions,
        "medications": medications,
        "observations": observations
    }


if __name__ == "__main__":
    mcp_patient_records.run()
