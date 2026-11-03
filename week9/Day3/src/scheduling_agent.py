"""City Care Clinics - Scheduling Specialist Agent.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Core Capabilities:
1. Clinical Symptom -> Specialty Mapping.
2. Doctor Preference Filtering (Gender, Language, Branch, Fee, Experience).
3. Slot Search, Anti-Past-Date Validation, and Anti-Double-Booking Protection.
4. Google Calendar Event Payload Generation (RFC 5545 / v3 API).
5. Culturally Respectful UrduLish Slot Offering and Booking Confirmation.
"""
from __future__ import annotations

import os
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
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

from db_models import (
    AppointmentModel,
    ClinicBranchModel,
    DoctorScheduleModel,
    PatientModel,
    PractitionerModel,
    get_db_engine,
    init_db,
)


class DoctorPreference(BaseModel):
    """Filter criteria for matching patient with an optimal physician."""
    specialty: Optional[str] = None
    symptoms: Optional[str] = None
    gender_preference: Optional[str] = Field(default="ANY", description="MALE, FEMALE, or ANY")
    language_preference: Optional[str] = Field(default=None, description="Urdu, Punjabi, English")
    branch_preference: Optional[str] = Field(default=None, description="DHA, Gulberg, Johar Town, F-8, Blue Area")
    city_preference: Optional[str] = Field(default=None, description="Lahore, Islamabad")
    max_fee_pkr: Optional[int] = Field(default=None, description="Budget cap in PKR")


class BookingRequest(BaseModel):
    """Input payload for reserving an appointment slot."""
    patient_id: str
    doctor_id: str
    slot_datetime: str  # Format: YYYY-MM-DD HH:MM
    chief_complaint: str
    urgency_tier: str = "ROUTINE"


class BookingResult(BaseModel):
    """Structured response from appointment scheduling operations."""
    status: str = Field(description="CONFIRMED, SLOT_CONFLICT, PAST_DATE_ERROR, NOT_FOUND, or CANCELLED")
    booking_id: Optional[str] = None
    token_number: Optional[int] = None
    doctor_name: Optional[str] = None
    specialty: Optional[str] = None
    branch: Optional[str] = None
    city: Optional[str] = None
    slot_datetime: Optional[str] = None
    fee_pkr: Optional[int] = None
    google_calendar_event: Optional[Dict[str, Any]] = None
    urdulish_message: str = ""
    message: str = ""


# Common Pakistani Female Names for Doctor Gender Inference
FEMALE_NAME_TOKENS = {
    "ayesha", "fatima", "zainab", "sadia", "mariam", "hina", "nida", "bushra",
    "sana", "amna", "samina", "khadija", "farah", "rabia", "shaista", "mahnoor",
    "anila", "uzma", "tahira", "shazia", "marium", "asma", "faiza"
}

# Symptom to Specialty Rulebase
SYMPTOM_SPECIALTY_RULES = [
    (r"\b(rash|khujli|acne|dana|daaney|skin|jild|eczema|fungal|hair fall|balo.n)\b", "Dermatology"),
    (r"\b(kaan|ear|gala|galay|throat|naak|nose|tonsil|sinus|hearing|suno|awaz)\b", "ENT"),
    (r"\b(dil|chest pain|seenay|seene|palpitation|dharkan|blood pressure|high bp|hypertension)\b", "Cardiology"),
    (r"\b(hamal|pregnancy|pregnant|period|haiz|menstrual|pelvic|aurat|ladies|khawateen|gynae)\b", "Gynaecology"),
    (r"\b(bacha|bachi|bachay|bache|bachon|beta|beti|baby|child|children|infant|newborn|toddler|vaccination|teeka|pediatric)\b", "Paediatrics"),
    (r"\b(fever|bukhar|cough|khansi|flu|nazla|sugar|diabetes|weakness|kamzori|pet|stomach)\b", "General Medicine"),
]


