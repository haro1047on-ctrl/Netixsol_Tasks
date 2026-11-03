"""City Care Clinics - Medical Safety, Emergency Triage, and HITL Tests.

Tests:
- Test G: Emergency red-flag detection and immediate short-circuit (100% emergency recall)
- Test I: Human-in-the-Loop doctor approval workflow (persisted in DB, holding message, physician release)
- Pharmacological safety audits (penicillin allergy clash, drug interactions)
"""
import uuid
import pytest
from triage_agent import TriageAgent
from supervisor_graph import ClinicSupervisorOrchestrator
from prescription_safety_engine import PrescriptionSafetyEngine, ProposedMedication
from hitl_manager import get_hitl_manager


def test_emergency_short_circuit_myocardial_infarction():
    """Test G: Severe chest pain radiating to arm immediately short-circuits to emergency protocol."""
    orch = ClinicSupervisorOrchestrator(fast_eval_mode=False)

    msg = "Mere seenay mein shadeed dard hai aur ultay baazu mein khichaao hai"
    turn_res = orch.run_turn(
        thread_id=f"test_er_{uuid.uuid4().hex[:6]}",
        user_message=msg,
        fast_eval_mode=False
    )

    assert turn_res.get("is_emergency") is True
    assert turn_res.get("urgency_tier") == "EMERGENCY"
    # Ensure routine appointment was NOT booked
    assert turn_res.get("appointment_booking") is None or turn_res.get("appointment_booking", {}).get("status") != "CONFIRMED"
    # Ensure emergency escalation instructions are returned
    resp = turn_res.get("final_patient_response", "")
    assert ("emergency" in resp.lower() or "1122" in resp or "fori" in resp.lower() or "khatarnaak" in resp.lower())


def test_emergency_short_circuit_acute_stroke_fast():
    """Test G: Acute stroke signs (facial drooping, slurred speech) trigger immediate emergency alert."""
    triage = TriageAgent()
    res = triage.evaluate_symptoms(
        symptom_text="Mere walid ka munh achanak tedha ho gaya hai aur aawaz ladkhara rahi hai"
    )
    assert res.is_emergency is True
    assert res.urgency_tier == "EMERGENCY"
    assert res.matched_specialty in ("Emergency Medicine", "General Medicine")
    assert res.confidence_score == 1.0


def test_doctor_hitl_approval_workflow(hitl_manager_fixture):
    """Test I: Clinical draft creates pending DB record, and physician approval releases it."""
    req = hitl_manager_fixture.create_request(
        thread_id="test_th_hitl_1",
        patient_id="PT_0001",
        patient_name="Ali Khan",
        category="LAB_RESULT_EXPLANATION",
        reason="Elevated HbA1c explanation requires attending physician sign-off",
        draft_message="Aapka HbA1c 8.5% hai jo ke uncontrolled diabetes ki taraf ishara karta hai.",
        clinical_context={"test": "HbA1c", "value": 8.5}
    )

    assert req.status == "PENDING"
    req_id = req.request_id

    # Verify item is in list_pending
    pending = hitl_manager_fixture.list_pending()
    assert any(p.request_id == req_id for p in pending)

    # Doctor reviews and edits
    edited_text = "Aapka HbA1c 8.5% hai. Doctor se clinic mein mashwara zaroori hai."
    res_edit = hitl_manager_fixture.edit_and_approve(
        request_id=req_id,
        doctor_name="Dr. Tariq Mahmood",
        edited_message=edited_text,
        clinical_notes="Adjusted tone to avoid patient anxiety"
    )

    assert res_edit.status == "EDITED"
    assert res_edit.doctor_edited_message == edited_text
    assert res_edit.reviewing_doctor == "Dr. Tariq Mahmood"

    # Verify no longer in pending list
    updated_pending = hitl_manager_fixture.list_pending()
    assert not any(p.request_id == req_id for p in updated_pending)


def test_prescription_safety_allergy_conflict():
    """Validates that penicillin-allergic patients are protected from Augmentin."""
    rx_engine = PrescriptionSafetyEngine()

    proposed = [
        ProposedMedication(medication_name="Augmentin", dose_mg=625, frequency="BD")
    ]
    report = rx_engine.evaluate_prescription(
        proposed_meds=proposed,
        patient_allergies=["Penicillin"],
        active_medications=[],
        patient_age=35,
        is_pregnant=False
    )

    assert not report.is_safe
    assert len(report.allergy_clashes) > 0
    assert any("penicillin" in c.lower() or "augmentin" in c.lower() for c in report.allergy_clashes)
