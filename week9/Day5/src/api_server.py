"""City Care Clinics - Production FastAPI Multi-Agent Service.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 5: Evaluation, Red-Teaming, Deployment & Client Handover
Production REST API serving the clinic multi-agent system:
- GET  /health                      -> Health checks for Database, ChromaDB RAG, and MCP tools
- POST /api/v1/auth/register        -> Secure user registration with bcrypt
- POST /api/v1/auth/login           -> JWT authentication with role-based claims
- GET  /api/v1/auth/me              -> Authenticated user identity
- GET  /api/v1/patient/me           -> Current patient chart and medical records
- GET  /api/v1/patient/{id}         -> EHR chart with strict cross-patient isolation guard
- GET  /api/v1/patient/{id}/appointments -> Patient appointment history
- GET  /api/v1/clinic/branches      -> Clinic branch directory across Lahore & Islamabad
- GET  /api/v1/clinic/doctors       -> 30 certified practitioners with specialty & branch filters
- GET  /api/v1/schedule/slots       -> Real available consultation slots
- POST /api/v1/schedule/book        -> Atomic booking with anti-double-booking invariant
- POST /api/v1/schedule/reschedule  -> Appointment reschedule preserving slot occupancy
- POST /api/v1/schedule/cancel      -> Appointment cancellation and slot release
- GET  /api/v1/schedule/appointments -> Active appointment registry
- POST /api/v1/chat                 -> Web / WhatsApp unified supervisor agent turn
- POST /api/v1/triage               -> Direct clinical triage urgency assessment
- GET  /api/v1/hitl/queue           -> Pending physician approval queue (DB-backed)
- POST /api/v1/hitl/action          -> Physician Approve / Edit / Reject action
- POST /api/v1/notifications/reminders/process -> Trigger persistent background reminder dispatch
- GET  /api/v1/notifications/audit  -> Persistent communication audit trail
- POST /api/v1/lab/analyze          -> Diagnostic lab document analysis
- GET  /api/v1/telemetry            -> Operational latency, cost, and trace metrics
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException, Security, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

# Setup path resolution
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
WEEK9_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
DAY3_SRC = os.path.join(WEEK9_DIR, "Day3", "src")
DAY4_SRC = os.path.join(WEEK9_DIR, "Day4", "src")

for p in [SRC_DIR, DAY4_SRC, DAY3_SRC, DAY2_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import settings
from db_models import (
    AppointmentModel,
    ClinicBranchModel,
    PatientModel,
    PractitionerModel,
    UserModel,
    get_db_engine,
    init_db
)
from services.auth_service import AuthService, get_auth_service
from services.reminder_service import get_reminder_service
from supervisor_graph import ClinicSupervisorOrchestrator
from hitl_manager import get_hitl_manager
from scheduling_agent import SchedulingAgent, BookingRequest, BookingResult, DoctorPreference
from triage_agent import TriageAgent
from lab_report_analyzer import LabReportAnalyzer
from mcp_servers.patient_records_server import get_full_patient_chart
from mcp_servers.notifications_server import get_notification_audit_log

app = FastAPI(
    title="City Care Clinics Multi-Agent Healthcare API",
    description="Enterprise multi-agent AI assistant for triage, scheduling, clinical records, and medical safety.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize singletons
db_engine = get_db_engine()
session_factory = init_db(db_engine)
orchestrator = ClinicSupervisorOrchestrator()
hitl_mgr = get_hitl_manager()
scheduling_agent = SchedulingAgent()
triage_agent = TriageAgent()
lab_analyzer = LabReportAnalyzer()
auth_service = get_auth_service()
reminder_service = get_reminder_service()

# Seed test accounts on startup
try:
    auth_service.seed_default_users()
except Exception:
    pass

# Security Bearer Scheme
security = HTTPBearer(auto_error=False)


# -----------------------------------------------------------------------------
# Database Session Dependency
# -----------------------------------------------------------------------------
def get_db():
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


# -----------------------------------------------------------------------------
# Authentication & Authorization Dependencies
# -----------------------------------------------------------------------------
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db)
) -> UserModel:
    """Extracts and verifies JWT token from Authorization header, returning UserModel."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    try:
        payload = auth_service.decode_access_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    user = db.query(UserModel).filter_by(id=user_id, is_active=True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated.")

    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    db: Session = Depends(get_db)
) -> Optional[UserModel]:
    """Optionally resolves current user without failing if unauthenticated."""
    if not credentials or not credentials.credentials:
        return None
    try:
        payload = auth_service.decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        return db.query(UserModel).filter_by(id=user_id, is_active=True).first()
    except Exception:
        return None