class SchedulingAgent:
    """Production Scheduling Specialist Agent for City Care Clinics."""

    def __init__(self, db_engine=None):
        self.engine = db_engine or get_db_engine()
        self.session_factory = init_db(self.engine)
        # Default clinic reference time for evaluation & past-date validation
        self.reference_now = datetime(2026, 10, 8, 12, 0, 0)

    def set_reference_time(self, ref_time: datetime) -> None:
        """Sets internal reference clock for testing past/future booking checks."""
        self.reference_now = ref_time

    def map_symptoms_to_specialty(self, symptom_text: str, is_pediatric: bool = False) -> str:
        """Determines best clinical specialty based on patient symptoms and demographics."""
        if is_pediatric:
            return "Paediatrics"

        text_lower = symptom_text.lower()
        for pattern, specialty in SYMPTOM_SPECIALTY_RULES:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return specialty

        return "General Medicine"

    def infer_doctor_gender(self, doctor_name: str) -> str:
        """Infers doctor gender from Pakistani name conventions."""
        tokens = re.sub(r"[^\w\s]", "", doctor_name.lower()).split()
        for t in tokens:
            if t in FEMALE_NAME_TOKENS:
                return "FEMALE"
        return "MALE"

    def match_doctors(self, preferences: DoctorPreference) -> List[Dict[str, Any]]:
        """Finds doctors matching clinical specialty and patient preferences."""
        session = self.session_factory()
        try:
            specialty = preferences.specialty
            if not specialty and preferences.symptoms:
                specialty = self.map_symptoms_to_specialty(preferences.symptoms)

            query = session.query(PractitionerModel).join(ClinicBranchModel)

            if specialty:
                query = query.filter(PractitionerModel.specialty.ilike(f"%{specialty}%"))

            if preferences.city_preference:
                query = query.filter(ClinicBranchModel.city.ilike(f"%{preferences.city_preference}%"))

            if preferences.branch_preference:
                query = query.filter(ClinicBranchModel.name.ilike(f"%{preferences.branch_preference}%"))

            if preferences.max_fee_pkr:
                query = query.filter(PractitionerModel.consultation_fee_pkr <= preferences.max_fee_pkr)

            all_candidates = query.all()

            results = []
            for doc in all_candidates:
                inferred_gender = self.infer_doctor_gender(doc.name)

                # Filter by gender preference
                if preferences.gender_preference and preferences.gender_preference.upper() != "ANY":
                    if inferred_gender != preferences.gender_preference.upper():
                        continue

                # Filter by language preference
                if preferences.language_preference:
                    req_lang = preferences.language_preference.lower()
                    doc_langs = (doc.languages_spoken or "").lower()
                    if req_lang not in doc_langs:
                        continue

                results.append({
                    "doctor_id": doc.id,
                    "name": doc.name,
                    "gender": inferred_gender,
                    "specialty": doc.specialty,
                    "qualification": doc.qualification,
                    "experience_years": doc.experience_years,
                    "branch_id": doc.branch_id,
                    "branch_name": doc.branch.name if doc.branch else "Main Branch",
                    "city": doc.branch.city if doc.branch else "Lahore",
                    "consultation_fee_pkr": doc.consultation_fee_pkr,
                    "languages_spoken": doc.languages_spoken,
                    "shift_hours": doc.shift_hours,
                    "available_days": doc.available_days
                })

            # Sort by experience descending, then fee ascending
            results.sort(key=lambda d: (-d["experience_years"], d["consultation_fee_pkr"]))
            return results
        finally:
            session.close()

    def get_available_slots(self, doctor_id: str, target_date: str) -> List[str]:
        """Calculates free 15-minute consultation slots on a given date."""
        session = self.session_factory()
        try:
            doc = session.query(PractitionerModel).filter_by(id=doctor_id).first()
            if not doc:
                return []

            # Check if doctor has active leave on that date
            on_leave = session.query(DoctorScheduleModel).filter(
                DoctorScheduleModel.practitioner_id == doctor_id,
                DoctorScheduleModel.is_leave == True,
                DoctorScheduleModel.leave_date == target_date
            ).first()
            if on_leave:
                return []  # Doctor on leave; no slots available

            # Check existing booked appointments on that date
            booked = session.query(AppointmentModel).filter(
                AppointmentModel.practitioner_id == doctor_id,
                AppointmentModel.slot_datetime.like(f"{target_date}%"),
                AppointmentModel.status.in_(["booked", "arrived", "confirmed"])
            ).all()
            booked_times = {a.slot_datetime.split(" ")[1] for a in booked if " " in a.slot_datetime}

            # Generate slots based on shift hours (e.g. 17:00-21:00)
            start_hour, end_hour = 17, 21
            if "-" in (doc.shift_hours or ""):
                try:
                    parts = doc.shift_hours.split("-")
                    start_hour = int(parts[0].split(":")[0])
                    end_hour = int(parts[1].split(":")[0])
                except Exception:
                    pass

            available_slots = []
            for h in range(start_hour, end_hour):
                for m in (0, 15, 30, 45):
                    time_str = f"{h:02d}:{m:02d}"
                    if time_str not in booked_times:
                        available_slots.append(f"{target_date} {time_str}")

            return available_slots
        finally:
            session.close()

    def create_google_calendar_event(
        self,
        booking_id: str,
        patient_name: str,
        doctor_name: str,
        specialty: str,
        branch_name: str,
        branch_address: str,
        slot_datetime: str,
        token_number: int,
        chief_complaint: str,
        fee_pkr: int
    ) -> Dict[str, Any]:
        """Builds RFC 5545 Google Calendar v3 Event resource."""
        # Parse slot timestamp
        dt_start = datetime.strptime(slot_datetime, "%Y-%m-%d %H:%M")
        dt_end = dt_start + timedelta(minutes=15)

        start_iso = dt_start.strftime("%Y-%m-%dT%H:%M:00+05:00")
        end_iso = dt_end.strftime("%Y-%m-%dT%H:%M:00+05:00")

        event_payload = {
            "kind": "calendar#event",
            "id": f"gcal_{booking_id.lower()}",
            "status": "confirmed",
            "htmlLink": f"https://calendar.google.com/calendar/event?eid={uuid.uuid4().hex[:12]}",
            "summary": f"Consultation: {doctor_name} ({specialty}) - {patient_name}",
            "description": (
                f"City Care Clinics Outpatient Consultation\n"
                f"Booking ID: {booking_id}\n"
                f"Token Number: #{token_number}\n"
                f"Doctor: {doctor_name} ({specialty})\n"
                f"Patient: {patient_name}\n"
                f"Chief Complaint: {chief_complaint}\n"
                f"Consultation Fee: PKR {fee_pkr}\n"
                f"Please arrive 10 minutes prior to your token slot."
            ),
            "location": f"{branch_name}, {branch_address}",
            "start": {
                "dateTime": start_iso,
                "timeZone": "Asia/Karachi"
            },
            "end": {
                "dateTime": end_iso,
                "timeZone": "Asia/Karachi"
            },
            "attendees": [
                {"displayName": patient_name, "responseStatus": "accepted"},
                {"displayName": doctor_name, "responseStatus": "accepted"}
            ],
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 60},
                    {"method": "popup", "minutes": 1440}
                ]
            },
            "iCalUID": f"{booking_id}@citycareclinics.pk"
        }
        return event_payload

    def book_appointment(self, request: BookingRequest) -> BookingResult:
        """Atomically books a consultation slot with zero double-booking and zero past-booking invariants."""
        # 1. Past Date Validation Check
        try:
            slot_dt = datetime.strptime(request.slot_datetime, "%Y-%m-%d %H:%M")
        except ValueError:
            return BookingResult(
                status="ERROR",
                message=f"Invalid slot_datetime format '{request.slot_datetime}'. Expected 'YYYY-MM-DD HH:MM'."
            )

        if slot_dt < self.reference_now:
            return BookingResult(
                status="PAST_DATE_ERROR",
                message=f"Cannot book appointments in the past. Requested {request.slot_datetime}, current time is {self.reference_now.strftime('%Y-%m-%d %H:%M')}."
            )

        session = self.session_factory()
        try:
            doc = session.query(PractitionerModel).filter_by(id=request.doctor_id).first()
            if not doc:
                return BookingResult(status="NOT_FOUND", message=f"Doctor '{request.doctor_id}' does not exist.")

            patient = session.query(PatientModel).filter_by(id=request.patient_id).first()
            patient_name = patient.full_name if patient else "Valued Patient"

            # 2. Anti-Double-Booking Invariant Check
            collision = session.query(AppointmentModel).filter(
                AppointmentModel.practitioner_id == request.doctor_id,
                AppointmentModel.slot_datetime == request.slot_datetime,
                AppointmentModel.status.in_(["booked", "arrived", "confirmed"])
            ).first()

            if collision:
                return BookingResult(
                    status="SLOT_CONFLICT",
                    doctor_name=doc.name,
                    specialty=doc.specialty,
                    slot_datetime=request.slot_datetime,
                    message=f"Slot '{request.slot_datetime}' with {doc.name} is already booked. Double-booking prevented.",
                    urdulish_message=f"Maaf kijiye ga, doctor sahib ka yeh slot ({request.slot_datetime}) pehle se booked hai. Barah-e-karam clinic ka doosra waqt muntakhib karein."
                )

            # 3. Token Allocation & Reservation
            date_str = request.slot_datetime.split(" ")[0]
            existing_count = session.query(AppointmentModel).filter(
                AppointmentModel.practitioner_id == request.doctor_id,
                AppointmentModel.slot_datetime.like(f"{date_str}%")
            ).count()
            token_num = existing_count + 1

            booking_id = f"APT_BK_{uuid.uuid4().hex[:8].upper()}"
            branch_name = doc.branch.name if doc.branch else "Main Clinic"
            branch_city = doc.branch.city if doc.branch else "Lahore"
            branch_addr = doc.branch.address if doc.branch else "Clinic Road"

            # Concurrency double check immediately before committing
            recheck = session.query(AppointmentModel).filter(
                AppointmentModel.practitioner_id == request.doctor_id,
                AppointmentModel.slot_datetime == request.slot_datetime,
                AppointmentModel.status.in_(["booked", "arrived", "confirmed"])
            ).first()
            if recheck:
                return BookingResult(
                    status="SLOT_CONFLICT",
                    message=f"Slot '{request.slot_datetime}' was just reserved concurrently. Double-booking prevented."
                )

            new_appt = AppointmentModel(
                id=booking_id,
                patient_id=request.patient_id,
                practitioner_id=request.doctor_id,
                branch_id=doc.branch_id,
                specialty=doc.specialty,
                slot_datetime=request.slot_datetime,
                status="booked",
                token_number=token_num,
                urgency_tier=request.urgency_tier,
                chief_complaint=request.chief_complaint,
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_appt)
            session.commit()

            # Automatically schedule 24h & 2h reminders in persistent NotificationModel
            try:
                from services.reminder_service import get_reminder_service
                get_reminder_service().schedule_appointment_reminders(booking_id)
            except Exception:
                pass

            # 4. Generate Google Calendar Event Payload
            gcal_event = self.create_google_calendar_event(
                booking_id=booking_id,
                patient_name=patient_name,
                doctor_name=doc.name,
                specialty=doc.specialty,
                branch_name=branch_name,
                branch_address=branch_addr,
                slot_datetime=request.slot_datetime,
                token_number=token_num,
                chief_complaint=request.chief_complaint,
                fee_pkr=doc.consultation_fee_pkr
            )

            # 5. Respectful UrduLish Confirmation Message
            urdulish_conf = (
                f"Aapki appointment {doc.name} ({doc.specialty}) ke saath {request.slot_datetime} "
                f"ko {branch_name} mein confirm ho chuki hai. "
                f"Aapka Token #{token_num} hai. Consultation fee PKR {doc.consultation_fee_pkr} hai. Shukriya!"
            )

            return BookingResult(
                status="CONFIRMED",
                booking_id=booking_id,
                token_number=token_num,
                doctor_name=doc.name,
                specialty=doc.specialty,
                branch=branch_name,
                city=branch_city,
                slot_datetime=request.slot_datetime,
                fee_pkr=doc.consultation_fee_pkr,
                google_calendar_event=gcal_event,
                urdulish_message=urdulish_conf,
                message=f"Appointment {booking_id} successfully confirmed."
            )
        finally:
            session.close()

    def reschedule_appointment(self, booking_id: str, new_slot_datetime: str) -> BookingResult:
        """Reschedules an existing appointment to a new validated slot."""
        try:
            slot_dt = datetime.strptime(new_slot_datetime, "%Y-%m-%d %H:%M")
        except ValueError:
            return BookingResult(
                status="ERROR",
                message=f"Invalid new_slot_datetime format '{new_slot_datetime}'."
            )

        if slot_dt < self.reference_now:
            return BookingResult(
                status="PAST_DATE_ERROR",
                message=f"Cannot reschedule into past date {new_slot_datetime}."
            )

        session = self.session_factory()
        try:
            appt = session.query(AppointmentModel).filter_by(id=booking_id).first()
            if not appt:
                return BookingResult(status="NOT_FOUND", message=f"Booking '{booking_id}' not found.")

            # Check collision with any currently active booking
            collision = session.query(AppointmentModel).filter(
                AppointmentModel.practitioner_id == appt.practitioner_id,
                AppointmentModel.slot_datetime == new_slot_datetime,
                AppointmentModel.status.in_(["booked", "arrived", "confirmed"])
            ).first()
            if collision and collision.id != booking_id:
                return BookingResult(
                    status="SLOT_CONFLICT",
                    message=f"Slot '{new_slot_datetime}' is already booked. Reschedule collision prevented."
                )

            old_slot = appt.slot_datetime
            appt.slot_datetime = new_slot_datetime
            appt.status = "booked"  # Maintain active booked status
            appt.rescheduled_from_slot = old_slot
            session.commit()

            try:
                from services.reminder_service import get_reminder_service
                get_reminder_service().schedule_appointment_reminders(booking_id)
            except Exception:
                pass

            doc_name = appt.practitioner.name if appt.practitioner else "Doctor"
            branch_name = appt.branch.name if appt.branch else "Clinic"

            urdulish_msg = (
                f"Aapki appointment reschedule kar di gayi hai: Ab {doc_name} ke saath "
                f"naya waqt {new_slot_datetime} hai ({branch_name})."
            )

            return BookingResult(
                status="CONFIRMED",
                booking_id=appt.id,
                token_number=appt.token_number,
                doctor_name=doc_name,
                specialty=appt.specialty,
                branch=branch_name,
                slot_datetime=new_slot_datetime,
                urdulish_message=urdulish_msg,
                message=f"Rescheduled from {old_slot} to {new_slot_datetime}."
            )
        finally:
            session.close()

    def get_appointment_details(self, booking_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves verified appointment record and practitioner metadata."""
        session = self.session_factory()
        try:
            appt = session.query(AppointmentModel).filter_by(id=booking_id).first()
            if not appt:
                return None
            return {
                "booking_id": appt.id,
                "patient_id": appt.patient_id,
                "doctor_id": appt.practitioner_id,
                "doctor_name": appt.practitioner.name if appt.practitioner else "Doctor",
                "specialty": appt.specialty,
                "branch_name": appt.branch.name if appt.branch else "Clinic",
                "slot_datetime": appt.slot_datetime,
                "status": appt.status,
                "token_number": appt.token_number,
                "fee_pkr": appt.practitioner.consultation_fee_pkr if appt.practitioner else 2000,
                "created_at": appt.created_at.isoformat() if appt.created_at else None
            }
        finally:
            session.close()

    def list_upcoming_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        """Lists active confirmed and booked appointments for a patient."""
        session = self.session_factory()
        try:
            appts = session.query(AppointmentModel).filter(
                AppointmentModel.patient_id == patient_id,
                AppointmentModel.status.in_(["booked", "arrived", "confirmed"])
            ).order_by(AppointmentModel.slot_datetime.asc()).all()

            return [
                {
                    "booking_id": a.id,
                    "doctor_name": a.practitioner.name if a.practitioner else "Doctor",
                    "specialty": a.specialty,
                    "branch_name": a.branch.name if a.branch else "Clinic",
                    "slot_datetime": a.slot_datetime,
                    "status": a.status,
                    "token_number": a.token_number
                }
                for a in appts
            ]
        finally:
            session.close()

    def cancel_appointment(self, booking_id: str, reason: str = "Patient request") -> BookingResult:
        """Cancels an appointment and frees up the consultation slot."""
        session = self.session_factory()
        try:
            appt = session.query(AppointmentModel).filter_by(id=booking_id).first()
            if not appt:
                return BookingResult(status="NOT_FOUND", message=f"Booking '{booking_id}' not found.")

            appt.status = "cancelled"
            session.commit()

            urdulish_msg = (
                f"Aapki appointment ({booking_id}) mansookh (cancel) kar di gayi hai. "
                f"Agar doobara booking karni ho tou rabta karein."
            )

            return BookingResult(
                status="CANCELLED",
                booking_id=booking_id,
                slot_datetime=appt.slot_datetime,
                urdulish_message=urdulish_msg,
                message=f"Appointment {booking_id} cancelled. Reason: {reason}."
            )
        finally:
            session.close()

    def generate_proactive_offer_urdu(
        self,
        doctor_name: str,
        specialty: str,
        slot_str: str,
        branch_name: str
    ) -> str:
        """Generates natural conversational UrduLish slot proposal."""
        # e.g.: 'Dr. Ayesha (Paediatrics) kal subah 10:30 baje DHA branch mein available hain. Kya main confirm kar doon?'
        return f"{doctor_name} ({specialty}) {slot_str} {branch_name} mein available hain. Kya main confirm kar doon?"
