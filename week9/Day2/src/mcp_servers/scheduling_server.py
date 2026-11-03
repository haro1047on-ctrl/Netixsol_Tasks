"""City Care Clinics - Clinic Scheduling MCP Server.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Exposes doctor directory, appointment slot negotiation, booking,
rescheduling, and cancellations over Model Context Protocol (FastMCP).
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from db_models import (
    AppointmentModel,
    ClinicBranchModel,
    PractitionerModel,
    get_db_engine,
    init_db,
)

mcp_scheduling = FastMCP(
    name="clinic-scheduling-server",
    instructions="Manages clinic rotas, doctor directory, 15-minute consultation slots, and booking state across Lahore and Islamabad."
)

engine = get_db_engine()
session_factory = init_db(engine)


@mcp_scheduling.tool()
def find_doctors(
    specialty: str,
    city: Optional[str] = None,
    branch_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Searches for certified doctors matching specialty and optional city or branch.

    Args:
        specialty: Clinical specialty (General Medicine, Paediatrics, Gynaecology, Cardiology, Dermatology, ENT).
        city: Optional city filter (Lahore, Islamabad).
        branch_id: Optional clinic branch identifier (e.g. BR_LHR_GULBERG).
    """
    session = session_factory()
    try:
        query = session.query(PractitionerModel).join(ClinicBranchModel)
        query = query.filter(PractitionerModel.specialty.ilike(f"%{specialty}%"))

        if city:
            query = query.filter(ClinicBranchModel.city.ilike(f"%{city}%"))
        if branch_id:
            query = query.filter(PractitionerModel.branch_id == branch_id)

        docs = query.all()
        return [
            {
                "doctor_id": d.id,
                "name": d.name,
                "specialty": d.specialty,
                "branch_name": d.branch.name if d.branch else "Main Clinic",
                "city": d.branch.city if d.branch else "Lahore",
                "qualification": d.qualification,
                "experience_years": d.experience_years,
                "consultation_fee_pkr": d.consultation_fee_pkr,
                "shift_hours": d.shift_hours,
                "available_days": d.available_days
            }
            for d in docs
        ]
    finally:
        session.close()


@mcp_scheduling.tool()
def get_doctor_slots(doctor_id: str, target_date: str) -> Dict[str, Any]:
    """Retrieves 15-minute consultation slots for a doctor on a specific date.

    Args:
        doctor_id: Doctor identifier (e.g. DOC_001).
        target_date: Target date formatted as YYYY-MM-DD.
    """
    session = session_factory()
    try:
        doc = session.query(PractitionerModel).filter_by(id=doctor_id).first()
        if not doc:
            return {"status": "ERROR", "message": f"Doctor '{doctor_id}' not found."}

        # Check existing bookings for that date
        existing_appts = session.query(AppointmentModel).filter(
            AppointmentModel.practitioner_id == doctor_id,
            AppointmentModel.slot_datetime.like(f"{target_date}%"),
            AppointmentModel.status.in_(["booked", "arrived"])
        ).all()

        booked_times = {a.slot_datetime.split(" ")[1] for a in existing_appts if " " in a.slot_datetime}

        # Generate standard 15-minute slots based on shift hours (e.g. 17:00 to 20:00)
        start_hour, end_hour = 17, 21
        if "-" in doc.shift_hours:
            try:
                parts = doc.shift_hours.split("-")
                start_hour = int(parts[0].split(":")[0])
                end_hour = int(parts[1].split(":")[0])
            except Exception:
                pass

        slots = []
        for h in range(start_hour, end_hour):
            for m in (0, 15, 30, 45):
                slot_time_str = f"{h:02d}:{m:02d}"
                full_slot_str = f"{target_date} {slot_time_str}"
                is_available = slot_time_str not in booked_times
                slots.append({
                    "slot_time": slot_time_str,
                    "slot_datetime": full_slot_str,
                    "is_available": is_available
                })

        return {
            "status": "SUCCESS",
            "doctor_id": doc.id,
            "doctor_name": doc.name,
            "specialty": doc.specialty,
            "date": target_date,
            "total_slots": len(slots),
            "available_slots": [s for s in slots if s["is_available"]]
        }
    finally:
        session.close()