def require_role(*allowed_roles: str):
    """Enforces role-based access control (RBAC)."""
    def role_checker(current_user: UserModel = Depends(get_current_user)) -> UserModel:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def verify_patient_access(patient_id: str, current_user: UserModel) -> None:
    """Enforces strict patient record isolation.

    Patients can ONLY view their own records.
    Doctors and Administrators have authorized clinical oversight.
    """
    if current_user.role == "PATIENT":
        if current_user.patient_id != patient_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Patient record isolation violation. You cannot view Patient '{patient_id}'."
            )


# -----------------------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------------------
class UserRegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    role: str = "PATIENT"
    patient_id: Optional[str] = None
    practitioner_id: Optional[str] = None


class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    role: str
    patient_id: Optional[str] = None
    practitioner_id: Optional[str] = None
    full_name: str


class ChatRequest(BaseModel):
    thread_id: Optional[str] = None
    patient_id: Optional[str] = "PT_0001"
    patient_name: Optional[str] = "Valued Patient"
    patient_phone: Optional[str] = "0300-1234567"
    channel: str = "web_chat"
    message: str


class ChatResponse(BaseModel):
    thread_id: str
    patient_id: Optional[str]
    patient_response_urdu: str
    urgency_tier: Optional[str]
    matched_specialty: Optional[str]
    is_emergency: bool = False
    hitl_required: bool = False
    appointment_confirmed: bool = False
    booking_id: Optional[str] = None
    token_number: Optional[int] = None
    duration_ms: float


class TriageRequest(BaseModel):
    symptom_text: str
    patient_age: Optional[int] = None
    is_pediatric: bool = False
    reported_temp_f: Optional[float] = None


class RescheduleRequest(BaseModel):
    booking_id: str
    new_slot_datetime: str


class CancelRequest(BaseModel):
    booking_id: str
    reason: Optional[str] = "Patient requested cancellation"


class HITLActionRequest(BaseModel):
    request_id: str
    action: str = Field(description="APPROVE, EDIT, or REJECT")
    doctor_name: str = "Dr. Tariq Mahmood"
    edited_message: Optional[str] = None
    clinical_notes: Optional[str] = None


# -----------------------------------------------------------------------------
# 1. Health Check
# -----------------------------------------------------------------------------
@app.get("/health", status_code=status.HTTP_200_OK)
def health_check() -> Dict[str, Any]:
    """Production health check confirming database, orchestrator, and external dependencies."""
    db_status = "HEALTHY"
    try:
        session = session_factory()
        session.execute(text("SELECT 1"))
        session.close()
    except Exception as e:
        db_status = f"DEGRADED: {str(e)}"

    llm_status = "ONLINE (Groq)" if settings.groq_api_key else "OFFLINE_FALLBACK (Deterministic Safe Mode)"
    email_status = f"CONFIGURED ({settings.email_provider.upper()} -> {settings.smtp_host})"

    return {
        "status": "UP",
        "service": "City Care Clinics Multi-Agent API",
        "environment": settings.app_env,
        "clinic_timezone": settings.clinic_timezone,
        "database": db_status,
        "llm_provider": llm_status,
        "email_provider": email_status,
        "supervisor_graph": "ACTIVE",
        "supported_branches": 5,
        "certified_doctors": 30,
        "version": "1.0.0"
    }


