"""City Care Clinics - Appointment Scheduling Tests.

Tests:
- Test A: New patient routine booking flow (token allocation, GCal event, reminders)
- Test D: Anti-double-booking concurrency invariant
- Test E: Reschedule flow (slot reallocation, frees old slot, updates reminders)
- Test F: Cancellation flow (slot release, status update)
"""
import uuid
import pytest
from scheduling_agent import BookingRequest


def test_appointment_booking_and_token_allocation(scheduling_agent_fixture):
    """Test A: Books a new appointment, validates token generation and calendar event."""
    # Find free slot for DOC_001 on Monday
    date_str = "2026-10-26"
    slots = scheduling_agent_fixture.get_available_slots("DOC_001", date_str)
    assert len(slots) > 0, "Expected available slots for DOC_001"
    chosen_slot = slots[0]

    req = BookingRequest(
        patient_id="PT_0001",
        doctor_id="DOC_001",
        slot_datetime=chosen_slot,
        chief_complaint="Persistent dry cough",
        urgency_tier="ROUTINE"
    )
    result = scheduling_agent_fixture.book_appointment(req)
    assert result.status == "CONFIRMED"
    assert result.booking_id.startswith("APT_BK_")
    assert result.token_number > 0
    assert result.google_calendar_event is not None
    assert "status" in result.google_calendar_event
    assert result.fee_pkr == 2000


def test_anti_double_booking_invariant(scheduling_agent_fixture):
    """Test D: Re-booking an already confirmed slot must trigger a SLOT_CONFLICT."""
    date_str = "2026-10-26"
    slots = scheduling_agent_fixture.get_available_slots("DOC_002", date_str)
    assert len(slots) > 0
    target_slot = slots[0]

    # First booking: success
    req1 = BookingRequest(
        patient_id="PT_0001",
        doctor_id="DOC_002",
        slot_datetime=target_slot,
        chief_complaint="Checkup 1"
    )
    res1 = scheduling_agent_fixture.book_appointment(req1)
    assert res1.status == "CONFIRMED"

    # Second booking: must be rejected with conflict
    req2 = BookingRequest(
        patient_id="PT_0002",
        doctor_id="DOC_002",
        slot_datetime=target_slot,
        chief_complaint="Checkup 2"
    )
    res2 = scheduling_agent_fixture.book_appointment(req2)
    assert res2.status == "SLOT_CONFLICT"
    assert "already booked" in res2.message.lower()


def test_reschedule_appointment_flow(scheduling_agent_fixture):
    """Test E: Rescheduling moves appointment to new slot, frees old slot, maintains booked status."""
    date_str = "2026-10-27"
    slots = scheduling_agent_fixture.get_available_slots("DOC_003", date_str)
    assert len(slots) >= 2
    old_slot = slots[0]
    new_slot = slots[1]

    # Initial booking
    req = BookingRequest(
        patient_id="PT_0003",
        doctor_id="DOC_003",
        slot_datetime=old_slot,
        chief_complaint="Follow-up consultation"
    )
    res_initial = scheduling_agent_fixture.book_appointment(req)
    assert res_initial.status == "CONFIRMED"
    b_id = res_initial.booking_id

    # Reschedule to new slot
    res_reschedule = scheduling_agent_fixture.reschedule_appointment(b_id, new_slot)
    assert res_reschedule.status == "CONFIRMED"
    assert res_reschedule.slot_datetime == new_slot

    # Verify old slot is now freed up
    updated_slots = scheduling_agent_fixture.get_available_slots("DOC_003", date_str)
    assert old_slot in updated_slots, "Old slot must be freed after rescheduling"
    assert new_slot not in updated_slots, "New slot must be marked booked"


def test_cancel_appointment_flow(scheduling_agent_fixture):
    """Test F: Cancelling an appointment marks status cancelled and releases the slot."""
    date_str = "2026-10-28"
    slots = scheduling_agent_fixture.get_available_slots("DOC_004", date_str)
    assert len(slots) > 0
    slot_to_book = slots[0]

    # Book slot
    req = BookingRequest(
        patient_id="PT_0004",
        doctor_id="DOC_004",
        slot_datetime=slot_to_book,
        chief_complaint="Ear ache"
    )
    res_book = scheduling_agent_fixture.book_appointment(req)
    assert res_book.status == "CONFIRMED"
    b_id = res_book.booking_id

    # Verify slot is no longer in free slots
    slots_mid = scheduling_agent_fixture.get_available_slots("DOC_004", date_str)
    assert slot_to_book not in slots_mid

    # Cancel appointment
    res_cancel = scheduling_agent_fixture.cancel_appointment(b_id, reason="Patient recovered")
    assert res_cancel.status == "CANCELLED"

    # Verify slot is back in free slots
    slots_after = scheduling_agent_fixture.get_available_slots("DOC_004", date_str)
    assert slot_to_book in slots_after, "Cancelled slot must be returned to availability pool"
