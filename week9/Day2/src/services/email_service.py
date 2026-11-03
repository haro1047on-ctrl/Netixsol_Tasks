"""City Care Clinics - Email Service.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Delivers production-grade appointment confirmations, reminders, cancellations,
and clinical summaries via standard SMTP with HTML and plain-text templates.
Records every delivery attempt persistently in NotificationModel.
"""
from __future__ import annotations

import email.utils
import html
import logging
import os
import smtplib
import sys
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

# Setup path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
WEEK9_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
DAY5_SRC = os.path.join(WEEK9_DIR, "Day5", "src")
for p in [SRC_DIR, DAY2_SRC, DAY5_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from db_models import NotificationModel, init_db, get_db_engine

logger = logging.getLogger("citycare.email_service")


class EmailTemplateRenderer:
    """Renders responsive HTML and fallback plain-text email templates."""

    HEADER_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>City Care Clinics</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #1e293b; }
        .container { max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }
        .header { background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%); padding: 28px 24px; text-align: center; color: #ffffff; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
        .header p { margin: 6px 0 0; font-size: 14px; opacity: 0.9; }
        .body { padding: 32px 28px; line-height: 1.6; }
        .badge { display: inline-block; padding: 6px 14px; border-radius: 9999px; font-size: 13px; font-weight: 600; text-transform: uppercase; margin-bottom: 16px; }
        .badge-confirmed { background: #dcfce7; color: #166534; }
        .badge-rescheduled { background: #fef3c7; color: #92400e; }
        .badge-cancelled { background: #fee2e2; color: #991b1b; }
        .badge-reminder { background: #e0e7ff; color: #3730a3; }
        .card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px 20px; margin: 20px 0; }
        .row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #e2e8f0; }
        .row:last-child { border-bottom: none; }
        .label { font-weight: 600; color: #64748b; font-size: 14px; }
        .val { font-weight: 700; color: #0f172a; font-size: 14px; text-align: right; }
        .notice { background: #ecfdf5; border-left: 4px solid #10b981; padding: 12px 16px; border-radius: 4px; font-size: 13px; color: #065f46; margin: 18px 0; }
        .warning { background: #fffbeb; border-left: 4px solid #f59e0b; padding: 12px 16px; border-radius: 4px; font-size: 13px; color: #92400e; margin: 18px 0; }
        .footer { background: #f1f5f9; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }
        .footer a { color: #0d9488; text-decoration: none; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>City Care Clinics</h1>
        <p>Reliable Outpatient Healthcare &bull; Lahore &bull; Islamabad</p>
    </div>
    <div class="body">
"""

    FOOTER_HTML = """
    </div>
    <div class="footer">
        <p>City Care Clinics &bull; 24/7 Helpline: <strong>042-111-CARE (2273)</strong></p>
        <p>This is an automated notification from City Care Clinics Multi-Agent Healthcare Assistant.</p>
        <p>Please do not reply directly to this email.</p>
    </div>
</div>
</body>
</html>
"""

    @classmethod
    def render_booking_confirmation(
        cls,
        patient_name: str,
        doctor_name: str,
        specialty: str,
        branch_name: str,
        slot_iso: str,
        fee_pkr: int = 2500,
        instructions: Optional[str] = None
    ) -> tuple[str, str]:
        """Returns (html_content, plain_text_content)."""
        safe_patient = html.escape(patient_name)
        safe_doctor = html.escape(doctor_name)
        safe_specialty = html.escape(specialty)
        safe_branch = html.escape(branch_name)
        safe_slot = html.escape(slot_iso)
        instructions_block = (
            f'<div class="notice"><strong>Patient Preparation:</strong> {html.escape(instructions)}</div>'
            if instructions else ""
        )

        html_body = f"""{cls.HEADER_HTML}
        <span class="badge badge-confirmed">Appointment Confirmed</span>
        <h2>Assalam-o-Alaikum, {safe_patient}</h2>
        <p>Your clinic consultation has been successfully booked with City Care Clinics. Here are your appointment details:</p>
        
        <div class="card">
            <div class="row"><span class="label">Consulting Doctor:</span><span class="val">{safe_doctor}</span></div>
            <div class="row"><span class="label">Specialty:</span><span class="val">{safe_specialty}</span></div>
            <div class="row"><span class="label">Clinic Branch:</span><span class="val">{safe_branch}</span></div>
            <div class="row"><span class="label">Date & Time:</span><span class="val">{safe_slot}</span></div>
            <div class="row"><span class="label">Consultation Fee:</span><span class="val">PKR {fee_pkr:,}</span></div>
        </div>
        
        {instructions_block}
        
        <p>Please arrive at the clinic <strong>10 minutes prior</strong> to your scheduled slot for registration and vitals check.</p>
        {cls.FOOTER_HTML}"""

        text_body = (
            f"City Care Clinics - Appointment Confirmed\n\n"
            f"Assalam-o-Alaikum {patient_name},\n"
            f"Your appointment has been confirmed with {doctor_name} ({specialty}).\n"
            f"Branch: {branch_name}\n"
            f"Slot: {slot_iso}\n"
            f"Fee: PKR {fee_pkr:,}\n"
            f"{'Instructions: ' + instructions if instructions else ''}\n"
            f"Please arrive 10 minutes before your slot.\n"
            f"Helpline: 042-111-2273"
        )
        return html_body, text_body

    @classmethod
    def render_reschedule_notice(
        cls,
        patient_name: str,
        doctor_name: str,
        old_slot_iso: str,
        new_slot_iso: str,
        branch_name: str
    ) -> tuple[str, str]:
        html_body = f"""{cls.HEADER_HTML}
        <span class="badge badge-rescheduled">Appointment Rescheduled</span>
        <h2>Assalam-o-Alaikum, {html.escape(patient_name)}</h2>
        <p>Your appointment has been successfully rescheduled as requested:</p>
        
        <div class="card">
            <div class="row"><span class="label">Consulting Doctor:</span><span class="val">{html.escape(doctor_name)}</span></div>
            <div class="row"><span class="label">Clinic Branch:</span><span class="val">{html.escape(branch_name)}</span></div>
            <div class="row"><span class="label">Previous Slot:</span><span class="val" style="text-decoration: line-through; color: #94a3b8;">{html.escape(old_slot_iso)}</span></div>
            <div class="row"><span class="label">New Confirmed Slot:</span><span class="val" style="color: #0f766e;">{html.escape(new_slot_iso)}</span></div>
        </div>
        
        <p>Your previous slot has been released. Please arrive 10 minutes before your new appointment time.</p>
        {cls.FOOTER_HTML}"""

        text_body = (
            f"City Care Clinics - Appointment Rescheduled\n\n"
            f"Assalam-o-Alaikum {patient_name},\n"
            f"Your appointment with {doctor_name} at {branch_name} has been rescheduled.\n"
            f"Old Slot: {old_slot_iso}\n"
            f"New Confirmed Slot: {new_slot_iso}\n"
            f"Helpline: 042-111-2273"
        )
        return html_body, text_body

    @classmethod
    def render_cancellation_notice(
        cls,
        patient_name: str,
        doctor_name: str,
        slot_iso: str,
        reason: Optional[str] = None
    ) -> tuple[str, str]:
        safe_reason = html.escape(reason or "Cancelled per patient request")
        html_body = f"""{cls.HEADER_HTML}
        <span class="badge badge-cancelled">Appointment Cancelled</span>
        <h2>Assalam-o-Alaikum, {html.escape(patient_name)}</h2>
        <p>Your appointment has been cancelled:</p>
        
        <div class="card">
            <div class="row"><span class="label">Consulting Doctor:</span><span class="val">{html.escape(doctor_name)}</span></div>
            <div class="row"><span class="label">Cancelled Slot:</span><span class="val">{html.escape(slot_iso)}</span></div>
            <div class="row"><span class="label">Reason:</span><span class="val">{safe_reason}</span></div>
        </div>
        
        <p>If you wish to re-book at any time, please visit our online portal or contact our 24/7 reception desk.</p>
        {cls.FOOTER_HTML}"""

        text_body = (
            f"City Care Clinics - Appointment Cancelled\n\n"
            f"Assalam-o-Alaikum {patient_name},\n"
            f"Your appointment with {doctor_name} scheduled for {slot_iso} has been cancelled.\n"
            f"Reason: {reason or 'Patient request'}\n"
            f"To book a new appointment, contact 042-111-2273."
        )
        return html_body, text_body

    @classmethod
    def render_reminder(
        cls,
        patient_name: str,
        doctor_name: str,
        slot_iso: str,
        branch_name: str,
        reminder_lead: str = "Upcoming"
    ) -> tuple[str, str]:
        html_body = f"""{cls.HEADER_HTML}
        <span class="badge badge-reminder">{html.escape(reminder_lead)} Appointment Reminder</span>
        <h2>Assalam-o-Alaikum, {html.escape(patient_name)}</h2>
        <p>This is a friendly reminder for your upcoming doctor consultation:</p>
        
        <div class="card">
            <div class="row"><span class="label">Doctor:</span><span class="val">{html.escape(doctor_name)}</span></div>
            <div class="row"><span class="label">Clinic Branch:</span><span class="val">{html.escape(branch_name)}</span></div>
            <div class="row"><span class="label">Scheduled Time:</span><span class="val">{html.escape(slot_iso)}</span></div>
        </div>
        
        <div class="warning">
            <strong>Checklist:</strong> Please bring your CNIC, past prescriptions, and recent lab reports.
        </div>
        {cls.FOOTER_HTML}"""

        text_body = (
            f"City Care Clinics - {reminder_lead} Reminder\n\n"
            f"Assalam-o-Alaikum {patient_name},\n"
            f"Reminder: You have a consultation with {doctor_name} at {branch_name} on {slot_iso}.\n"
            f"Please bring your CNIC and previous medical records.\n"
            f"Helpline: 042-111-2273"
        )
        return html_body, text_body


class EmailService:
    """Production-grade SMTP Email Delivery with Database Audit Trail."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or init_db()
        self.host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
        self.username = os.getenv("SMTP_USERNAME", "")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", "noreply@citycareclinics.pk")
        self.app_env = os.getenv("APP_ENV", "development").lower()

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        patient_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
        notification_type: str = "GENERAL",
        db_session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Dispatches an email via SMTP and records the attempt in NotificationModel.

        Returns:
            Dict containing status ('SENT' or 'FAILED'), notification_id, and details.
        """
        notification_id = f"NOTIF_{uuid.uuid4().hex[:10].upper()}"
        now_utc = datetime.now(timezone.utc)
        plain_content = body_text or "Please view this email in an HTML-compatible client."

        session_to_use = db_session or self.session_factory()
        should_close_session = db_session is None

        # 1. Create Pending Notification Record in Database
        notif_record = NotificationModel(
            id=notification_id,
            patient_id=patient_id,
            appointment_id=appointment_id,
            channel="EMAIL",
            recipient=recipient_email,
            subject=subject,
            body=body_html,
            notification_type=notification_type,
            status="PENDING",
            scheduled_for=now_utc,
            created_at=now_utc
        )
        try:
            session_to_use.add(notif_record)
            session_to_use.commit()
        except Exception as e:
            logger.error(f"Failed to record initial NotificationModel: {e}")
            session_to_use.rollback()

        # 2. Check Configuration
        is_configured = bool(self.host and self.username and self.password)

        if not is_configured:
            err_msg = (
                f"SMTP not configured (host={self.host}, user={'set' if self.username else 'empty'}). "
                f"Email dispatch aborted without silent simulation."
            )
            logger.warning(err_msg)
            try:
                notif_record.status = "FAILED"
                notif_record.error_message = err_msg
                session_to_use.commit()
            except Exception:
                session_to_use.rollback()
            finally:
                if should_close_session:
                    session_to_use.close()

            return {
                "status": "FAILED",
                "notification_id": notification_id,
                "channel": "EMAIL",
                "recipient": recipient_email,
                "subject": subject,
                "error": err_msg,
                "is_configured": False
            }

        # 3. Construct MIME Message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"City Care Clinics <{self.from_email}>"
        msg["To"] = recipient_email
        msg["Date"] = email.utils.formatdate(localtime=True)
        msg["Message-ID"] = email.utils.make_msgid(domain="citycareclinics.pk")

        msg.attach(MIMEText(plain_content, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        # 4. Attempt Real SMTP Transmission
        try:
            server = smtplib.SMTP(self.host, self.port, timeout=12)
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(self.from_email, [recipient_email], msg.as_string())
            server.quit()

            receipt_id = f"SMTP_250_OK_{uuid.uuid4().hex[:8].upper()}"
            notif_record.status = "SENT"
            notif_record.sent_at = datetime.now(timezone.utc)
            notif_record.provider_receipt = receipt_id
            session_to_use.commit()

            logger.info(f"Successfully sent email to {recipient_email} (Receipt: {receipt_id})")
            return {
                "status": "SENT",
                "notification_id": notification_id,
                "channel": "EMAIL",
                "recipient": recipient_email,
                "subject": subject,
                "provider_receipt": receipt_id,
                "sent_at": notif_record.sent_at.isoformat()
            }

        except Exception as exc:
            error_details = f"SMTP Transmission Error: {type(exc).__name__}: {str(exc)}"
            logger.error(f"Failed to send email to {recipient_email}: {error_details}")
            try:
                notif_record.status = "FAILED"
                notif_record.error_message = error_details
                session_to_use.commit()
            except Exception:
                session_to_use.rollback()

            return {
                "status": "FAILED",
                "notification_id": notification_id,
                "channel": "EMAIL",
                "recipient": recipient_email,
                "subject": subject,
                "error": error_details
            }
        finally:
            if should_close_session:
                session_to_use.close()


# Global Singleton Instance
_email_service_instance: Optional[EmailService] = None

def get_email_service() -> EmailService:
    global _email_service_instance
    if _email_service_instance is None:
        _email_service_instance = EmailService()
    return _email_service_instance