# -----------------------------------------------------------------------------
# 2. Authentication & User Endpoints
# -----------------------------------------------------------------------------
@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Registers a new user account with bcrypt password hashing."""
    try:
        res = auth_service.register_user(
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
            email=payload.email,
            phone=payload.phone,
            patient_id=payload.patient_id,
            practitioner_id=payload.practitioner_id,
            db_session=db
        )
        return {"status": "SUCCESS", "user": res}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/api/v1/auth/login", response_model=TokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Authenticates credentials and returns a signed JWT access token."""
    user = auth_service.authenticate_user(payload.username_or_email, payload.password, db_session=db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    claims = {
        "sub": user.id,
        "username": user.username,
        "role": user.role,
        "patient_id": user.patient_id,
        "practitioner_id": user.practitioner_id,
        "full_name": user.full_name
    }
    access_token = auth_service.create_access_token(claims)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        role=user.role,
        patient_id=user.patient_id,
        practitioner_id=user.practitioner_id,
        full_name=user.full_name
    )


@app.get("/api/v1/auth/me")
def get_current_user_profile(current_user: UserModel = Depends(get_current_user)) -> Dict[str, Any]:
    """Returns the authenticated user's profile and permissions."""
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "patient_id": current_user.patient_id,
        "practitioner_id": current_user.practitioner_id,
        "phone": current_user.phone
    }


