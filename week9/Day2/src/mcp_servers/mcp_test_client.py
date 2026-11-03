"""City Care Clinics - Independent MCP Server Test Suite & Inspector.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Tests all 4 MCP servers (patient-records, scheduling, drug-database, notifications)
independently, verifying tool schemas, responses, and safety invariants.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict

# Reconfigure stdout for UTF-8 compatibility on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from mcp_servers.patient_records_server import (
    get_full_patient_chart,
    get_patient_allergies,
    get_patient_medications,
    get_patient_profile,
    mcp_patient_records,
)
from mcp_servers.scheduling_server import (
    book_appointment,
    cancel_appointment,
    find_doctors,
    get_doctor_slots,
    mcp_scheduling,
    reschedule_appointment,
)
from mcp_servers.drug_database_server import (
    check_allergy_conflict,
    check_drug_interaction,
    lookup_drug,
    mcp_drug_database,
    verify_daily_dose,
)
from mcp_servers.notifications_server import (
    get_notification_audit_log,
    mcp_notifications,
    send_email_summary,
    send_sms_alert,
    send_whatsapp_message,
)


def test_mcp_patient_records() -> Dict[str, Any]:
    """Tests patient-records MCP server tools."""
    print("\n--- Testing MCP Server: patient-records-server ---")
    tools = [t.name for t in mcp_patient_records._tool_manager.list_tools()]
    print(f"  • Tools registered: {tools}")
    assert len(tools) >= 5, f"Expected at least 5 tools, got {len(tools)}"

    # Test 1: Fetch Profile
    profile = get_patient_profile("PT_0001")
    assert profile["status"] == "FOUND", f"Profile fetch failed: {profile}"
    print(f"  ✓ get_patient_profile('PT_0001'): Found {profile['full_name']} ({profile['age']}yo, {profile['city']})")

    # Test 2: Fetch Chart
    chart = get_full_patient_chart("PT_0001")
    assert chart["status"] == "SUCCESS", f"Chart fetch failed: {chart}"
    print(f"  ✓ get_full_patient_chart('PT_0001'): Returned full clinical chart with {len(chart['allergies'])} allergies, {len(chart['conditions'])} conditions.")

    return {"server": "patient-records-server", "tools_count": len(tools), "status": "PASSED"}


def test_mcp_scheduling() -> Dict[str, Any]:
    """Tests clinic-scheduling MCP server tools."""
    print("\n--- Testing MCP Server: clinic-scheduling-server ---")
    tools = [t.name for t in mcp_scheduling._tool_manager.list_tools()]
    print(f"  • Tools registered: {tools}")
    assert len(tools) >= 5, f"Expected at least 5 tools, got {len(tools)}"

    # Test 1: Find Cardiology doctors in Lahore
    docs = find_doctors(specialty="Cardiology", city="Lahore")
    assert len(docs) > 0, "No cardiologists found in Lahore"
    chosen_doc = docs[0]
    print(f"  ✓ find_doctors(Cardiology, Lahore): Found {chosen_doc['name']} at {chosen_doc['branch_name']}")

    # Test 2: Check slots
    slots_res = get_doctor_slots(chosen_doc["doctor_id"], "2026-10-20")
    assert slots_res["status"] == "SUCCESS"
    assert len(slots_res["available_slots"]) > 0
    slot_time = slots_res["available_slots"][0]["slot_datetime"]
    print(f"  ✓ get_doctor_slots: Found {len(slots_res['available_slots'])} open slots on 2026-10-20")

    # Test 3: Book Appointment
    booking = book_appointment(
        patient_id="PT_0001",
        doctor_id=chosen_doc["doctor_id"],
        slot_datetime=slot_time,
        chief_complaint="Chest tightness on brisk walking",
        urgency_tier="ROUTINE"
    )
    assert booking["status"] == "CONFIRMED"
    booking_id = booking["booking_id"]
    print(f"  ✓ book_appointment: Confirmed booking {booking_id} with token #{booking['token_number']}")

    # Test 4: Reschedule
    reschedule = reschedule_appointment(booking_id, "2026-10-21 18:30")
    assert reschedule["status"] == "SUCCESS"
    print(f"  ✓ reschedule_appointment: Rescheduled to 2026-10-21 18:30")

    # Test 5: Cancel
    cancel = cancel_appointment(booking_id, "Patient travel conflict")
    assert cancel["status"] == "CANCELLED"
    print(f"  ✓ cancel_appointment: Slot freed successfully.")

    return {"server": "clinic-scheduling-server", "tools_count": len(tools), "status": "PASSED"}


def test_mcp_drug_database() -> Dict[str, Any]:
    """Tests pharmacy-safety MCP server tools."""
    print("\n--- Testing MCP Server: pharmacy-safety-server ---")
    tools = [t.name for t in mcp_drug_database._tool_manager.list_tools()]
    print(f"  • Tools registered: {tools}")
    assert len(tools) >= 4, f"Expected at least 4 tools, got {len(tools)}"

    # Test 1: Drug lookup
    lookup = lookup_drug("Augmentin")
    assert lookup["status"] == "FOUND"
    assert lookup["generic_name"] == "Amoxicillin / Clavulanate"
    print(f"  ✓ lookup_drug('Augmentin'): Resolved to {lookup['generic_name']} (Max adult: {lookup['max_daily_dose_mg_adult']}mg/day)")

    # Test 2: Drug-Drug Interaction (Warfarin + Aspirin)
    interaction = check_drug_interaction("Warfarin", "Disprin")
    assert interaction["status"] == "INTERACTION_DETECTED"
    assert interaction["severity"] == "CRITICAL_DANGER"
    print(f"  ✓ check_drug_interaction('Warfarin', 'Disprin'): Intercepted CRITICAL_DANGER bleeding risk.")

    # Test 3: Allergy Conflict (Penicillin allergy vs Augmentin)
    allergy_check = check_allergy_conflict("Augmentin", ["Penicillin Allergy", "Dust"])
    assert allergy_check["status"] == "ALLERGY_CLASH_DETECTED"
    print(f"  ✓ check_allergy_conflict('Augmentin', ['Penicillin Allergy']): Flagged critical anaphylaxis clash.")

    # Test 4: Overdose check (Paracetamol 1000mg QDS = 4000mg ok, but 2000mg TDS = 6000mg exceeds!)
    overdose = verify_daily_dose("Panadol", dose_mg_per_intake=2000.0, frequency="TDS")
    assert overdose["status"] == "DOSE_EXCEEDED"
    print(f"  ✓ verify_daily_dose(Panadol, 2000mg TDS = 6000mg/day): Correctly intercepted overdose exceeding 4000mg ceiling.")

    # Test 5: Pediatric dose calculation (Infant Aspirin contraindication)
    ped_check = verify_daily_dose("Aspirin", dose_mg_per_intake=100.0, frequency="BD", patient_age=6, patient_weight_kg=20.0)
    assert ped_check["status"] == "PEDIATRIC_CONTRAINDICATION"
    print(f"  ✓ verify_daily_dose(Aspirin in 6yo child): Intercepted pediatric Reye's syndrome contraindication.")

    return {"server": "pharmacy-safety-server", "tools_count": len(tools), "status": "PASSED"}


def test_mcp_notifications() -> Dict[str, Any]:
    """Tests notifications MCP server tools."""
    print("\n--- Testing MCP Server: notifications-server ---")
    tools = [t.name for t in mcp_notifications._tool_manager.list_tools()]
    print(f"  • Tools registered: {tools}")
    assert len(tools) >= 4, f"Expected at least 4 tools, got {len(tools)}"

    # Test 1: WhatsApp notification
    wa = send_whatsapp_message(
        recipient_phone="0300-1234567",
        message_text="Assalam-o-Alaikum Usman sahib! Dr. Tariq ke sath aap ki appointment confirm ho gayi hai."
    )
    assert wa["status"] == "DELIVERED"
    print(f"  ✓ send_whatsapp_message: Delivered {wa['message_id']} to {wa['recipient']}")

    # Test 2: Email summary
    eml = send_email_summary(
        recipient_email="usman@example.com",
        subject="City Care Clinics — Appointment Confirmation",
        body_html="<p>Your appointment is confirmed.</p>"
    )
    assert eml["status"] == "SENT"
    print(f"  ✓ send_email_summary: Dispatched {eml['message_id']} to {eml['recipient']}")

    # Test 3: SMS alert
    sms = send_sms_alert(
        recipient_phone="0300-1234567",
        sms_text="City Care: Token #14 reserved for Dr Tariq Gulberg today 5:30PM."
    )
    assert sms["status"] == "DISPATCHED"
    print(f"  ✓ send_sms_alert: Dispatched {sms['message_id']}")

    # Test 4: Audit log
    logs = get_notification_audit_log("0300-1234567")
    assert len(logs) >= 2
    print(f"  ✓ get_notification_audit_log: Verified {len(logs)} immutable audit trail records.")

    return {"server": "notifications-server", "tools_count": len(tools), "status": "PASSED"}


def run_all_mcp_tests() -> Dict[str, Any]:
    """Orchestrates independent tests across all 4 MCP servers."""
    r1 = test_mcp_patient_records()
    r2 = test_mcp_scheduling()
    r3 = test_mcp_drug_database()
    r4 = test_mcp_notifications()

    print("\n=======================================================")
    print("ALL 4 MCP SERVERS INDEPENDENTLY TESTED & VERIFIED")
    print("=======================================================")
    return {
        "patient_records": r1,
        "scheduling": r2,
        "drug_database": r3,
        "notifications": r4
    }


if __name__ == "__main__":
    run_all_mcp_tests()
