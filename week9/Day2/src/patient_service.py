"""City Care Clinics - Patient Management & Record Services.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Implements secure patient registration, authorized profile retrieval, clinical history access,
appointment records, and longitudinal preference management with input validation.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from db_models import (
    AllergyIntoleranceModel,
    AppointmentModel,
    ConditionModel,
    MedicationRequestModel,
    ObservationModel,
    PatientModel,
    PatientPreferenceModel,
    VisitModel,
    get_db_engine,
    init_db,
)


class PatientRegistrationInput(BaseModel):
    """Validated input schema for new patient onboarding."""
    full_name: str = Field(min_length=2, max_length=100)
    gender: str = Field(pattern=r"^(MALE|FEMALE|OTHER)$")
    birth_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    age: int = Field(ge=0, le=120)
    phone: str = Field(pattern=r"^03\d{2}-\d{7}$")  # Pakistani mobile: 03XX-XXXXXXX
    cnic: Optional[str] = Field(default=None, pattern=r"^\d{5}-\d{7}-\d{1}$")  # 13-digit CNIC
    city: str = Field(default="Lahore")
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    preferred_language: str = Field(default="UrduLish")
    consent_given: bool = True


class PatientProfileOutput(BaseModel):
    """Sanitized patient profile response."""
    patient_id: str
    full_name: str
    gender: str
    birth_date: str
    age: int
    is_pediatric: bool
    phone: str
    cnic: Optional[str]
    city: str
    address: Optional[str]
    emergency_contact: Optional[str]
    consent_given: bool
    created_at: str


class PatientService:
    """Production service for managing patient records and longitudinal continuity."""

    def __init__(self, db_engine=None):
        self.engine = db_engine or get_db_engine()
        self.session_factory = init_db(self.engine)

    def register_patient(self, data: Union[PatientRegistrationInput, Dict[str, Any]]) -> Dict[str, Any]:
        """Registers a new patient with unique phone verification and baseline preferences."""
        if isinstance(data, dict):
            # Normalise dictionary inputs from web forms
            reg_dict = dict(data)
            if "gender" in reg_dict and isinstance(reg_dict["gender"], str):
                reg_dict["gender"] = reg_dict["gender"].upper()
            if "birth_date" not in reg_dict:
                age_val = int(reg_dict.get("age", 25))
                year_val = datetime.now().year - age_val
                reg_dict["birth_date"] = f"{year_val}-01-01"
            if "consent_given" not in reg_dict:
                reg_dict["consent_given"] = True
            data = PatientRegistrationInput(**reg_dict)

        session = self.session_factory()
        try:
            # Check for existing patient with identical phone or CNIC
            existing = session.query(PatientModel).filter(
                (PatientModel.phone == data.phone) |
                ((PatientModel.cnic != None) & (PatientModel.cnic == data.cnic))
            ).first()

            if existing:
                return {
                    "status": "DUPLICATE",
                    "message": f"Patient already registered with this phone/CNIC (Patient ID: {existing.id}).",
                    "patient_id": existing.id
                }

            # Generate structured Pakistani patient ID (e.g., PT_1042)
            pt_count = session.query(PatientModel).count()
            patient_id = f"PT_{pt_count + 1:04d}"
            is_pediatric = data.age < 14

            new_pt = PatientModel(
                id=patient_id,
                full_name=data.full_name,
                gender=data.gender,
                birth_date=data.birth_date,
                age=data.age,
                is_pediatric=is_pediatric,
                phone=data.phone,
                cnic=data.cnic,
                city=data.city,
                address=data.address,
                emergency_contact=data.emergency_contact,
                consent_given=data.consent_given,
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_pt)

            # Create default preference
            pref = PatientPreferenceModel(
                id=f"PREF_{uuid.uuid4().hex[:8].upper()}",
                patient_id=patient_id,
                preferred_language=data.preferred_language,
                preferred_channel="web_chat",
                last_updated=datetime.now(timezone.utc)
            )
            session.add(pref)

            session.commit()
            return {
                "status": "CREATED",
                "patient_id": patient_id,
                "full_name": data.full_name,
                "message": f"Patient {data.full_name} successfully registered with ID {patient_id}."
            }
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_patient_profile(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves verified demographic and administrative profile."""
        session = self.session_factory()
        try:
            pt = session.query(PatientModel).filter_by(id=patient_id).first()
            if not pt:
                return None

            return {
                "patient_id": pt.id,
                "full_name": pt.full_name,
                "gender": pt.gender,
                "birth_date": pt.birth_date,
                "age": pt.age,
                "is_pediatric": pt.is_pediatric,
                "phone": pt.phone,
                "cnic": pt.cnic,
                "city": pt.city,
                "address": pt.address,
                "emergency_contact": pt.emergency_contact,
                "consent_given": pt.consent_given,
                "created_at": pt.created_at.isoformat() if pt.created_at else None
            }
        finally:
            session.close()

    def update_patient_profile(self, patient_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Authorized update of non-clinical patient contact details."""
        session = self.session_factory()
        try:
            pt = session.query(PatientModel).filter_by(id=patient_id).first()
            if not pt:
                return {"status": "NOT_FOUND", "message": f"Patient '{patient_id}' not found."}

            allowed_fields = ["phone", "address", "city", "emergency_contact", "consent_given"]
            for field in allowed_fields:
                if field in updates:
                    setattr(pt, field, updates[field])

            session.commit()
            return {"status": "UPDATED", "patient_id": patient_id, "message": "Profile updated successfully."}
        finally:
            session.close()

    def get_patient_medical_history(self, patient_id: str) -> Dict[str, Any]:
        """Retrieves authoritative clinical chart: allergies, chronic conditions, and active meds."""
        session = self.session_factory()
        try:
            pt = session.query(PatientModel).filter_by(id=patient_id).first()
            if not pt:
                return {"status": "NOT_FOUND", "patient_id": patient_id, "allergies": [], "conditions": [], "medications": []}

            allergies = [
                {
                    "substance": a.substance,
                    "clinical_status": a.clinical_status,
                    "criticality": a.criticality,
                    "manifestation": a.manifestation,
                    "recorded_date": a.recorded_date
                }
                for a in pt.allergies
            ]

            conditions = [
                {
                    "code": c.code,
                    "display_name": c.display_name,
                    "clinical_status": c.clinical_status,
                    "severity": c.severity,
                    "onset_date": c.onset_date
                }
                for c in pt.conditions
            ]

            medications = [
                {
                    "medication_name": m.medication_name,
                    "generic_name": m.generic_name,
                    "dose_mg": m.dose_mg,
                    "frequency": m.frequency,
                    "status": m.status,
                    "authored_on": m.authored_on
                }
                for m in pt.medications
            ]

            observations = [
                {
                    "test_category": o.test_category,
                    "display_name": o.display_name,
                    "value": o.value_numeric if o.value_numeric is not None else o.value_string,
                    "unit": o.unit,
                    "interpretation": o.interpretation,
                    "date": o.effective_datetime
                }
                for o in pt.observations
            ]

            return {
                "status": "SUCCESS",
                "patient_id": pt.id,
                "full_name": pt.full_name,
                "allergies": allergies,
                "conditions": conditions,
                "medications": medications,
                "observations": observations
            }
        finally:
            session.close()

    def get_patient_appointments(self, patient_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves appointment history and upcoming bookings for a patient."""
        session = self.session_factory()
        try:
            appts = session.query(AppointmentModel).filter_by(patient_id=patient_id).order_by(
                AppointmentModel.created_at.desc()
            ).limit(limit).all()

            results = []
            for a in appts:
                doc_name = a.practitioner.name if a.practitioner else "Consulting Doctor"
                branch_name = a.branch.name if a.branch else "Clinic Branch"
                results.append({
                    "booking_id": a.id,
                    "doctor_name": doc_name,
                    "specialty": a.specialty,
                    "branch_name": branch_name,
                    "slot_datetime": a.slot_datetime,
                    "status": a.status,
                    "token_number": a.token_number,
                    "urgency_tier": a.urgency_tier,
                    "chief_complaint": a.chief_complaint,
                    "created_at": a.created_at.isoformat() if a.created_at else None
                })
            return results
        finally:
            session.close()

    def get_patient_preferences(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves longitudinal patient care preferences."""
        session = self.session_factory()
        try:
            pref = session.query(PatientPreferenceModel).filter_by(patient_id=patient_id).first()
            if not pref:
                return None

            return {
                "preferred_language": pref.preferred_language,
                "preferred_branch_id": pref.preferred_branch_id,
                "preferred_branch_name": pref.preferred_branch.name if pref.preferred_branch else None,
                "preferred_doctor_id": pref.preferred_doctor_id,
                "preferred_doctor_name": pref.preferred_doctor.name if pref.preferred_doctor else None,
                "preferred_channel": pref.preferred_channel,
                "special_notes": pref.special_notes,
                "last_updated": pref.last_updated.isoformat() if pref.last_updated else None
            }
        finally:
            session.close()

    def update_patient_preferences(
        self,
        patient_id: str,
        preferred_doctor_id: Optional[str] = None,
        preferred_branch_id: Optional[str] = None,
        preferred_language: Optional[str] = None,
        special_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Updates or seeds patient preferences in the database."""
        session = self.session_factory()
        try:
            pref = session.query(PatientPreferenceModel).filter_by(patient_id=patient_id).first()
            if not pref:
                pref = PatientPreferenceModel(
                    id=f"PREF_{uuid.uuid4().hex[:8].upper()}",
                    patient_id=patient_id,
                    preferred_language=preferred_language or "UrduLish"
                )
                session.add(pref)

            if preferred_doctor_id:
                pref.preferred_doctor_id = preferred_doctor_id
            if preferred_branch_id:
                pref.preferred_branch_id = preferred_branch_id
            if preferred_language:
                pref.preferred_language = preferred_language
            if special_notes:
                pref.special_notes = special_notes

            pref.last_updated = datetime.now(timezone.utc)
            session.commit()
            return {"status": "SUCCESS", "patient_id": patient_id}
        finally:
            session.close()

    def get_patient_chart(self, identifier: str) -> Dict[str, Any]:
        """Finds patient by ID, phone, or CNIC and returns consolidated chart."""
        session = self.session_factory()
        try:
            pt = session.query(PatientModel).filter(
                (PatientModel.id == identifier) |
                (PatientModel.phone == identifier) |
                (PatientModel.cnic == identifier)
            ).first()
            if not pt:
                return {"status": "NOT_FOUND", "message": f"Patient '{identifier}' not found."}

            demo = {
                "patient_id": pt.id,
                "name": pt.full_name,
                "phone": pt.phone,
                "cnic": pt.cnic,
                "gender": pt.gender,
                "age": pt.age,
                "city": pt.city,
                "consent_given": pt.consent_given,
            }
            return {
                "status": "SUCCESS",
                "demographics": demo,
                "allergies": [{"substance": a.substance, "severity": a.criticality} for a in pt.allergies],
                "conditions": [{"code": c.code, "display": c.display_name} for c in pt.conditions],
                "preferences": {
                    "preferred_language": pt.preference.preferred_language if pt.preference else "UrduLish",
                    "preferred_doctor_id": pt.preference.preferred_doctor_id if pt.preference else None,
                    "preferred_branch_id": pt.preference.preferred_branch_id if pt.preference else None,
                }
            }
        finally:
            session.close()


# Singleton Instance
_patient_service_instance: Optional[PatientService] = None

def get_patient_service(db_engine=None) -> PatientService:
    """Returns singleton PatientService instance."""
    global _patient_service_instance
    if _patient_service_instance is None or db_engine is not None:
        _patient_service_instance = PatientService(db_engine=db_engine)
    return _patient_service_instance

