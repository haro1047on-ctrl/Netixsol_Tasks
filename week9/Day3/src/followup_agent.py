"""City Care Clinics - Patient Follow-up & Care Continuity Specialist Agent.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Automates outpatient care continuity and treatment adherence:
1. Generates Structured Reminder Plan:
   - Daily Medication Timetable (Morning, Afternoon, Night meal-aligned)
   - Diagnostic Laboratory Due Dates & Fasting Instructions
   - Follow-up Consultation Review Timetable
2. Drafts Multi-Stage UrduLish WhatsApp / SMS Patient Messages:
   - Day 0: Immediate post-encounter regimen brief & medication timetable
   - 48 Hours: Adherence check & symptom resolution inquiry
   - 7 Days: Diagnostic lab test reminder & follow-up review alert
3. Dispatches messages via FastMCP Notifications Server with delivery receipts.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
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

from mcp_servers.notifications_server import send_whatsapp_message


class MedicationScheduleItem(BaseModel):
    """Specific scheduled dose for a patient."""
    time_slot: str = Field(description="Morning (08:00 AM), Afternoon (02:00 PM), or Night (08:00 PM)")
    urdu_timing: str
    medication_name: str
    dose: str
    instructions: str


class LabReminderItem(BaseModel):
    """Scheduled laboratory diagnostic test."""
    test_name: str
    due_date: str
    fasting_required: bool
    instructions_urdu: str


class FollowUpReminderPlan(BaseModel):
    """Comprehensive outpatient follow-up care plan."""
    patient_id: str
    patient_name: str
    patient_phone: str
    doctor_name: str
    branch_name: str
    encounter_date: str
    follow_up_visit_date: str

    medication_schedule: List[MedicationScheduleItem] = Field(default_factory=list)
    lab_reminders: List[LabReminderItem] = Field(default_factory=list)

    # Drafted multi-stage patient outreach messages in UrduLish
    day0_post_visit_message: str
    day2_adherence_check_message: str
    day7_followup_reminder_message: str


class FollowUpAgent:
    """Production Follow-up Specialist Agent."""

    def create_reminder_plan(
        self,
        patient_id: str,
        patient_name: str,
        patient_phone: str,
        doctor_name: str,
        branch_name: str,
        encounter_date: str,  # YYYY-MM-DD
        prescribed_meds: List[Dict[str, Any]],
        ordered_labs: Optional[List[Dict[str, Any]]] = None,
        follow_up_days: int = 7
    ) -> FollowUpReminderPlan:
        """Constructs personalized medication timetable, lab schedules, and outreach messages."""
        base_dt = datetime.strptime(encounter_date, "%Y-%m-%d")
        follow_up_dt = base_dt + timedelta(days=follow_up_days)
        follow_up_date_str = follow_up_dt.strftime("%Y-%m-%d")

        # 1. Build Medication Timetable
        schedule_items: List[MedicationScheduleItem] = []
        for med in prescribed_meds:
            name = med.get("name", "Medicine")
            dose = med.get("dose", "Standard dose")
            freq = (med.get("frequency") or "OD").upper()
            instr = med.get("instructions", "Baad az ta'am (Khane ke baad)")

            if freq in ["OD", "DAILY"]:
                schedule_items.append(MedicationScheduleItem(
                    time_slot="Morning (08:00 AM)",
                    urdu_timing="Subah 08:00 baje (Nashtay ke baad)",
                    medication_name=name,
                    dose=dose,
                    instructions=instr
                ))
            elif freq in ["BD", "BID"]:
                schedule_items.append(MedicationScheduleItem(
                    time_slot="Morning (08:00 AM)",
                    urdu_timing="Subah 08:00 baje (Nashtay ke baad)",
                    medication_name=name,
                    dose=dose,
                    instructions=instr
                ))
                schedule_items.append(MedicationScheduleItem(
                    time_slot="Night (08:00 PM)",
                    urdu_timing="Raat 08:00 baje (Khane ke baad)",
                    medication_name=name,
                    dose=dose,
                    instructions=instr
                ))
            elif freq in ["TDS", "TID"]:
                schedule_items.append(MedicationScheduleItem(
                    time_slot="Morning (08:00 AM)",
                    urdu_timing="Subah 08:00 baje (Nashtay ke baad)",
                    medication_name=name,
                    dose=dose,
                    instructions=instr
                ))
                schedule_items.append(MedicationScheduleItem(
                    time_slot="Afternoon (02:00 PM)",
                    urdu_timing="Dopehar 02:00 baje (Khane ke baad)",
                    medication_name=name,
                    dose=dose,
                    instructions=instr
                ))
                schedule_items.append(MedicationScheduleItem(
                    time_slot="Night (08:00 PM)",
                    urdu_timing="Raat 08:00 baje (Khane ke baad)",
                    medication_name=name,
                    dose=dose,
                    instructions=instr
                ))
            else:
                schedule_items.append(MedicationScheduleItem(
                    time_slot="As Needed (PRN)",
                    urdu_timing="Zaroorat ke waqt (Dard ya bukhar mein)",
                    medication_name=name,
                    dose=dose,
                    instructions=instr
                ))

        # 2. Build Lab Reminders
        lab_items: List[LabReminderItem] = []
        if ordered_labs:
            for lab in ordered_labs:
                test_name = lab.get("test_name", "Laboratory Test")
                offset = lab.get("due_days", 7)
                lab_due_dt = base_dt + timedelta(days=offset)
                is_fasting = lab.get("fasting_required", False)

                fasting_msg = "8-10 ghantay ka nehar munh (fasting) zaroori hai." if is_fasting else "Fasting ki zaroorat nahi hai."
                lab_items.append(LabReminderItem(
                    test_name=test_name,
                    due_date=lab_due_dt.strftime("%Y-%m-%d"),
                    fasting_required=is_fasting,
                    instructions_urdu=f"Test ki tareekh: {lab_due_dt.strftime('%d-%b-%Y')}. {fasting_msg}"
                ))

        # 3. Draft UrduLish Outreach Messages
        med_summary_lines = []
        for item in schedule_items:
            med_summary_lines.append(f"• {item.urdu_timing}: {item.medication_name} ({item.dose})")
        med_summary_text = "\n".join(med_summary_lines)

        # Message 1: Day 0 Immediate Post-Encounter Care Plan
        day0_msg = (
            f"Assalam-o-Alaikum {patient_name} Janab!\n"
            f"City Care Clinics ({branch_name}) mein {doctor_name} se consultation ka shukriya.\n\n"
            f"📋 Aapki Dawaiyon Ka Schedule:\n"
            f"{med_summary_text}\n\n"
            f"Agar koi masla ho tou is number par rabta farmaiye ga. Shifa-e-Kamilah ke liye dua-go!"
        )

        # Message 2: 48-Hour Adherence & Recovery Pulse Check
        day2_msg = (
            f"Assalam-o-Alaikum {patient_name} Janab,\n"
            f"City Care Clinics se follow-up rabta kiya ja raha hai.\n"
            f"Aapki tabiyat ab kaisi hai? Kya dawaiyan ba-qaidgi se le rahe hain aur behtari mehsoos ho rahi hai?\n"
            f"Agar koi side-effect ya takleef ho tou barah-e-karam foran batayein taake doctor sahib rehnumai farma sakein."
        )

        # Message 3: Day 7 Lab Test & Follow-up Visit Reminder
        lab_due_text = ""
        if lab_items:
            lab_names = ", ".join([l.test_name for l in lab_items])
            lab_due_text = f"\n🧪 Lab Tests Due: {lab_names} ({lab_items[0].instructions_urdu})\n"

        day7_msg = (
            f"Mohtaram {patient_name} Janab, yaad dahani:\n"
            f"{doctor_name} ke saath aapka follow-up checkup {follow_up_date_str} ko scheduled hai."
            f"{lab_due_text}\n"
            f"Barah-e-karam waqt par {branch_name} tashreef layein taake treatment progress ka jaiza liya ja sake. Shukriya!"
        )

        return FollowUpReminderPlan(
            patient_id=patient_id,
            patient_name=patient_name,
            patient_phone=patient_phone,
            doctor_name=doctor_name,
            branch_name=branch_name,
            encounter_date=encounter_date,
            follow_up_visit_date=follow_up_date_str,
            medication_schedule=schedule_items,
            lab_reminders=lab_items,
            day0_post_visit_message=day0_msg,
            day2_adherence_check_message=day2_msg,
            day7_followup_reminder_message=day7_msg
        )

    def dispatch_whatsapp_reminder(
        self,
        recipient_phone: str,
        message_text: str,
        template_name: str = "care_continuity_followup"
    ) -> Dict[str, Any]:
        """Dispatches outbound message via FastMCP Notifications Server."""
        return send_whatsapp_message(
            recipient_phone=recipient_phone,
            message_text=message_text,
            template_name=template_name
        )
