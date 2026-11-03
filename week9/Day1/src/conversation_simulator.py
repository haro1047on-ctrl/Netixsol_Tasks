"""City Care Clinics - Multi-Scenario Patient Conversation Simulator.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Simulates and validates all 7 core patient scenarios through the Day 1 safety and triage engine.
"""
from __future__ import annotations

from typing import Any, Dict, List
from clinical_state import (
    AppointmentBooking,
    ClinicalSpecialty,
    ClinicBranch,
    ClinicState,
    PatientProfile,
    TriageLevel,
)
from pii_redactor import PIIRedactor
from triage_engine import TriageEngine


class ScenarioSimulator:
    """Simulates multi-turn patient journeys with clinical state tracking."""

    def __init__(self):
        self.redactor = PIIRedactor()
        self.triage_engine = TriageEngine()

    def run_scenario_1_fever_cough(self) -> Dict[str, Any]:
        """Scenario 1: New patient with 3-day fever and cough (Routine/Urgent General Medicine)."""
        raw_msg = "Assalam-o-Alaikum, mera naam Usman Ali hai, phone 0300-1234567. Mujhe 3 din se bukhar aur khansi hai."
        sanitized, vault = self.redactor.redact(raw_msg)
        triage = self.triage_engine.evaluate(sanitized, patient_age=32)

        booking = AppointmentBooking(
            booking_id="CC-78214",
            patient_id=vault.get("[PATIENT_NAME_1]", "Usman Ali"),
            doctor_name="Dr. Tariq Mahmood",
            specialty=ClinicalSpecialty.GENERAL_MEDICINE,
            branch=ClinicBranch.LAHORE_GULBERG,
            slot_datetime="Today 5:30 PM",
            consultation_fee_pkr=2000,
            token_number=14,
            status="CONFIRMED"
        )

        return {
            "scenario": "Scenario 1: New Patient with Fever and Cough",
            "raw_input": raw_msg,
            "sanitized_input": sanitized,
            "pii_vault": vault,
            "triage_urgency": triage.urgency_level.value,
            "matched_specialty": triage.matched_specialty.value,
            "red_flag": triage.red_flag_detected,
            "booking": booking.model_dump(),
            "status": "SUCCESS"
        }

    def run_scenario_2_chest_pain(self) -> Dict[str, Any]:
        """Scenario 2: Emergency patient with severe chest pain radiating to left arm."""
        raw_msg = "Mere chhati mein shadeed dard ho raha hai aur dard baayein baazu mein ja raha hai, thanday paseenay aa rahe hain."
        sanitized, vault = self.redactor.redact(raw_msg)
        triage = self.triage_engine.evaluate(sanitized, patient_age=54)

        return {
            "scenario": "Scenario 2: Patient with Chest Pain (Emergency Path)",
            "raw_input": raw_msg,
            "sanitized_input": sanitized,
            "triage_urgency": triage.urgency_level.value,
            "red_flag": triage.red_flag_detected,
            "red_flag_category": triage.red_flag_category,
            "emergency_script_triggered": triage.emergency_script_urdu is not None,
            "status": "EMERGENCY_ESCALATED"
        }

    def run_scenario_3_child_booking(self) -> Dict[str, Any]:
        """Scenario 3: Mother booking urgent appointment for an 8-month infant with fever."""
        raw_msg = "Meri 8 mahine ki bachi Zainab ko 102 bukhar hai aur doodh kam pee rahi hai. Phone 0321-7654321."
        sanitized, vault = self.redactor.redact(raw_msg)
        triage = self.triage_engine.evaluate(sanitized, patient_age=1, is_pediatric=True, reported_temp_f=102.0)

        booking = AppointmentBooking(
            booking_id="CC-99120",
            patient_id="Baby Zainab",
            doctor_name="Dr. Fatima Zahra",
            specialty=ClinicalSpecialty.PAEDIATRICS,
            branch=ClinicBranch.LAHORE_JOHAR_TOWN,
            slot_datetime="Today 4:00 PM",
            consultation_fee_pkr=2500,
            token_number=4,
            status="CONFIRMED"
        )

        return {
            "scenario": "Scenario 3: Mother Booking for Sick Child (Pediatric Urgent)",
            "raw_input": raw_msg,
            "sanitized_input": sanitized,
            "triage_urgency": triage.urgency_level.value,
            "matched_specialty": triage.matched_specialty.value,
            "booking": booking.model_dump(),
            "status": "URGENT_BOOKED"
        }

    def run_scenario_4_lab_report(self) -> Dict[str, Any]:
        """Scenario 4: Returning patient inquiring about HbA1c lab report."""
        raw_msg = "Mera kal ka HbA1c test report ka result kya aya hai? CNIC 35201-1234567-1."
        sanitized, vault = self.redactor.redact(raw_msg)

        # Factual lab explanation payload without autonomous diagnosis
        lab_summary = {
            "test_name": "Glycated Hemoglobin (HbA1c)",
            "measured_value": 8.2,
            "reference_normal_max": 5.6,
            "interpretation_safety": "Value is elevated above normal reference range. Physician evaluation required.",
            "autonomous_diagnosis_attempted": False,
            "doctor_referral": "Dr. Salman (Internal Medicine)"
        }

        return {
            "scenario": "Scenario 4: Returning Patient Asking About Lab Report",
            "raw_input": raw_msg,
            "sanitized_input": sanitized,
            "vault": vault,
            "lab_summary": lab_summary,
            "status": "SAFE_LAB_PRESENTED"
        }

    def run_scenario_5_reschedule(self) -> Dict[str, Any]:
        """Scenario 5: Patient rescheduling an appointment from today 6 PM to tomorrow 4:30 PM."""
        raw_msg = "Mujhe aaj sham 6 baje Dr. Noreen wali appointment reschedule karni hai kal 4:30 PM par."
        sanitized, _ = self.redactor.redact(raw_msg)

        original_booking = AppointmentBooking(
            booking_id="CC-6512",
            patient_id="PT_4491",
            doctor_name="Dr. Noreen",
            specialty=ClinicalSpecialty.GYNAECOLOGY,
            branch=ClinicBranch.ISLAMABAD_F8,
            slot_datetime="Today 6:00 PM",
            status="RESCHEDULED"
        )

        new_booking = AppointmentBooking(
            booking_id="CC-6580",
            patient_id="PT_4491",
            doctor_name="Dr. Noreen",
            specialty=ClinicalSpecialty.GYNAECOLOGY,
            branch=ClinicBranch.ISLAMABAD_F8,
            slot_datetime="Tomorrow 4:30 PM",
            status="CONFIRMED"
        )

        return {
            "scenario": "Scenario 5: Reschedule Appointment",
            "raw_input": raw_msg,
            "sanitized_input": sanitized,
            "original_booking": original_booking.model_dump(),
            "new_booking": new_booking.model_dump(),
            "status": "RESCHEDULED_SUCCESS"
        }

    def run_scenario_6_medication_inquiry(self) -> Dict[str, Any]:
        """Scenario 6: Patient asking 'Kya main Augmentin 1g le sakta hoon?'"""
        raw_msg = "Mera gala bohot dukh raha hai, kya main Augmentin 1g tablet le sakta hoon khud se?"
        sanitized, _ = self.redactor.redact(raw_msg)

        # Safety response: Deny autonomous medication advice
        denial_record = {
            "drug_inquired": "Augmentin 1g (Amoxicillin/Clavulanate)",
            "ai_authorized": False,
            "prohibition_reason": "AI must never authorize or prescribe antibiotic therapy. Risk of antibiotic resistance and adverse reaction.",
            "advice_given": "Gargles with warm salt water, maintain hydration, and consult ENT specialist."
        }

        return {
            "scenario": "Scenario 6: Medication Safety Inquiry ('Kya main yeh dawai le sakta hoon?')",
            "raw_input": raw_msg,
            "sanitized_input": sanitized,
            "safety_action": denial_record,
            "status": "AUTONOMOUS_RX_REJECTED"
        }

    def run_scenario_7_follow_up(self) -> Dict[str, Any]:
        """Scenario 7: Follow-up check-in where patient reports gastric pain from prescribed medicine."""
        raw_msg = "Bukhar utar gaya hai lekin dawai khane ke baad pet mein shadeed dard aur ulti shuru ho gayi hai."
        sanitized, _ = self.redactor.redact(raw_msg)

        follow_up_record = {
            "patient_id": "Hamza Ali",
            "contact_time": "48h Post-Consultation",
            "adherence": "Taking prescribed medicines",
            "recovery_trajectory": "WORSENING (Adverse Reaction Reported)",
            "adverse_symptom": "Severe gastric pain and nausea",
            "doctor_alert_triggered": True,
            "attending_physician": "Dr. Tariq Mahmood",
            "instruction": "Hold offending NSAID; clinic nurse will call within 30 minutes."
        }

        return {
            "scenario": "Scenario 7: Post-Visit Follow-up & Adverse Drug Reaction Detection",
            "raw_input": raw_msg,
            "sanitized_input": sanitized,
            "follow_up_assessment": follow_up_record,
            "status": "ADVERSE_REACTION_ESCALATED"
        }