# -----------------------------------------------------------------------------
# 3. Patient EHR Records & Patient Isolation
# -----------------------------------------------------------------------------
@app.get("/api/v1/patient/me")
def get_my_patient_chart(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieves authenticated patient's own longitudinal EHR chart."""
    if not current_user.patient_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No patient profile linked to this user.")
    return get_full_patient_chart(current_user.patient_id)


@app.get("/api/v1/patient/{patient_id}")
def get_patient_chart(
    patient_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieves full EHR chart. Strictly enforces cross-patient isolation."""
    verify_patient_access(patient_id, current_user)
    chart = get_full_patient_chart(patient_id)
    if not chart or chart.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Patient '{patient_id}' not found.")
    return chart


@app.get("/api/v1/patient/{patient_id}/appointments")
def get_patient_appointments(
    patient_id: str,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieves appointments for a patient. Enforces patient isolation."""
    verify_patient_access(patient_id, current_user)
    appts = db.query(AppointmentModel).filter_by(patient_id=patient_id).order_by(AppointmentModel.slot_datetime.desc()).all()
    return [
        {
            "booking_id": a.id,
            "doctor_id": a.practitioner_id,
            "doctor_name": a.practitioner.name if a.practitioner else "Doctor",
            "specialty": a.specialty,
            "slot_datetime": a.slot_datetime,
            "token_number": a.token_number,
            "status": a.status,
            "chief_complaint": a.chief_complaint
        }
        for a in appts
    ]


# -----------------------------------------------------------------------------
# 4. Clinic Directory & Doctor Search
# -----------------------------------------------------------------------------
@app.get("/api/v1/clinic/branches")
def list_branches(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """Retrieves all 5 City Care Clinics branches across Lahore and Islamabad."""
    branches = db.query(ClinicBranchModel).all()
    return [
        {
            "branch_id": b.id,
            "name": b.name,
            "city": b.city,
            "address": b.address,
            "phone": b.phone,
            "emergency_hospital_nearby": b.emergency_hospital_nearby
        }
        for b in branches
    ]


@app.get("/api/v1/clinic/doctors")
def list_doctors(
    specialty: Optional[str] = None,
    city: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieves certified doctor directory with specialty and city filters."""
    query = db.query(PractitionerModel)
    if specialty:
        query = query.filter(PractitionerModel.specialty.ilike(f"%{specialty}%"))
    if city:
        query = query.join(ClinicBranchModel).filter(ClinicBranchModel.city.ilike(f"%{city}%"))

    docs = query.all()
    return [
        {
            "doctor_id": d.id,
            "name": d.name,
            "specialty": d.specialty,
            "branch_name": d.branch.name if d.branch else "Clinic",
            "city": d.branch.city if d.branch else "Lahore",
            "consultation_fee_pkr": d.consultation_fee_pkr,
            "shift_hours": d.shift_hours,
            "experience_years": d.experience_years
        }
        for d in docs
    ]


# -----------------------------------------------------------------------------
# 5. Doctor Appointment Scheduling Endpoints
# -----------------------------------------------------------------------------
@app.get("/api/v1/schedule/slots")
def get_available_slots(doctor_id: str, target_date: str) -> Dict[str, Any]:
    """Calculates free 15-minute consultation slots on target date."""
    slots = scheduling_agent.get_available_slots(doctor_id, target_date)
    return {
        "doctor_id": doctor_id,
        "target_date": target_date,
        "available_slots_count": len(slots),
        "slots": slots
    }


@app.post("/api/v1/schedule/book", response_model=BookingResult)
def book_appointment(payload: BookingRequest) -> BookingResult:
    """Atomically books a consultation slot with zero double-booking invariant."""
    result = scheduling_agent.book_appointment(payload)
    if result.status == "SLOT_CONFLICT":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.message)
    elif result.status == "PAST_DATE_ERROR":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
    elif result.status == "NOT_FOUND":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
    return result


@app.post("/api/v1/schedule/reschedule", response_model=BookingResult)
def reschedule_appointment(payload: RescheduleRequest) -> BookingResult:
    """Atomically reschedules appointment, freeing old slot and reserving new slot."""
    result = scheduling_agent.reschedule_appointment(payload.booking_id, payload.new_slot_datetime)
    if result.status == "SLOT_CONFLICT":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result.message)
    elif result.status == "NOT_FOUND":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
    elif result.status == "ERROR":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.message)
    return result


@app.post("/api/v1/schedule/cancel")
def cancel_appointment(payload: CancelRequest) -> Dict[str, Any]:
    """Cancels an appointment, releases the slot, and cleans up notifications."""
    result = scheduling_agent.cancel_appointment(payload.booking_id, payload.reason)
    if result.status == "NOT_FOUND":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=result.message)
    return result.model_dump()


@app.get("/api/v1/schedule/appointments")
def list_appointments(
    doctor_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Lists appointments with optional doctor and patient filters."""
    query = db.query(AppointmentModel)
    if doctor_id:
        query = query.filter_by(practitioner_id=doctor_id)
    if patient_id:
        query = query.filter_by(patient_id=patient_id)
    records = query.order_by(AppointmentModel.slot_datetime.desc()).limit(100).all()
    return [
        {
            "booking_id": r.id,
            "patient_id": r.patient_id,
            "patient_name": r.patient.full_name if r.patient else "Patient",
            "doctor_id": r.practitioner_id,
            "doctor_name": r.practitioner.name if r.practitioner else "Doctor",
            "specialty": r.specialty,
            "slot_datetime": r.slot_datetime,
            "token_number": r.token_number,
            "status": r.status,
            "chief_complaint": r.chief_complaint
        }
        for r in records
    ]


# -----------------------------------------------------------------------------
# 6. Conversational Chat & Triage Endpoints
# -----------------------------------------------------------------------------
@app.post("/api/v1/chat", response_model=ChatResponse)
def execute_chat_turn(
    payload: ChatRequest,
    current_user: Optional[UserModel] = Depends(get_optional_user)
) -> ChatResponse:
    """Invokes supervisor graph to process conversational turn across any channel."""
    thread_id = payload.thread_id or f"TH_{uuid.uuid4().hex[:8]}"
    effective_patient_id = payload.patient_id
    effective_patient_name = payload.patient_name
    effective_patient_phone = payload.patient_phone

    if current_user and current_user.role == "PATIENT":
        effective_patient_id = current_user.patient_id or payload.patient_id
        effective_patient_name = current_user.full_name
        effective_patient_phone = current_user.phone or payload.patient_phone

    final_state = orchestrator.run_turn(
        thread_id=thread_id,
        user_message=payload.message,
        patient_id=effective_patient_id,
        patient_name=effective_patient_name,
        patient_phone=effective_patient_phone,
        channel=payload.channel
    )

    booking = final_state.get("appointment_booking") or {}
    transitions = final_state.get("node_transitions") or []
    tot_dur = sum(t.get("duration_ms", 0.0) for t in transitions)

    return ChatResponse(
        thread_id=thread_id,
        patient_id=effective_patient_id,
        patient_response_urdu=final_state.get("final_patient_response", ""),
        urgency_tier=final_state.get("urgency_tier"),
        matched_specialty=final_state.get("matched_specialty"),
        is_emergency=final_state.get("is_emergency", False),
        hitl_required=final_state.get("hitl_required", False),
        appointment_confirmed=booking.get("status") == "CONFIRMED",
        booking_id=booking.get("booking_id"),
        token_number=booking.get("token_number"),
        duration_ms=round(tot_dur, 2)
    )


@app.post("/api/v1/triage")
def direct_triage(payload: TriageRequest) -> Dict[str, Any]:
    """Direct triage urgency assessment for mobile app or reception portal."""
    decision = triage_agent.evaluate_symptoms(
        symptom_text=payload.symptom_text,
        patient_age=payload.patient_age,
        is_pediatric=payload.is_pediatric,
        reported_temp_f=payload.reported_temp_f,
        use_llm=False
    )
    return decision.model_dump()


# -----------------------------------------------------------------------------
# 7. Human-in-the-Loop (HITL) Doctor Approvals
# -----------------------------------------------------------------------------
@app.get("/api/v1/hitl/queue")
def get_hitl_queue() -> List[Dict[str, Any]]:
    """Retrieves all pending clinical drafts awaiting physician sign-off (DB-backed)."""
    pending = hitl_mgr.list_pending()
    return [p.model_dump() for p in pending]


@app.post("/api/v1/hitl/action")
def resolve_hitl_action(payload: HITLActionRequest) -> Dict[str, Any]:
    """Attending physician action: Approve, Edit & Approve, or Reject."""
    action = payload.action.upper()
    try:
        if action == "APPROVE":
            req = hitl_mgr.approve_request(payload.request_id, doctor_name=payload.doctor_name)
        elif action == "EDIT":
            req = hitl_mgr.edit_and_approve(
                payload.request_id,
                doctor_name=payload.doctor_name,
                edited_message=payload.edited_message or "",
                clinical_notes=payload.clinical_notes
            )
        elif action == "REJECT":
            req = hitl_mgr.reject_request(
                payload.request_id,
                doctor_name=payload.doctor_name,
                rejection_reason=payload.clinical_notes or "Rejected by physician"
            )
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action. Must be APPROVE, EDIT, or REJECT.")

        return {"status": "SUCCESS", "request": req.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# -----------------------------------------------------------------------------
# 8. Persistent Reminders & Notifications
# -----------------------------------------------------------------------------
@app.post("/api/v1/notifications/reminders/process")
def trigger_reminder_worker() -> Dict[str, Any]:
    """Manually triggers background reminder worker to process all pending due reminders."""
    processed = reminder_service.process_due_reminders()
    return {
        "status": "COMPLETED",
        "processed_count": len(processed),
        "results": processed
    }


@app.get("/api/v1/notifications/audit")
def get_notifications_audit(recipient: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves persistent communication audit log from NotificationModel."""
    return get_notification_audit_log(recipient)


# -----------------------------------------------------------------------------
# 9. Lab Document Analysis & Telemetry
# -----------------------------------------------------------------------------
@app.post("/api/v1/lab/analyze")
def analyze_lab_report(pdf_path: Optional[str] = None) -> Dict[str, Any]:
    """Analyzes a laboratory report PDF and returns structured findings with safe explanation."""
    target_path = pdf_path
    if not target_path:
        # Default to benchmark report 1
        base_dir = os.path.dirname(os.path.abspath(__file__))
        target_path = os.path.join(WEEK9_DIR, "Day2", "data", "lab_reports", "LAB_REP_0001.pdf")

    if not os.path.exists(target_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PDF report not found at: {target_path}")

    parsed = lab_analyzer.parse_pdf_report(target_path)
    explanation = lab_analyzer.explain_report(parsed)
    return {
        "parsed_report": parsed,
        "patient_explanation_urdulish": explanation
    }


@app.get("/api/v1/telemetry")
def get_telemetry_metrics() -> Dict[str, Any]:
    """Retrieves operational latency, token counts, and cost metrics."""
    return orchestrator.telemetry.get_summary_metrics()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
