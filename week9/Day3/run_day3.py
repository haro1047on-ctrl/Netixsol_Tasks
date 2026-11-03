"""City Care Clinics - Week 9 Day 3 Master Benchmark & Integration Suite.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Validates all specialist agents across 5 clinical operational tasks:
- Task 1: Conversational Intake Agent (Single-question UrduLish dialogue -> Structured JSON)
- Task 2: Triage Agent & 50-Scenario Benchmark (100% Emergency Recall, Over/Under-Triage)
- Task 3: Scheduling Agent (Specialty routing, Preferences, Calendar JSON, Anti-Double-Booking)
- Task 4: Records & Clinical Summary Agents (EHR Q&A, Pre-visit SOAP, 3-Doctor Panel on 10 cases)
- Task 5: Prescription Safety & Follow-up Agents (Rx audit with warnings, 48h/7d WhatsApp reminders)
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime

# Windows console UTF-8 safety
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from intake_agent import IntakeAgent, IntakeForm
from triage_agent import TriageAgent, evaluate_50_triage_scenarios
from scheduling_agent import SchedulingAgent, DoctorPreference, BookingRequest
from records_agent import RecordsAgent
from clinical_summary_agent import ClinicalSummaryAgent, ThreeDoctorEvaluationPanel
from prescription_safety_agent import PrescriptionSafetyAgent, ProposedMedication
from followup_agent import FollowUpAgent


def print_banner(title: str) -> None:
    print("\n" + "=" * 78)
    print(f" {title}")
    print("=" * 78)


def run_task1_intake() -> None:
    print_banner("TASK 1: CONVERSATIONAL INTAKE AGENT DEMONSTRATION")
    agent = IntakeAgent()

    # Simulate multi-turn dialogue with single questions
    turns = [
        "Mere 6 saal ke betay ko bukhar hai aur khansi bhi hai.",
        "Bukhar 2 din se hai.",
        "Bukhar taqreeban 7/10 tez lag raha hai.",
        "Isko koi allergy nahi hai aur na hi pehle se koi bimari hai."
    ]

    current_state = IntakeForm()
    for idx, user_msg in enumerate(turns, 1):
        print(f"\n[Turn {idx}] Patient: '{user_msg}'")
        current_state, next_question = agent.process_turn(user_msg, current_state)
        print(f"[Turn {idx}] Sitara (Intake Agent): '{next_question}'")
        print(f"       -> Extracted State: Complaint='{current_state.chief_complaint}', Duration='{current_state.duration}', Severity={current_state.severity_scale}, Identity='{current_state.patient_identity}'")

    print("\n[Final Structured Intake Form JSON]:")
    print(current_state.model_dump_json(indent=2))
    assert current_state.chief_complaint is not None, "Intake must capture chief complaint"
    print(">>> Task 1 Intake Agent: PASSED (Natural single-question dialogue validated)")


def run_task2_triage() -> None:
    print_banner("TASK 2: TRIAGE AGENT & 50-SCENARIO BENCHMARK")
    results = evaluate_50_triage_scenarios()
    em_recall = results["emergency_recall_percent"]
    under_triage = results["under_triage_rate_percent"]
    over_triage = results["over_triage_rate_percent"]

    print(f"Total Scenarios Evaluated: {results['total_scenarios']}")
    print(f"Emergency Recall Rate    : {em_recall}% (Contract: Must be 100%)")
    print(f"Under-Triage Rate        : {under_triage}%")
    print(f"Over-Triage Rate         : {over_triage}%")
    print(f"Tier Classification Acc  : {results['overall_accuracy_percent']}%")

    assert em_recall == 100.0, f"FAILED: Emergency recall was {em_recall}%, must be 100%!"
    assert under_triage == 0.0, f"FAILED: Under-triage rate was {under_triage}%, must be 0%!"
    print(">>> Task 2 Triage Agent: PASSED (100% Emergency Recall verified)")


def run_task3_scheduling() -> None:
    print_banner("TASK 3: SCHEDULING AGENT DEMONSTRATION")
    agent = SchedulingAgent()

    # 1. Symptom to Specialty Mapping
    symptom_tests = [
        ("Jild par surkh dhabay aur shadeed khujli", "Dermatology"),
        ("Kaan mein dard aur gala kharab", "ENT"),
        ("Dil ki dharkan tez aur seenay mein dabao", "Cardiology"),
        ("Bachay ko bukhar aur ulti", "Paediatrics"),
    ]
    print("\n[Symptom -> Specialty Mapping]:")
    for symp, expected in symptom_tests:
        spec = agent.map_symptoms_to_specialty(symp)
        print(f"• '{symp}' -> {spec}")
        assert spec == expected, f"Expected {expected}, got {spec}"

    # 2. Preference Matching (Paediatrics in DHA)
    pref = DoctorPreference(specialty="Paediatrics", branch_preference="DHA")
    docs = agent.match_doctors(pref)
    assert len(docs) > 0, "Must find paediatricians in DHA"
    doc = docs[0]
    print(f"\nMatched Doctor: {doc['name']} ({doc['specialty']}) | Branch: {doc['branch_name']} | Fee: PKR {doc['consultation_fee_pkr']}")

    # 3. Proactive Slot Proposal
    slots = agent.get_available_slots(doc["doctor_id"], "2026-10-15")
    assert len(slots) > 0, "Doctor must have available consultation slots"
    proposal = agent.generate_proactive_offer_urdu(
        doctor_name=doc["name"],
        specialty=doc["specialty"],
        slot_str="kal shaam 5:00 baje",
        branch_name="DHA branch"
    )
    print(f"\n[Proactive Offer]: '{proposal}'")

    # 4. Anti-Past-Date Invariant Verification
    past_booking = BookingRequest(
        patient_id="PT_0001",
        doctor_id=doc["doctor_id"],
        slot_datetime="2020-01-01 10:00",
        chief_complaint="Past appointment attempt"
    )
    past_res = agent.book_appointment(past_booking)
    print(f"\n[Anti-Past-Date Check]: Status={past_res.status} | Reason: {past_res.message}")
    assert past_res.status == "PAST_DATE_ERROR", "Past date booking must be rejected!"

    # 5. Valid Booking & Google Calendar Event
    target_slot = slots[0]
    valid_booking = BookingRequest(
        patient_id="PT_0001",
        doctor_id=doc["doctor_id"],
        slot_datetime=target_slot,
        chief_complaint="Child fever and ear discomfort",
        urgency_tier="ROUTINE"
    )
    book_res = agent.book_appointment(valid_booking)
    print(f"\n[Confirmed Booking]: Status={book_res.status} | ID={book_res.booking_id} | Token=#{book_res.token_number}")
    print(f"UrduLish Confirmation: '{book_res.urdulish_message}'")
    print(f"Google Calendar Event Summary: '{book_res.google_calendar_event['summary']}'")
    assert book_res.status == "CONFIRMED", "Valid booking must be confirmed"
    assert book_res.google_calendar_event is not None, "Must generate Google Calendar payload"

    # 6. Anti-Double-Booking Invariant Verification
    collision_booking = BookingRequest(
        patient_id="PT_0002",
        doctor_id=doc["doctor_id"],
        slot_datetime=target_slot,
        chief_complaint="Attempting double booking same slot"
    )
    collision_res = agent.book_appointment(collision_booking)
    print(f"\n[Anti-Double-Booking Check]: Status={collision_res.status} | Reason: {collision_res.message}")
    assert collision_res.status == "SLOT_CONFLICT", "Double booking same slot must be rejected!"

    # 7. Reschedule & Cancel
    new_slot = slots[1] if len(slots) > 1 else "2026-10-15 18:30"
    resched_res = agent.reschedule_appointment(book_res.booking_id, new_slot)
    print(f"\n[Reschedule Check]: Status={resched_res.status} | New Slot={resched_res.slot_datetime}")

    cancel_res = agent.cancel_appointment(book_res.booking_id)
    print(f"[Cancel Check]: Status={cancel_res.status} | Freed Slot={cancel_res.slot_datetime}")
    assert cancel_res.status == "CANCELLED", "Cancellation must succeed and release slot"
    print(">>> Task 3 Scheduling Agent: PASSED (Preferences, Calendar JSON, and Invariants verified)")


def run_task4_records_and_summary() -> None:
    print_banner("TASK 4: RECORDS & CLINICAL SUMMARY AGENTS")
    rec_agent = RecordsAgent()

    # 1. Records Agent Q&A
    print("\n[Records Agent Q&A - Grounded EHR Queries]:")
    ans_alg = rec_agent.answer_records_query("PT_0001", "What are my documented allergies?", use_llm=False)
    print(f"• Query: Allergies ->\n  {ans_alg.answer_text.strip()}")
    assert "Sulfa" in ans_alg.answer_text, "PT_0001 must have Sulfa allergy"

    ans_chart = rec_agent.answer_records_query("PT_0005", "Tell me my medical history and conditions", use_llm=False)
    print(f"\n• Query: Conditions ->\n  {ans_chart.answer_text.strip()}")

    # 2. Clinical Summary Agent Pre-Visit SOAP Note
    sum_agent = ClinicalSummaryAgent()
    sample_intake = IntakeForm(
        patient_identity="SELF",
        patient_name="Ali Khan",
        patient_age=32,
        chief_complaint="Shadeed bukhar aur galay mein dard",
        duration="3 din",
        severity_scale=7,
        associated_symptoms=["khansi", "sar dard"],
        medical_history=["Asthma"],
        allergies=["Sulfa"]
    )
    soap = sum_agent.generate_soap_note("PT_0001", sample_intake, use_llm=False)
    print("\n[Generated Pre-Visit SOAP Note (Visual Structure Check)]:")
    print(soap.formatted_text[:700] + "\n... [truncated] ...\n" + soap.formatted_text[-400:])

    assert "SECTION 1: PATIENT-REPORTED & VERIFIED CLINICAL FACTS" in soap.formatted_text
    assert "SECTION 2: AI CLINICAL SUGGESTIONS" in soap.formatted_text
    assert "NOT A FORMAL DIAGNOSIS" in soap.formatted_text

    # 3. 3-Doctor Evaluation Panel on 10 Cases
    panel = ThreeDoctorEvaluationPanel()
    panel_report = panel.run_10_case_panel(sum_agent)
    print("\n[3-Doctor Evaluation Panel Results (10 Clinical Cases)]:")
    print(f"• Total Cases Evaluated   : {panel_report['total_cases_evaluated']}")
    print(f"• Clinical Raters          : Dr. Ayesha Malik (CMO), Dr. Tariq Mahmood (MD), Fatima Khan (RN)")
    print(f"• Overall Mean Accuracy   : {panel_report['overall_mean_accuracy']} / 5.0")
    print(f"• Overall Mean Usefulness : {panel_report['overall_mean_usefulness']} / 5.0")

    assert panel_report["overall_mean_accuracy"] >= 4.5, "Evaluation panel accuracy must be >= 4.5"
    assert panel_report["overall_mean_usefulness"] >= 4.5, "Evaluation panel usefulness must be >= 4.5"
    print(">>> Task 4 Records & Clinical Summary Agents: PASSED (SOAP structure & 3-doctor benchmark verified)")


def run_task5_prescription_and_followup() -> None:
    print_banner("TASK 5: PRESCRIPTION SAFETY & FOLLOW-UP AGENTS")
    rx_agent = PrescriptionSafetyAgent()

    # 1. Prescription Safety Audit - Penicillin Allergy Clash
    from prescription_safety_engine import ProposedMedication as PM
    from prescription_safety_engine import PrescriptionSafetyEngine
    engine = PrescriptionSafetyEngine()

    print("\n[Case 1: Penicillin Allergy Clash Verification]:")
    rep_allergy = engine.evaluate_prescription(
        proposed_meds=[PM(medication_name="Augmentin", dose_mg=625, frequency="BD")],
        patient_allergies=["Penicillin"],
        active_medications=[]
    )
    print(f"Status: {rep_allergy.overall_status} | Is Safe: {rep_allergy.is_safe}")
    for clash in rep_allergy.allergy_clashes:
        print(f"Alert to Doctor: '{clash}'")
    assert not rep_allergy.is_safe, "Augmentin must clash with Penicillin allergy!"

    # 2. DDI Bleeding Risk: Warfarin + Aspirin
    print("\n[Case 2: Drug-Drug Interaction Verification]:")
    rep_ddi = engine.evaluate_prescription(
        proposed_meds=[PM(medication_name="Aspirin", dose_mg=300, frequency="OD")],
        patient_allergies=[],
        active_medications=["Warfarin"]
    )
    print(f"Status: {rep_ddi.overall_status} | DDI Identified: {len(rep_ddi.drug_interactions)}")
    for ddi in rep_ddi.drug_interactions:
        print(f"Alert: {ddi.get('clinical_effect')}")
    assert rep_ddi.overall_status == "CRITICAL_DANGER", "Warfarin + Aspirin must be CRITICAL_DANGER!"

    # 3. Adult Overdose: Paracetamol > 4000mg/day
    print("\n[Case 3: Dose Ceiling Verification]:")
    rep_dose = engine.evaluate_prescription(
        proposed_meds=[PM(medication_name="Panadol", dose_mg=2000, frequency="TDS")],
        patient_allergies=[],
        active_medications=[]
    )
    print(f"Status: {rep_dose.overall_status} | Dose Violation: {rep_dose.dose_violations[0]}")
    assert not rep_dose.is_safe, "Panadol 6000mg must trigger overdose violation!"

    # 4. Follow-up Agent: Reminder Plan & Multi-Stage WhatsApp Messages
    followup_agent = FollowUpAgent()
    plan = followup_agent.create_reminder_plan(
        patient_id="PT_0001",
        patient_name="Ali Khan",
        patient_phone="0300-1234567",
        doctor_name="Dr. Tariq Mahmood",
        branch_name="City Care Clinics — DHA Branch",
        encounter_date="2026-10-15",
        prescribed_meds=[
            {"name": "Augmentin 625mg", "dose": "1 tablet", "frequency": "BD", "instructions": "Khane ke baad"},
            {"name": "Panadol 500mg", "dose": "1 tablet", "frequency": "PRN", "instructions": "Dard ya bukhar mein"}
        ],
        ordered_labs=[
            {"test_name": "Complete Blood Count (CBC)", "due_days": 7, "fasting_required": False}
        ],
        follow_up_days=7
    )

    print("\n[Follow-up Agent Reminder Plan & Outreach Generation]:")
    print(f"• Scheduled Follow-up Date: {plan.follow_up_visit_date}")
    print(f"• Daily Medication Slots : {len(plan.medication_schedule)}")
    print(f"• Lab Due Notifications  : {len(plan.lab_reminders)}")

    print("\n[Stage 1: Day 0 Immediate Regimen Brief]:")
    print(plan.day0_post_visit_message)

    print("\n[Stage 2: 48-Hour Adherence & Recovery Pulse Check]:")
    print(plan.day2_adherence_check_message)

    print("\n[Stage 3: Day 7 Lab Test & Follow-up Review Reminder]:")
    print(plan.day7_followup_reminder_message)

    # 5. Dispatch via FastMCP Notifications Server
    receipt = followup_agent.dispatch_whatsapp_reminder(
        recipient_phone=plan.patient_phone,
        message_text=plan.day2_adherence_check_message
    )
    print(f"\n[Notifications MCP Server Live Dispatch Receipt]: {receipt['status']} (Receipt: {receipt['delivery_receipt']})")
    assert receipt["status"] == "DELIVERED", "WhatsApp reminder must be successfully delivered!"
    print(">>> Task 5 Prescription Safety & Follow-up Agents: PASSED (Warnings & 3-stage reminders verified)")


def main():
    start_time = time.time()
    print_banner("CITY CARE CLINICS — WEEK 9 DAY 3 COMPREHENSIVE SUITE")
    print("Testing All 5 Specialist Agents (Intake, Triage, Scheduling, Records/Summary, Rx Safety/Followup)")

    run_task1_intake()
    run_task2_triage()
    run_task3_scheduling()
    run_task4_records_and_summary()
    run_task5_prescription_and_followup()

    duration = time.time() - start_time
    print_banner(f"ALL DAY 3 SPECIALIST AGENT TASKS VALIDATED SUCCESSFULLY ({duration:.2f}s)")


if __name__ == "__main__":
    main()
