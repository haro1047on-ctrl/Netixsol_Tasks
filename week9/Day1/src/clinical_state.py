"""City Care Clinics - Clinical State & Schema Definitions.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Defines typed Pydantic models and LangGraph TypedDict states for all 8 agents.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Any, Dict, List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field


class TriageLevel(str, Enum):
    """Three-tier clinical urgency classification."""
    EMERGENCY = "EMERGENCY"  # Immediate 1122 escalation, outpatient halt
    URGENT = "URGENT"        # Same-day appointment within 4-6 hours
    ROUTINE = "ROUTINE"      # Standard appointment within 1-3 days


class ClinicalSpecialty(str, Enum):
    """The 6 supported outpatient clinical specialties."""
    GENERAL_MEDICINE = "General Medicine"
    PAEDIATRICS = "Paediatrics"
    GYNAECOLOGY = "Gynaecology"
    CARDIOLOGY = "Cardiology"
    DERMATOLOGY = "Dermatology"
    ENT = "ENT"


class ClinicBranch(str, Enum):
    """The 5 clinic branches across Lahore and Islamabad."""
    LAHORE_GULBERG = "Lahore Gulberg"
    LAHORE_DHA = "Lahore DHA"
    LAHORE_JOHAR_TOWN = "Lahore Johar Town"
    ISLAMABAD_F8 = "Islamabad F-8"
    ISLAMABAD_BLUE_AREA = "Islamabad Blue Area"


class PatientProfile(BaseModel):
    """Sanitized patient demographic and clinical baseline."""
    patient_id: str = Field(default="PT_ANON")
    full_name: str = Field(default="Anonymous Patient")
    age: int = Field(default=30, ge=0, le=120)
    gender: Literal["MALE", "FEMALE", "OTHER"] = Field(default="MALE")
    is_pediatric: bool = Field(default=False)
    phone: str = Field(default="0300-0000000")
    cnic: Optional[str] = Field(default=None)
    guardian_name: Optional[str] = Field(default=None)
    known_allergies: List[str] = Field(default_factory=list)
    chronic_conditions: List[str] = Field(default_factory=list)
    active_medications: List[str] = Field(default_factory=list)


class TriageAssessment(BaseModel):
    """Structured output from the Triage Agent."""
    urgency_level: TriageLevel = Field(default=TriageLevel.ROUTINE)
    red_flag_detected: bool = Field(default=False)
    red_flag_category: Optional[str] = Field(default=None)
    matched_specialty: ClinicalSpecialty = Field(default=ClinicalSpecialty.GENERAL_MEDICINE)
    clinical_rationale: str = Field(default="Standard intake, no danger signs identified.")
    emergency_script_urdu: Optional[str] = Field(default=None)


class AppointmentBooking(BaseModel):
    """Structured appointment transaction record."""
    booking_id: Optional[str] = Field(default=None)
    patient_id: str
    doctor_name: str
    specialty: ClinicalSpecialty
    branch: ClinicBranch
    slot_datetime: str
    consultation_fee_pkr: int = Field(default=2000)
    token_number: int = Field(default=1)
    status: Literal["CONFIRMED", "RESCHEDULED", "CANCELLED", "PENDING"] = Field(default="PENDING")


class SOAPNote(BaseModel):
    """Standardized physician pre-visit brief and clinical draft."""
    subjective: str = Field(description="Patient's reported symptoms, duration, history")
    objective: str = Field(description="Recorded vitals, labs, observations")
    assessment_draft: str = Field(description="AI differential symptom clusters (Non-diagnostic draft)")
    plan_draft: str = Field(description="Suggested baseline investigations and doctor review points")
    doctor_approved: bool = Field(default=False)
    doctor_signature: Optional[str] = Field(default=None)
    doctor_notes: Optional[str] = Field(default=None)


class PrescriptionItem(BaseModel):
    """Single medication order."""
    drug_name: str
    generic_name: str
    dose_mg: float
    frequency: str
    route: str = Field(default="Oral")
    duration_days: int = Field(default=5)


class PrescriptionCheckResult(BaseModel):
    """Output of the Prescription Safety Agent."""
    safety_status: Literal["SAFE", "WARNING_MODERATE", "CRITICAL_DANGER"] = Field(default="SAFE")
    allergy_clashes: List[str] = Field(default_factory=list)
    drug_interactions: List[str] = Field(default_factory=list)
    dose_limit_violations: List[str] = Field(default_factory=list)
    recommendation_for_doctor: str = Field(default="Medication regimen verified safe.")


class AuditLogEntry(BaseModel):
    """Tamper-evident audit log event."""
    event_id: str
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    actor_id: str
    actor_role: Literal["PATIENT", "RECEPTIONIST", "NURSE", "ATTENDING_DOCTOR", "SYSTEM"]
    action_type: Literal["READ", "WRITE", "OVERRIDE", "TRIAGE_ESCALATE", "HITL_INTERRUPT"]
    resource_type: str
    resource_id: str
    payload_summary: str
    previous_event_hash: str
    event_hash_sha256: str = Field(default="")

    def compute_hash(self) -> str:
        """Computes SHA-256 hash of this entry chained to the previous entry."""
        content = f"{self.previous_event_hash}|{self.timestamp_utc}|{self.actor_id}|{self.action_type}|{self.resource_id}|{self.payload_summary}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ClinicState(TypedDict):
    """Central Typed State for LangGraph Multi-Agent Runtime."""
    session_id: str
    patient_profile: PatientProfile
    raw_user_message: str
    sanitized_user_message: str
    pii_vault: Dict[str, str]
    current_agent: str
    next_agent: str
    intake_complete: bool
    chief_complaint: str
    symptom_duration: str
    symptom_severity: int
    triage_assessment: TriageAssessment
    active_booking: Optional[AppointmentBooking]
    soap_note: Optional[SOAPNote]
    prescription_check: Optional[PrescriptionCheckResult]
    hitl_pending: bool
    hitl_reason: Optional[str]
    audit_chain_tip: str
    conversation_history: List[Dict[str, str]]