@mcp_scheduling.tool()
def book_appointment(
    patient_id: str,
    doctor_id: str,
    slot_datetime: str,
    chief_complaint: str,
    urgency_tier: str = "ROUTINE"
) -> Dict[str, Any]:
    """Atomically books a consultation slot and issues a token number.

    Args:
        patient_id: Unique Patient ID.
        doctor_id: Selected Doctor ID.
        slot_datetime: Exact timestamp (e.g. '2026-10-15 17:30').
        chief_complaint: Primary intake symptom summary.
        urgency_tier: Urgency level (ROUTINE, URGENT).
    """
    session = session_factory()
    try:
        doc = session.query(PractitionerModel).filter_by(id=doctor_id).first()
        if not doc:
            return {"status": "ERROR", "message": f"Doctor '{doctor_id}' does not exist."}

        # Check slot collision
        collision = session.query(AppointmentModel).filter_by(
            practitioner_id=doctor_id,
            slot_datetime=slot_datetime,
            status="booked"
        ).first()

        if collision:
            return {
                "status": "SLOT_CONFLICT",
                "message": f"Slot {slot_datetime} with {doc.name} is already booked. Please pick another slot."
            }

        # Count tokens booked for doctor on that date to assign sequential token
        date_str = slot_datetime.split(" ")[0] if " " in slot_datetime else slot_datetime
        count_today = session.query(AppointmentModel).filter(
            AppointmentModel.practitioner_id == doctor_id,
            AppointmentModel.slot_datetime.like(f"{date_str}%")
        ).count()

        booking_id = f"APT_BK_{uuid.uuid4().hex[:8].upper()}"
        token_num = count_today + 1

        new_appt = AppointmentModel(
            id=booking_id,
            patient_id=patient_id,
            practitioner_id=doctor_id,
            branch_id=doc.branch_id,
            specialty=doc.specialty,
            slot_datetime=slot_datetime,
            status="booked",
            token_number=token_num,
            urgency_tier=urgency_tier,
            chief_complaint=chief_complaint,
            created_at=datetime.now(timezone.utc)
        )
        session.add(new_appt)
        session.commit()

        return {
            "status": "CONFIRMED",
            "booking_id": booking_id,
            "patient_id": patient_id,
            "doctor_name": doc.name,
            "specialty": doc.specialty,
            "branch": doc.branch.name if doc.branch else "City Care Clinic",
            "slot_datetime": slot_datetime,
            "token_number": token_num,
            "fee_pkr": doc.consultation_fee_pkr,
            "message": f"Appointment confirmed with {doc.name}. Token #{token_num} reserved."
        }
    finally:
        session.close()


@mcp_scheduling.tool()
def reschedule_appointment(appointment_id: str, new_slot_datetime: str) -> Dict[str, Any]:
    """Reschedules an active appointment to a new slot datetime.

    Args:
        appointment_id: Existing Appointment Booking ID.
        new_slot_datetime: New target timestamp (e.g. '2026-10-16 18:00').
    """
    session = session_factory()
    try:
        appt = session.query(AppointmentModel).filter_by(id=appointment_id).first()
        if not appt:
            return {"status": "NOT_FOUND", "message": f"Appointment '{appointment_id}' not found."}

        # Check collision on new slot
        collision = session.query(AppointmentModel).filter_by(
            practitioner_id=appt.practitioner_id,
            slot_datetime=new_slot_datetime,
            status="booked"
        ).first()

        if collision:
            return {"status": "COLLISION", "message": f"New slot {new_slot_datetime} is already booked."}

        old_slot = appt.slot_datetime
        appt.slot_datetime = new_slot_datetime
        appt.status = "rescheduled"
        session.commit()

        return {
            "status": "SUCCESS",
            "appointment_id": appt.id,
            "doctor_id": appt.practitioner_id,
            "old_slot": old_slot,
            "new_slot": new_slot_datetime,
            "message": f"Appointment {appointment_id} successfully rescheduled to {new_slot_datetime}."
        }
    finally:
        session.close()


@mcp_scheduling.tool()
def cancel_appointment(appointment_id: str, reason: str = "Patient Request") -> Dict[str, Any]:
    """Cancels an existing appointment slot.

    Args:
        appointment_id: Booking reference to cancel.
        reason: Justification for cancellation.
    """
    session = session_factory()
    try:
        appt = session.query(AppointmentModel).filter_by(id=appointment_id).first()
        if not appt:
            return {"status": "NOT_FOUND", "message": f"Appointment '{appointment_id}' not found."}

        appt.status = "cancelled"
        session.commit()

        return {
            "status": "CANCELLED",
            "appointment_id": appointment_id,
            "slot_freed": appt.slot_datetime,
            "reason": reason,
            "message": f"Appointment {appointment_id} has been cancelled and the slot released."
        }
    finally:
        session.close()


if __name__ == "__main__":
    mcp_scheduling.run()
