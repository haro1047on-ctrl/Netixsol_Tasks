"""City Care Clinics - Persistent Reminders Service & Background Worker.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Replaces volatile in-memory queues with database-backed NotificationModel persistence.
Handles automated appointment reminders (24h and 2h lead time), cancelled appointment guards,
idempotent delivery, and background execution.
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

# Setup path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DAY4_SRC = os.path.dirname(CURRENT_DIR)
WEEK9_DIR = os.path.dirname(os.path.dirname(DAY4_SRC))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
DAY5_SRC = os.path.join(WEEK9_DIR, "Day5", "src")

for p in [DAY4_SRC, DAY2_SRC, DAY5_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from db_models import AppointmentModel, NotificationModel, PatientModel, PractitionerModel, init_db
from services.email_service import EmailTemplateRenderer, get_email_service
from mcp_servers.notifications_server import send_whatsapp_message, send_sms_alert

logger = logging.getLogger("citycare.reminders")


class ReminderService:
    """Database-backed persistent reminder scheduler and worker."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or init_db()
        self.email_service = get_email_service()

    def schedule_appointment_reminders(
        self,
        appointment_id: str,
        db_session: Optional[Session] = None
    ) -> List[Dict[str, Any]]:
        """Schedules 24-hour and 2-hour automated reminders for an appointment."""
        session = db_session or self.session_factory()
        should_close = db_session is None

        scheduled_entries = []
        try:
            appt = session.query(AppointmentModel).filter_by(id=appointment_id).first()
            if not appt or appt.status not in ["booked", "confirmed"]:
                return []

            patient = session.query(PatientModel).filter_by(id=appt.patient_id).first()
            doctor = session.query(PractitionerModel).filter_by(id=appt.practitioner_id).first()

            patient_name = patient.full_name if patient else "Valued Patient"
            doctor_name = doctor.name if doctor else "Specialist"
            branch_name = (doctor.branch.name if doctor and doctor.branch else "Main Clinic")
            slot_str = appt.slot_datetime  # "YYYY-MM-DD HH:MM"

            try:
                appt_dt = datetime.strptime(slot_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            except Exception:
                return []

            now_utc = datetime.now(timezone.utc)
            offsets = [
                ("REMINDER_24H", timedelta(hours=24), "24-Hour"),
                ("REMINDER_2H", timedelta(hours=2), "2-Hour")
            ]

            for notif_type, delta, lead_name in offsets:
                remind_time = appt_dt - delta
                # Only schedule if reminder time is in the future
                if remind_time > now_utc:
                    # Check if already scheduled
                    exists = session.query(NotificationModel).filter(
                        NotificationModel.appointment_id == appointment_id,
                        NotificationModel.notification_type == notif_type
                    ).first()

                    if not exists:
                        patient_email = getattr(patient, "email", None)
                        patient_phone = getattr(patient, "phone", None)

                        # Schedule Email if email exists
                        if patient and patient_email:
                            html_b, text_b = EmailTemplateRenderer.render_reminder(
                                patient_name=patient_name,
                                doctor_name=doctor_name,
                                slot_iso=slot_str,
                                branch_name=branch_name,
                                reminder_lead=lead_name
                            )
                            notif_email = NotificationModel(
                                id=f"NOTIF_REM_{uuid.uuid4().hex[:8].upper()}",
                                patient_id=patient.id,
                                appointment_id=appointment_id,
                                channel="EMAIL",
                                recipient=patient_email,
                                subject=f"Reminder: Appointment with {doctor_name} on {slot_str}",
                                body=html_b,
                                notification_type=notif_type,
                                status="PENDING",
                                scheduled_for=remind_time,
                                created_at=now_utc
                            )
                            session.add(notif_email)
                            scheduled_entries.append({"id": notif_email.id, "type": notif_type, "channel": "EMAIL"})

                        # Schedule WhatsApp if phone exists
                        if patient and patient_phone:
                            wa_msg = (
                                f"Assalam-o-Alaikum {patient_name}! Yeh City Care Clinics ki taraf se yaad-dihani hai: "
                                f"Aapki appointment {doctor_name} ke saath {slot_str} ko {branch_name} par scheduled hai. "
                                f"Barah-e-karam apna token slip aur puraani reports saath laayein. Helpline: 042-111-2273"
                            )
                            notif_wa = NotificationModel(
                                id=f"NOTIF_WA_{uuid.uuid4().hex[:8].upper()}",
                                patient_id=patient.id,
                                appointment_id=appointment_id,
                                channel="WHATSAPP",
                                recipient=patient_phone,
                                subject=f"WhatsApp {lead_name} Reminder",
                                body=wa_msg,
                                notification_type=notif_type,
                                status="PENDING",
                                scheduled_for=remind_time,
                                created_at=now_utc
                            )
                            session.add(notif_wa)
                            scheduled_entries.append({"id": notif_wa.id, "type": notif_type, "channel": "WHATSAPP"})

            session.commit()
            return scheduled_entries
        except Exception as e:
            logger.error(f"Error scheduling appointment reminders: {e}")
            session.rollback()
            return []
        finally:
            if should_close:
                session.close()

    def schedule_custom_reminder(
        self,
        recipient: str,
        channel: str,
        message_text: str,
        delay_hours: int,
        label: str,
        appointment_id: Optional[str] = None,
        patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Schedules a generic persistent reminder with a specified delay."""
        session = self.session_factory()
        now_utc = datetime.now(timezone.utc)
        remind_time = now_utc + timedelta(hours=delay_hours)
        notif_id = f"REM_{uuid.uuid4().hex[:8].upper()}"

        try:
            notif = NotificationModel(
                id=notif_id,
                patient_id=patient_id,
                appointment_id=appointment_id,
                channel=channel.upper(),
                recipient=recipient,
                subject=label,
                body=message_text,
                notification_type=label.upper().replace(" ", "_"),
                status="PENDING",
                scheduled_for=remind_time,
                created_at=now_utc
            )
            session.add(notif)
            session.commit()
            return {
                "schedule_id": notif_id,
                "recipient": recipient,
                "channel": channel,
                "delay_hours": delay_hours,
                "scheduled_for": remind_time.isoformat(),
                "label": label,
                "status": "QUEUED"
            }
        except Exception as e:
            logger.error(f"Failed to schedule custom reminder: {e}")
            session.rollback()
            return {"error": str(e), "status": "FAILED"}
        finally:
            session.close()

    def get_pending_due_reminders(self, db_session: Optional[Session] = None) -> List[NotificationModel]:
        """Returns all reminders scheduled for now or earlier that remain PENDING."""
        session = db_session or self.session_factory()
        now_utc = datetime.now(timezone.utc)
        return (
            session.query(NotificationModel)
            .filter(
                NotificationModel.status == "PENDING",
                NotificationModel.scheduled_for <= now_utc
            )
            .order_by(NotificationModel.scheduled_for.asc())
            .all()
        )

    def process_due_reminders(self, db_session: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Worker function: dispatches all pending due notifications and updates DB state."""
        session = db_session or self.session_factory()
        should_close = db_session is None

        processed = []
        try:
            now_utc = datetime.now(timezone.utc)
            due_records = (
                session.query(NotificationModel)
                .filter(
                    NotificationModel.status == "PENDING",
                    NotificationModel.scheduled_for <= now_utc
                )
                .all()
            )

            for rec in due_records:
                # 1. Check if associated appointment was cancelled
                if rec.appointment_id:
                    appt = session.query(AppointmentModel).filter_by(id=rec.appointment_id).first()
                    if appt and appt.status == "cancelled":
                        rec.status = "CANCELLED"
                        rec.error_message = "Appointment was cancelled before reminder was dispatched."
                        session.commit()
                        processed.append({
                            "id": rec.id,
                            "status": "CANCELLED",
                            "reason": "Appointment cancelled"
                        })
                        continue

                # 2. Mark PROCESSING
                rec.status = "PROCESSING"
                rec.retry_count = (rec.retry_count or 0) + 1
                session.commit()

                # 3. Channel dispatch
                try:
                    if rec.channel == "EMAIL":
                        res = self.email_service.send_email(
                            recipient_email=rec.recipient,
                            subject=rec.subject or "City Care Clinics Reminder",
                            body_html=rec.body,
                            patient_id=rec.patient_id,
                            appointment_id=rec.appointment_id,
                            notification_type=rec.notification_type,
                            db_session=session
                        )
                        delivery_status = res.get("status", "FAILED")
                        receipt = res.get("provider_receipt")
                        err = res.get("error")

                    elif rec.channel == "WHATSAPP":
                        res = send_whatsapp_message(
                            recipient_phone=rec.recipient,
                            message_text=rec.body
                        )
                        delivery_status = res.get("status", "DELIVERED")
                        receipt = res.get("message_id")
                        err = None

                    elif rec.channel == "SMS":
                        res = send_sms_alert(
                            recipient_phone=rec.recipient,
                            sms_text=rec.body
                        )
                        delivery_status = res.get("status", "DISPATCHED")
                        receipt = res.get("message_id")
                        err = None
                    else:
                        delivery_status = "FAILED"
                        receipt = None
                        err = f"Unknown notification channel '{rec.channel}'"

                    rec.status = "SENT" if delivery_status in ("SENT", "DELIVERED", "DISPATCHED") else "FAILED"
                    rec.sent_at = datetime.now(timezone.utc) if rec.status == "SENT" else None
                    rec.provider_receipt = receipt
                    rec.error_message = err
                    session.commit()

                    processed.append({
                        "id": rec.id,
                        "recipient": rec.recipient,
                        "channel": rec.channel,
                        "status": rec.status,
                        "receipt": receipt,
                        "error": err
                    })

                except Exception as dispatch_exc:
                    rec.status = "FAILED"
                    rec.error_message = str(dispatch_exc)
                    session.commit()
                    processed.append({
                        "id": rec.id,
                        "recipient": rec.recipient,
                        "channel": rec.channel,
                        "status": "FAILED",
                        "error": str(dispatch_exc)
                    })

            return processed
        finally:
            if should_close:
                session.close()


# Singleton Instance
_reminder_service_instance: Optional[ReminderService] = None

def get_reminder_service() -> ReminderService:
    global _reminder_service_instance
    if _reminder_service_instance is None:
        _reminder_service_instance = ReminderService()
    return _reminder_service_instance
