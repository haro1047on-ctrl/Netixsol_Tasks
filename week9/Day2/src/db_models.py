"""City Care Clinics - FHIR-Inspired Relational Database Models & Enterprise Schema.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Supports PostgreSQL and SQLite via SQLAlchemy.
FHIR v4 Aligned:
- ClinicBranchModel (clinic_branches)
- SpecialtyModel (clinical_specialties)
- PractitionerModel (practitioners)
- DoctorScheduleModel (doctor_schedules)
- PatientModel (patients)
- PatientPreferenceModel (patient_preferences)
- AllergyIntoleranceModel (allergy_intolerances)
- ConditionModel (conditions)
- MedicationRequestModel (medication_requests)
- AppointmentModel (appointments)
- VisitModel (visits)
- ObservationModel (observations)
- ConversationThreadModel (conversation_threads)
- ConversationMessageModel (conversation_messages)
- DoctorApprovalRequestModel (doctor_approval_requests)
- NotificationModel (notifications)
- AuditEventModel (audit_events)
- UserModel (users)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


# =============================================================================
# 1. CLINIC LOCATIONS & SPECIALTIES
# =============================================================================

class ClinicBranchModel(Base):
    """City Care Clinics Physical Branches (Lahore & Islamabad)."""
    __tablename__ = "clinic_branches"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    city = Column(String(50), nullable=False)
    address = Column(String(255), nullable=False)
    phone = Column(String(30), nullable=False)
    emergency_hospital_nearby = Column(String(100), nullable=False)


class SpecialtyModel(Base):
    """Supported Clinical Outpatient Specialties."""
    __tablename__ = "clinical_specialties"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)


# =============================================================================
# 2. DOCTOR DIRECTORY & SCHEDULES
# =============================================================================

class PractitionerModel(Base):
    """FHIR Practitioner: Doctors across 6 specialties and 5 branches."""
    __tablename__ = "practitioners"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    specialty = Column(String(50), nullable=False, index=True)
    branch_id = Column(String(50), ForeignKey("clinic_branches.id"), nullable=False)
    pmdc_number = Column(String(30), nullable=False)
    qualification = Column(String(100), nullable=False)
    experience_years = Column(Integer, default=10)
    consultation_fee_pkr = Column(Integer, default=2000)
    languages_spoken = Column(String(100), default="Urdu, English, Punjabi")
    available_days = Column(String(100), default="Mon-Sat")
    shift_hours = Column(String(50), default="17:00-21:00")

    branch = relationship("ClinicBranchModel")
    appointments = relationship("AppointmentModel", back_populates="practitioner")
    schedules = relationship("DoctorScheduleModel", back_populates="practitioner", cascade="all, delete-orphan")


class DoctorScheduleModel(Base):
    """Configured working shifts, days, and approved leave periods for a physician."""
    __tablename__ = "doctor_schedules"

    id = Column(String(50), primary_key=True)
    practitioner_id = Column(String(50), ForeignKey("practitioners.id"), nullable=False, index=True)
    day_of_week = Column(String(20), nullable=False)  # Monday, Tuesday, etc.
    shift_start = Column(String(10), nullable=False, default="17:00")  # HH:MM
    shift_end = Column(String(10), nullable=False, default="21:00")    # HH:MM
    slot_duration_minutes = Column(Integer, default=15)
    is_active = Column(Boolean, default=True)
    is_leave = Column(Boolean, default=False)
    leave_date = Column(String(20), nullable=True)  # YYYY-MM-DD
    leave_reason = Column(String(255), nullable=True)

    practitioner = relationship("PractitionerModel", back_populates="schedules")


# =============================================================================
# 3. PATIENTS & LONGITUDINAL PREFERENCES
# =============================================================================

class PatientModel(Base):
    """FHIR Patient: Demographics, Pakistani identifiers, contact."""
    __tablename__ = "patients"

    id = Column(String(50), primary_key=True)
    full_name = Column(String(100), nullable=False)
    gender = Column(String(20), nullable=False)
    birth_date = Column(String(20), nullable=False)
    age = Column(Integer, nullable=False)
    is_pediatric = Column(Boolean, default=False)
    phone = Column(String(30), nullable=False, index=True)
    email = Column(String(100), nullable=True)
    cnic = Column(String(30), nullable=True, index=True)
    address = Column(String(255), nullable=True)
    city = Column(String(50), default="Lahore")
    emergency_contact = Column(String(50), nullable=True)
    consent_given = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    allergies = relationship("AllergyIntoleranceModel", back_populates="patient", cascade="all, delete-orphan")
    conditions = relationship("ConditionModel", back_populates="patient", cascade="all, delete-orphan")
    medications = relationship("MedicationRequestModel", back_populates="patient", cascade="all, delete-orphan")
    appointments = relationship("AppointmentModel", back_populates="patient", cascade="all, delete-orphan")
    observations = relationship("ObservationModel", back_populates="patient", cascade="all, delete-orphan")
    preference = relationship("PatientPreferenceModel", back_populates="patient", uselist=False, cascade="all, delete-orphan")
    visits = relationship("VisitModel", back_populates="patient", cascade="all, delete-orphan")


class PatientPreferenceModel(Base):
    """Persistent patient preferences across clinic encounters."""
    __tablename__ = "patient_preferences"

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.id"), unique=True, nullable=False, index=True)
    preferred_language = Column(String(30), default="UrduLish")
    preferred_branch_id = Column(String(50), ForeignKey("clinic_branches.id"), nullable=True)
    preferred_doctor_id = Column(String(50), ForeignKey("practitioners.id"), nullable=True)
    preferred_channel = Column(String(30), default="web_chat")
    special_notes = Column(Text, nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("PatientModel", back_populates="preference")
    preferred_branch = relationship("ClinicBranchModel")
    preferred_doctor = relationship("PractitionerModel")


# =============================================================================
# 4. CLINICAL ENTITIES (FHIR ALIGNED)
# =============================================================================

class AllergyIntoleranceModel(Base):
    """FHIR AllergyIntolerance: Drug & environmental allergies."""
    __tablename__ = "allergy_intolerances"

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=False, index=True)
    substance = Column(String(100), nullable=False)
    clinical_status = Column(String(30), default="active")
    verification_status = Column(String(30), default="confirmed")
    category = Column(String(30), default="medication")
    criticality = Column(String(30), default="high")
    manifestation = Column(String(255), default="Anaphylaxis / Skin Rash / Bronchospasm")
    recorded_date = Column(String(30), default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    patient = relationship("PatientModel", back_populates="allergies")


class ConditionModel(Base):
    """FHIR Condition: Confirmed chronic and acute diagnoses."""
    __tablename__ = "conditions"

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=False, index=True)
    code = Column(String(50), nullable=False)  # ICD-10 code
    display_name = Column(String(150), nullable=False)
    clinical_status = Column(String(30), default="active")
    category = Column(String(50), default="problem-list-item")
    severity = Column(String(30), default="moderate")
    onset_date = Column(String(30), nullable=True)

    patient = relationship("PatientModel", back_populates="conditions")


class MedicationRequestModel(Base):
    """FHIR MedicationRequest: Active and past prescription orders."""
    __tablename__ = "medication_requests"

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=False, index=True)
    practitioner_id = Column(String(50), ForeignKey("practitioners.id"), nullable=True)
    medication_name = Column(String(150), nullable=False)
    generic_name = Column(String(150), nullable=False)
    dose_mg = Column(Float, nullable=False)
    frequency = Column(String(50), nullable=False)
    route = Column(String(30), default="Oral")
    status = Column(String(30), default="active")
    authored_on = Column(String(30), default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    patient = relationship("PatientModel", back_populates="medications")


class AppointmentModel(Base):
    """FHIR Appointment: Outpatient visit scheduling records."""
    __tablename__ = "appointments"

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=False, index=True)
    practitioner_id = Column(String(50), ForeignKey("practitioners.id"), nullable=False, index=True)
    branch_id = Column(String(50), ForeignKey("clinic_branches.id"), nullable=False)
    specialty = Column(String(50), nullable=False)
    slot_datetime = Column(String(50), nullable=False, index=True)
    status = Column(String(30), default="booked", index=True)  # booked, arrived, fulfilled, cancelled, rescheduled
    token_number = Column(Integer, default=1)
    urgency_tier = Column(String(30), default="ROUTINE")
    chief_complaint = Column(Text, nullable=True)
    rescheduled_from_slot = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("PatientModel", back_populates="appointments")
    practitioner = relationship("PractitionerModel", back_populates="appointments")
    branch = relationship("ClinicBranchModel")


class VisitModel(Base):
    """Completed clinic visit encounter records linking diagnosis, doctor, and patient."""
    __tablename__ = "visits"

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=False, index=True)
    practitioner_id = Column(String(50), ForeignKey("practitioners.id"), nullable=False, index=True)
    branch_id = Column(String(50), ForeignKey("clinic_branches.id"), nullable=False)
    appointment_id = Column(String(50), ForeignKey("appointments.id"), nullable=True)
    visit_date = Column(String(30), nullable=False)  # YYYY-MM-DD
    chief_complaint = Column(String(255), nullable=False)
    diagnosis_summary = Column(Text, nullable=True)
    clinical_notes = Column(Text, nullable=True)
    vitals_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("PatientModel", back_populates="visits")
    practitioner = relationship("PractitionerModel")
    branch = relationship("ClinicBranchModel")


class ObservationModel(Base):
    """FHIR Observation: Lab metrics, vitals, test investigations."""
    __tablename__ = "observations"

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=False, index=True)
    test_category = Column(String(50), nullable=False)  # CBC, LFT, Lipid, HbA1c, RFT
    code = Column(String(50), nullable=False)  # LOINC code or test code
    display_name = Column(String(150), nullable=False)
    value_numeric = Column(Float, nullable=True)
    value_string = Column(String(100), nullable=True)
    unit = Column(String(30), nullable=False)
    reference_low = Column(Float, nullable=True)
    reference_high = Column(Float, nullable=True)
    interpretation = Column(String(30), default="NORMAL")  # NORMAL, HIGH, LOW, CRITICAL
    effective_datetime = Column(String(50), default=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d"))

    patient = relationship("PatientModel", back_populates="observations")


# =============================================================================
# 5. CONVERSATION THREADS & MESSAGES (PERSISTENT MEMORY)
# =============================================================================

class ConversationThreadModel(Base):
    """Persistent chat sessions across patient touchpoints."""
    __tablename__ = "conversation_threads"

    id = Column(String(100), primary_key=True)  # thread_id
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=True, index=True)
    channel = Column(String(30), default="web_chat")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    patient = relationship("PatientModel")
    messages = relationship("ConversationMessageModel", back_populates="thread", cascade="all, delete-orphan", order_by="ConversationMessageModel.timestamp_utc")


class ConversationMessageModel(Base):
    """Individual serialized message turn in a conversation thread."""
    __tablename__ = "conversation_messages"

    id = Column(String(100), primary_key=True)
    thread_id = Column(String(100), ForeignKey("conversation_threads.id"), nullable=False, index=True)
    sender_role = Column(String(20), nullable=False)  # user, assistant, system, doctor
    content = Column(Text, nullable=False)
    intent = Column(String(50), nullable=True)
    metadata_json = Column(Text, nullable=True)
    timestamp_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    thread = relationship("ConversationThreadModel", back_populates="messages")


# =============================================================================
# 6. HUMAN-IN-THE-LOOP (HITL) CLINICIAN APPROVALS
# =============================================================================

class DoctorApprovalRequestModel(Base):
    """Database-backed clinical draft approvals requiring attending physician sign-off."""
    __tablename__ = "doctor_approval_requests"

    id = Column(String(50), primary_key=True)  # e.g. HITL_1234ABCD
    thread_id = Column(String(100), nullable=True, index=True)
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # LAB_RESULT_EXPLANATION, PRESCRIPTION_MESSAGE, LOW_CONFIDENCE_TRIAGE
    reason_for_interrupt = Column(String(255), nullable=False)
    draft_message_for_patient = Column(Text, nullable=False)
    clinical_context_json = Column(Text, nullable=True)
    status = Column(String(30), default="PENDING", index=True)  # PENDING, APPROVED, EDITED, REJECTED
    reviewing_doctor_id = Column(String(50), nullable=True)
    reviewing_doctor_name = Column(String(100), nullable=True)
    doctor_edited_message = Column(Text, nullable=True)
    doctor_clinical_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    reviewed_at = Column(DateTime, nullable=True)

    patient = relationship("PatientModel")


# =============================================================================
# 7. NOTIFICATIONS & PERSISTENT REMINDER QUEUE
# =============================================================================

class NotificationModel(Base):
    """Persistent notification and reminder dispatch tracking."""
    __tablename__ = "notifications"

    id = Column(String(50), primary_key=True)
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=True, index=True)
    appointment_id = Column(String(50), ForeignKey("appointments.id"), nullable=True, index=True)
    channel = Column(String(30), nullable=False)  # EMAIL, SMS, WHATSAPP
    recipient = Column(String(100), nullable=False)
    subject = Column(String(255), nullable=True)
    body = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)  # CONFIRMATION, RESCHEDULE, CANCELLATION, REMINDER_48H, REMINDER_7D
    status = Column(String(30), default="PENDING", index=True)  # PENDING, PROCESSING, SENT, FAILED
    scheduled_for = Column(DateTime, nullable=True, index=True)
    sent_at = Column(DateTime, nullable=True)
    provider_receipt = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("PatientModel")
    appointment = relationship("AppointmentModel")


# =============================================================================
# 8. AUDIT LOGS & AUTHENTICATION USERS
# =============================================================================

class AuditEventModel(Base):
    """Cryptographic SHA-256 chained tamper-evident audit log."""
    __tablename__ = "audit_events"

    id = Column(String(50), primary_key=True)
    timestamp_utc = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    actor_id = Column(String(50), nullable=False)
    actor_role = Column(String(30), nullable=False)  # PATIENT, DOCTOR, RECEPTIONIST, SYSTEM
    action_type = Column(String(50), nullable=False)  # READ, WRITE, OVERRIDE, TRIAGE_ESCALATE, HITL_ACTION
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=False)
    payload_summary = Column(Text, nullable=False)
    previous_event_hash = Column(String(64), nullable=False)
    event_hash_sha256 = Column(String(64), nullable=False)


class UserModel(Base):
    """User account credentials and role-based permissions."""
    __tablename__ = "users"

    id = Column(String(50), primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(30), nullable=False)  # PATIENT, DOCTOR, ADMIN
    patient_id = Column(String(50), ForeignKey("patients.id"), nullable=True, unique=True)
    practitioner_id = Column(String(50), ForeignKey("practitioners.id"), nullable=True, unique=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("PatientModel")
    practitioner = relationship("PractitionerModel")


# =============================================================================
# ENGINE & SESSION INITIALIZATION
# =============================================================================

def get_db_engine(db_path: Optional[str] = None):
    """Factory creating SQLAlchemy Engine supporting SQLite and PostgreSQL."""
    pg_url = os.getenv("DATABASE_URL")
    if pg_url and pg_url.startswith("postgresql"):
        try:
            engine = create_engine(pg_url, pool_pre_ping=True)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine
        except Exception:
            pass  # fallback to SQLite

    if not db_path:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        db_path = os.path.join(base_dir, "clinic_fhir.db")

    sqlite_url = f"sqlite:///{db_path}"
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    return engine


def init_db(engine=None):
    """Initializes tables in database non-destructively and applies schema updates."""
    if engine is None:
        engine = get_db_engine()
    Base.metadata.create_all(bind=engine)

    # Safe non-destructive column migration for SQLite / PostgreSQL
    with engine.begin() as conn:
        try:
            conn.execute(text("ALTER TABLE patients ADD COLUMN consent_given BOOLEAN DEFAULT 1"))
        except Exception:
            pass  # Column already exists

        try:
            conn.execute(text("ALTER TABLE appointments ADD COLUMN rescheduled_from_slot VARCHAR(50)"))
        except Exception:
            pass  # Column already exists

        try:
            conn.execute(text("ALTER TABLE patients ADD COLUMN email VARCHAR(100)"))
        except Exception:
            pass  # Column already exists

        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(100)"))
        except Exception:
            pass  # Column already exists

    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory
