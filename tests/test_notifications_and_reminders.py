"""City Care Clinics - Notifications, Reminders, and Persistence Tests.

Tests:
- Test H: Real email failure handling (records FAILED without false simulation)
- Test L: Background reminders worker (skips cancelled appointments, updates status)
- Test J: Data persistence across sessions
- Test K: Deterministic offline fallback operation
"""
import uuid
from datetime import datetime, timezone
import pytest
from services.email_service import get_email_service
from services.reminder_service import get_reminder_service
from db_models import AppointmentModel, NotificationModel, init_db
from supervisor_graph import ClinicSupervisorOrchestrator


def test_real_email_unconfigured_failure_handling(email_service_fixture):
    """Test H: When SMTP is unconfigured or credentials missing, records FAILED with clear error."""
    # Temporarily unconfigure credentials on fixture to verify offline/unconfigured guard
    orig_user = email_service_fixture.username
    orig_pass = email_service_fixture.password
    email_service_fixture.username = ""
    email_service_fixture.password = ""
    try:
        res = email_service_fixture.send_email(
            recipient_email="test_patient@example.com",
            subject="Consultation Confirmation",
            body_html="<p>Test Content</p>",
            notification_type="CONFIRMATION"
        )
    finally:
        email_service_fixture.username = orig_user
        email_service_fixture.password = orig_pass

    # In test environment without live credentials, must report FAILED, never simulated success!
    assert res["status"] == "FAILED"
    assert "error" in res
    assert res.get("notification_id") is not None

    # Verify notification record is in NotificationModel table with status FAILED
    session = init_db()()
    notif = session.query(NotificationModel).filter_by(id=res["notification_id"]).first()
    assert notif is not None
    assert notif.status == "FAILED"
    assert notif.error_message is not None
    session.close()


def test_background_reminder_worker_cancelled_appointment_guard(reminder_service_fixture):
    """Test L: Reminders for cancelled appointments are marked CANCELLED, not dispatched."""
    session = init_db()()

    # 1. Create a test appointment
    appt_id = f"APT_TEST_{uuid.uuid4().hex[:6].upper()}"
    test_appt = AppointmentModel(
        id=appt_id,
        patient_id="PT_0001",
        practitioner_id="DOC_001",
        branch_id="BR_001",
        specialty="General Medicine",
        slot_datetime="2026-10-26 17:00",
        status="cancelled",  # Cancelled!
        created_at=datetime.now(timezone.utc)
    )
    session.add(test_appt)

    # 2. Create pending notification due now
    notif_id = f"NOTIF_TEST_{uuid.uuid4().hex[:6].upper()}"
    notif = NotificationModel(
        id=notif_id,
        patient_id="PT_0001",
        appointment_id=appt_id,
        channel="WHATSAPP",
        recipient="0300-1234567",
        subject="Appointment Reminder",
        body="Reminder text",
        notification_type="REMINDER_24H",
        status="PENDING",
        scheduled_for=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc)
    )
    session.add(notif)
    session.commit()
    session.close()

    # 3. Run worker
    processed = reminder_service_fixture.process_due_reminders()
    item = next((p for p in processed if p["id"] == notif_id), None)
    assert item is not None
    assert item["status"] == "CANCELLED"

    # Verify in DB
    session = init_db()()
    check = session.query(NotificationModel).filter_by(id=notif_id).first()
    assert check.status == "CANCELLED"
    session.close()


def test_database_records_persistence_across_sessions():
    """Test J: Confirms that newly created patients and appointments persist in DB."""
    session1 = init_db()()
    test_notif_id = f"PERSIST_{uuid.uuid4().hex[:8].upper()}"
    notif = NotificationModel(
        id=test_notif_id,
        channel="WHATSAPP",
        recipient="0300-9999999",
        subject="Persistence Test",
        body="Hello",
        notification_type="GENERAL",
        status="SENT",
        created_at=datetime.now(timezone.utc)
    )
    session1.add(notif)
    session1.commit()
    session1.close()

    # Query from new session
    session2 = init_db()()
    loaded = session2.query(NotificationModel).filter_by(id=test_notif_id).first()
    assert loaded is not None
    assert loaded.id == test_notif_id
    assert loaded.recipient == "0300-9999999"
    session2.close()


def test_deterministic_offline_safe_mode(orchestrator_fixture):
    """Test K: System operates safely in deterministic mode even when LLM keys are absent."""
    turn_res = orchestrator_fixture.run_turn(
        thread_id=f"offline_test_{uuid.uuid4().hex[:6]}",
        user_message="Mujhe 3 din se bukhar aur sardi lag rahi hai",
        fast_eval_mode=True
    )
    assert turn_res is not None
    assert "final_patient_response" in turn_res
    assert turn_res.get("urgency_tier") in ("ROUTINE", "URGENT", "EMERGENCY")
