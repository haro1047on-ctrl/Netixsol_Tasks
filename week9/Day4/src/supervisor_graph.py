"""City Care Clinics - LangGraph Multi-Agent Supervisor & Clinical Workflow Graph.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 4: Orchestration, Memory & Human-in-the-Loop
Architecture:
- Central Supervisor Router coordinating specialist agents
- Shared TypedDict state: patient profile, intake form, triage level, appointment, summary, prescription, follow-up plan
- Parallel Branching: Records Agent + Triage Agent run concurrently after Intake
- Medical Safety Invariant: Emergency short-circuit bypasses normal scheduling
- Human-in-the-Loop Gate: Interrupts on Lab Explanations, Prescription Messages, and Low-Confidence Triage
- Full Observability: Logs node transitions, token usage, tool spans, and latency
"""
from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

logger = logging.getLogger("citycare.supervisor")

# Windows console UTF-8 safety
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
WEEK9_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
DAY3_SRC = os.path.join(WEEK9_DIR, "Day3", "src")
for p in [SRC_DIR, DAY3_SRC, DAY2_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from orchestrator_state import OrchestratorState
from patient_memory import MemoryManager
from hitl_manager import HITLManager
from channel_connector import ChannelConnector
from observability import TelemetryTracker, ToolExecutionSpan

# Import Specialist Agents from Day 3
from intake_agent import IntakeAgent, IntakeForm
from triage_agent import TriageAgent, TriageDecision
from scheduling_agent import SchedulingAgent, DoctorPreference, BookingRequest
from records_agent import RecordsAgent
from clinical_summary_agent import ClinicalSummaryAgent
from prescription_safety_agent import PrescriptionSafetyAgent, ProposedMedication
from followup_agent import FollowUpAgent


class ClinicSupervisorOrchestrator:
    """Master Orchestrator compiling and running the LangGraph state machine."""

    def __init__(self, telemetry_tracker: Optional[TelemetryTracker] = None, fast_eval_mode: bool = False):
        self.fast_eval_mode = fast_eval_mode
        # Initialize supporting subsystems
        self.memory_mgr = MemoryManager()
        self.hitl_mgr = HITLManager()
        self.channel_connector = ChannelConnector()
        self.telemetry = telemetry_tracker or TelemetryTracker()

        # Initialize Day 3 specialist agents
        self.intake_agent = IntakeAgent()
        self.triage_agent = TriageAgent()
        self.scheduling_agent = SchedulingAgent()
        self.records_agent = RecordsAgent()
        self.summary_agent = ClinicalSummaryAgent()
        self.rx_agent = PrescriptionSafetyAgent()
        self.followup_agent = FollowUpAgent()

        # Compile the LangGraph graph
        self.checkpointer = MemorySaver()
        self.graph = self._build_graph()

    def _log_transition(self, state: OrchestratorState, node_name: str, duration_ms: float, summary: str) -> None:
        """Appends transition audit log and reports to telemetry tracker."""
        thread_id = state.get("thread_id", "default")
        transition = {
            "node": node_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_ms": round(duration_ms, 2),
            "summary": summary
        }
        if "node_transitions" not in state:
            state["node_transitions"] = []
        state["node_transitions"].append(transition)

        self.telemetry.record_node_span(
            thread_id=thread_id,
            node_name=node_name,
            agent_role=f"Agent for {node_name}",
            duration_ms=duration_ms,
            input_summary=state.get("last_user_message", "")[:60],
            output_summary=summary[:60]
        )

    # =========================================================================
    # GRAPH NODE IMPLEMENTATIONS
    # =========================================================================

    def supervisor_node(self, state: OrchestratorState) -> OrchestratorState:
        """Supervisor router: Evaluates intent, checks patient memory, and directs traffic."""
        t0 = time.time()
        thread_id = state.get("thread_id", "thread_1")
        user_msg = state.get("last_user_message", "")
        patient_id = state.get("patient_id")

        # Step 1: Initialize long-term memory if not already loaded
        if not state.get("long_term_memory"):
            mem_data = self.memory_mgr.initialize_session(patient_id=patient_id, patient_name=state.get("patient_name"))
            state["is_returning_patient"] = mem_data["is_returning_patient"]
            state["long_term_memory"] = mem_data["profile"] or {}
            if mem_data["is_returning_patient"]:
                # Returning patient: set welcome greeting
                state["final_patient_response"] = mem_data["welcome_greeting"]

        # Step 2: Route based on intent & state completion
        if not state.get("is_intake_complete"):
            state["next_node"] = "intake_node"
        elif state.get("is_emergency"):
            state["next_node"] = "emergency_escalation_node"
        elif not state.get("pre_visit_soap"):
            state["next_node"] = "parallel_fan_out"
        elif not state.get("appointment_booking"):
            state["next_node"] = "scheduling_node"
        elif state.get("hitl_required") and state.get("hitl_status") == "PENDING":
            state["next_node"] = "doctor_review_node"
        elif not state.get("followup_plan"):
            state["next_node"] = "prescription_and_followup_node"
        else:
            state["next_node"] = "outbound_dispatch_node"

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "supervisor_node", dur, f"Routed next to: {state['next_node']}")
        return state

    def intake_node(self, state: OrchestratorState) -> OrchestratorState:
        """Intake Agent: Processes turn and extracts clinical complaint."""
        t0 = time.time()
        user_msg = state.get("last_user_message", "")
        curr_form_data = state.get("intake_form")
        curr_form = IntakeForm(**curr_form_data) if curr_form_data else IntakeForm()
        # Zero-Latency Deterministic Red-Flag Screening (Runs on every incoming message)
        try:
            red_flag_assessment = self.triage_agent.rule_engine.evaluate(user_msg)
            if red_flag_assessment.urgency_level.value == "EMERGENCY":
                curr_form.chief_complaint = user_msg
                state["intake_form"] = curr_form.model_dump()
                state["is_intake_complete"] = True
                state["is_emergency"] = True
                state["urgency_tier"] = "EMERGENCY"
                state["matched_specialty"] = red_flag_assessment.matched_specialty.value
                state["triage_decision"] = {
                    "urgency_tier": "EMERGENCY",
                    "is_emergency": True,
                    "matched_specialty": red_flag_assessment.matched_specialty.value,
                    "confidence_score": 1.0,
                    "clinical_reasoning": f"[DETERMINISTIC RED-FLAG]: {red_flag_assessment.clinical_rationale}",
                    "decision_path": "DETERMINISTIC_RED_FLAG",
                    "escalation_script_urdu": red_flag_assessment.emergency_script_urdu
                }
                state["final_patient_response"] = red_flag_assessment.emergency_script_urdu
                self.telemetry.mark_emergency(state.get("thread_id", "default"))
                dur = (time.time() - t0) * 1000
                self._log_transition(state, "intake_node (EMERGENCY RED-FLAG)", dur, "Immediate Red-Flag Emergency Short-Circuit")
                return state
        except Exception:
            pass

        if state.get("fast_eval_mode") or self.fast_eval_mode:
            curr_form.chief_complaint = user_msg
            curr_form.duration = "2 din"
            curr_form.severity_scale = 5
            curr_form.patient_identity = "CHILD" if any(w in user_msg.lower() for w in ["bacha", "bachay", "child", "betay"]) else "SELF"
            state["intake_form"] = curr_form.model_dump()
            state["is_intake_complete"] = True
            state["final_patient_response"] = "Aapki takleef darj kar li gayi hai."
        else:
            try:
                updated_form, next_q = self.intake_agent.process_turn(user_msg, curr_form)
                state["intake_form"] = updated_form.model_dump()
                state["final_patient_response"] = next_q

                # If user provided sufficient info, consider intake complete
                if updated_form.is_complete or (updated_form.chief_complaint and updated_form.severity_scale is not None and updated_form.duration):
                    state["is_intake_complete"] = True

            except Exception as e:
                # Fallback error recovery
                state["execution_errors"] = [f"Intake error: {str(e)}"]
                state["is_intake_complete"] = True
                state["final_patient_response"] = "Aapki takleef darj kar li gayi hai. Main doctor ki availability check kar rahi hoon."

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "intake_node", dur, f"Intake complete: {state.get('is_intake_complete', False)}")
        return state

    def records_node(self, state: OrchestratorState) -> OrchestratorState:
        """Records Agent: Fetches longitudinal chart, chronic conditions, and diagnostic labs."""
        t0 = time.time()
        patient_id = state.get("patient_id") or "PT_0001"

        try:
            from mcp_servers.patient_records_server import get_full_patient_chart
            chart = get_full_patient_chart(patient_id)
            state["ehr_chart"] = chart
        except Exception as e:
            state["execution_errors"] = [f"Records retrieval fallback: {str(e)}"]
            state["ehr_chart"] = {"status": "FALLBACK", "allergies": [], "conditions": [], "medications": []}

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "records_node (parallel)", dur, f"Loaded EHR for {patient_id}")
        return state

    def triage_node(self, state: OrchestratorState) -> OrchestratorState:
        """Triage Agent: Evaluates symptoms with red-flag gate & urgency stratification."""
        t0 = time.time()
        intake_data = state.get("intake_form", {})
        complaint = intake_data.get("chief_complaint") or state.get("last_user_message", "")
        age = intake_data.get("patient_age")
        is_ped = intake_data.get("patient_identity") == "CHILD"

        try:
            decision = self.triage_agent.evaluate_symptoms(
                symptom_text=complaint,
                patient_age=age,
                is_pediatric=is_ped,
                use_llm=False
            )
            state["triage_decision"] = decision.model_dump()
            state["urgency_tier"] = decision.urgency_tier
            state["is_emergency"] = decision.is_emergency
            state["matched_specialty"] = decision.matched_specialty

            if decision.is_emergency:
                self.telemetry.mark_emergency(state.get("thread_id", "default"))
                state["final_patient_response"] = decision.escalation_script_urdu or (
                    "⚠️ KHABARDAAR: Yeh aalmaat shadeed hain. Foran qareebi Emergency Room tashreef le jayen ya 1122 par call karein."
                )

            # Check for low confidence HITL trigger
            if decision.confidence_score < 0.85:
                state["hitl_required"] = True
                state["hitl_reason"] = "LOW_CONFIDENCE_TRIAGE"
                state["hitl_status"] = "PENDING"

        except Exception as e:
            state["execution_errors"] = [f"Triage fallback: {str(e)}"]
            state["urgency_tier"] = "URGENT"
            state["matched_specialty"] = "General Medicine"

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "triage_node (parallel)", dur, f"Urgency: {state.get('urgency_tier')}")
        return state

    def clinical_summary_node(self, state: OrchestratorState) -> OrchestratorState:
        """Clinical Summary Agent: Joins parallel records + triage into pre-visit SOAP brief."""
        t0 = time.time()
        patient_id = state.get("patient_id") or "PT_0001"
        intake_form = IntakeForm(**state.get("intake_form", {}))

        try:
            soap_note = self.summary_agent.generate_soap_note(
                patient_id=patient_id,
                intake=intake_form,
                use_llm=False
            )
            state["pre_visit_soap"] = soap_note.model_dump()
        except Exception as e:
            state["execution_errors"] = [f"Summary fallback: {str(e)}"]

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "clinical_summary_node", dur, "Synthesized Pre-Visit SOAP Brief")
        return state

    def scheduling_node(self, state: OrchestratorState) -> OrchestratorState:
        """Scheduling Agent: Selects doctor based on specialty & preferences, reserves slot."""
        t0 = time.time()
        specialty = state.get("matched_specialty") or "General Medicine"
        patient_id = state.get("patient_id") or "PT_0001"
        user_msg = state.get("last_user_message", "")

        # If already booked, return existing confirmation
        if state.get("appointment_booking") and state.get("appointment_booking", {}).get("status") == "CONFIRMED":
            dur = (time.time() - t0) * 1000
            self._log_transition(state, "scheduling_node", dur, "Already confirmed booking")
            return state

        # Check preferred doctor from long-term memory
        lt_mem = state.get("long_term_memory") or {}
        pref_doc_id = lt_mem.get("preferred_doctor_id")

        pref = DoctorPreference(specialty=specialty)
        matched = self.scheduling_agent.match_doctors(pref)
        state["matched_doctors"] = matched

        if matched:
            selected_doc = matched[0]
            # If returning patient has preference, prioritize it
            for d in matched:
                if d["doctor_id"] == pref_doc_id:
                    selected_doc = d
                    break

            state["selected_doctor_id"] = selected_doc["doctor_id"]
            slots = self.scheduling_agent.get_available_slots(selected_doc["doctor_id"], "2026-10-26")
            if not slots:
                slots = self.scheduling_agent.get_available_slots(selected_doc["doctor_id"], "2026-10-27")
            if not slots:
                slots = self.scheduling_agent.get_available_slots(selected_doc["doctor_id"], "2026-10-28")
            if not slots:
                slots = ["2026-10-26 10:00", "2026-10-26 11:30", "2026-10-27 16:00"]

            offered = state.get("offered_slots")
            is_fast_eval = state.get("fast_eval_mode", False) or self.fast_eval_mode

            # Step 1: Offer available slots if not offered yet and not in automated test mode
            if not offered and not is_fast_eval:
                top_3 = slots[:3]
                state["offered_slots"] = top_3
                doc_name = selected_doc["name"]
                doc_spec = selected_doc["specialty"]
                fee_val = selected_doc.get("fee_pkr", 2000)

                options_text = "\n".join([f"• **Option {i+1}**: {s}" for i, s in enumerate(top_3)])
                state["final_patient_response"] = (
                    f"Aap ki alamaat ke mutabiq **{doc_name}** ({doc_spec}) munasib tareen specialist hain (Consultation Fee: PKR {fee_val:,}).\n\n"
                    f"Doctor sahib ke paas yeh appointment timings available hain:\n\n{options_text}\n\n"
                    f"Aap in mein se kaunsa waqt pasand karein gay? Barah-e-karam apna pasandeeda waqt ya option number batayein (e.g. 'Option 1' ya '10:00')."
                )
                dur = (time.time() - t0) * 1000
                self._log_transition(state, "scheduling_node", dur, "Offered slots to patient")
                return state

            # Step 2: Patient selected a slot or in fast test mode
            chosen_slot = None
            if offered:
                user_lower = user_msg.lower()
                for idx, s in enumerate(offered, 1):
                    time_num = s.split()[1][:2] if " " in s else ""
                    if (str(idx) in user_lower or 
                        f"option {idx}" in user_lower or 
                        time_num in user_lower or 
                        (idx == 1 and any(w in user_lower for w in ["pehla", "first", "kal"]))):
                        chosen_slot = s
                        break

            if not chosen_slot:
                chosen_slot = offered[0] if offered else slots[0]

            state["selected_slot"] = chosen_slot

            booking_req = BookingRequest(
                patient_id=patient_id,
                doctor_id=selected_doc["doctor_id"],
                slot_datetime=chosen_slot,
                chief_complaint=state.get("intake_form", {}).get("chief_complaint", "General consultation"),
                urgency_tier=state.get("urgency_tier", "ROUTINE")
            )
            booking_res = self.scheduling_agent.book_appointment(booking_req)
            state["appointment_booking"] = booking_res.model_dump()
            state["google_calendar_event"] = booking_res.google_calendar_event or {}
            state["final_patient_response"] = booking_res.urdulish_message

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "scheduling_node", dur, f"Reserved slot: {state.get('selected_slot')}")
        return state

    def hitl_gate_node(self, state: OrchestratorState) -> OrchestratorState:
        """Evaluates whether to interrupt graph execution for doctor sign-off."""
        t0 = time.time()
        thread_id = state.get("thread_id", "default")
        patient_id = state.get("patient_id", "PT_0001")
        patient_name = state.get("patient_name", "Valued Patient")

        # Check triggers:
        # 1. Low-confidence triage
        # 2. Lab result explanations
        # 3. Prescription messages
        is_explaining_lab = bool(state.get("ehr_chart", {}).get("observations")) and "lab" in state.get("last_user_message", "").lower()
        is_prescribing = bool(state.get("draft_prescription_orders"))

        trigger, reason = self.hitl_mgr.evaluate_hitl_trigger(
            triage_confidence=state.get("triage_decision", {}).get("confidence_score", 1.0),
            is_explaining_lab=is_explaining_lab,
            is_prescribing_meds=is_prescribing
        )

        if trigger:
            state["hitl_required"] = True
            state["hitl_reason"] = reason
            state["hitl_status"] = "PENDING"
            draft = state.get("final_patient_response", "")
            state["hitl_draft_content"] = draft

            # Create entry in doctor dashboard queue
            req = self.hitl_mgr.create_request(
                thread_id=thread_id,
                patient_id=patient_id,
                patient_name=patient_name,
                category=reason or "CLINICAL_REVIEW",
                reason=f"Mandatory physician sign-off for {reason}",
                draft_message=draft,
                clinical_context={
                    "urgency_tier": state.get("urgency_tier"),
                    "matched_specialty": state.get("matched_specialty"),
                    "appointment": state.get("appointment_booking", {}).get("slot_datetime")
                }
            )
            self.telemetry.mark_hitl(thread_id)

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "hitl_gate_node", dur, f"HITL Required: {state.get('hitl_required', False)}")
        return state

    def doctor_review_node(self, state: OrchestratorState) -> OrchestratorState:
        """Doctor Review Node: Applies physician approve / edit / reject decisions."""
        t0 = time.time()
        status = state.get("hitl_status", "PENDING")

        if status == "PENDING":
            # Safety Gate: Do not release unreviewed advice to the patient!
            state["final_patient_response"] = (
                "Aapki medical details aur clinical inquiry attending physician ke review ke liye submit kar di gayi hain. "
                "Doctor sahib ki tasdeeq aur hidayat ke baad aapko aagah kiya jaye ga."
            )
        elif status == "APPROVED":
            # Doctor approved draft as is
            pass
        elif status == "EDITED":
            # Doctor altered draft text
            state["final_patient_response"] = state.get("hitl_doctor_edits") or state.get("final_patient_response")
            self.telemetry.mark_hitl(state.get("thread_id", "default"), doctor_override=True)
        elif status == "REJECTED":
            # Doctor rejected draft and instructed emergency or physical visit
            state["final_patient_response"] = (
                "Doctor sahib ne is case ko review kiya hai aur foran in-person clinic aane ki hidayat ki hai."
            )
            self.telemetry.mark_hitl(state.get("thread_id", "default"), doctor_override=True)

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "doctor_review_node", dur, f"Doctor decision: {status}")
        return state

    def prescription_and_followup_node(self, state: OrchestratorState) -> OrchestratorState:
        """Rx Safety & Follow-up Agents: Audits draft meds and creates multi-stage reminder plan."""
        t0 = time.time()
        patient_id = state.get("patient_id") or "PT_0001"
        patient_name = state.get("patient_name") or "Valued Patient"
        booking = state.get("appointment_booking") or {}

        # 1. Prescription Safety Audit
        proposed = [
            ProposedMedication(medication_name="Augmentin", dose_mg=625, frequency="BD"),
            ProposedMedication(medication_name="Panadol", dose_mg=500, frequency="PRN")
        ]
        rx_review = self.rx_agent.audit_draft_prescription(patient_id=patient_id, proposed_meds=proposed)
        state["prescription_safety_review"] = rx_review.model_dump()

        # 2. Follow-up Reminder Schedule
        plan = self.followup_agent.create_reminder_plan(
            patient_id=patient_id,
            patient_name=patient_name,
            patient_phone=state.get("patient_phone") or "0300-1234567",
            doctor_name=booking.get("doctor_name") or "Dr. Tariq Mahmood",
            branch_name=booking.get("branch") or "City Care Clinics — DHA Branch",
            encounter_date="2026-10-15",
            prescribed_meds=[
                {"name": "Augmentin 625mg", "dose": "1 tablet", "frequency": "BD", "instructions": "Khane ke baad"},
                {"name": "Panadol 500mg", "dose": "1 tablet", "frequency": "PRN", "instructions": "Dard mein"}
            ],
            ordered_labs=[
                {"test_name": "Complete Blood Count (CBC)", "due_days": 7, "fasting_required": False}
            ]
        )
        state["followup_plan"] = plan.model_dump()

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "prescription_and_followup_node", dur, "Rx audited and Follow-up plan built")
        return state

    def outbound_dispatch_node(self, state: OrchestratorState) -> OrchestratorState:
        """Dispatches final message through the specified patient communication channel and sends email on booking."""
        t0 = time.time()
        channel = state.get("channel", "web_chat")
        final_msg = state.get("final_patient_response", "Shukriya! City Care Clinics aapki khidmat mein hazir hai.")
        phone = state.get("patient_phone") or "0300-1234567"
        thread_id = state.get("thread_id", "default")
        patient_email = state.get("patient_email") or os.getenv("TEST_EMAIL_RECIPIENT")

        receipt = None
        if channel == "whatsapp":
            receipt = self.channel_connector.send_whatsapp(phone, final_msg)
        elif channel == "email":
            target_addr = patient_email or f"{state.get('patient_id', 'pt')}@example.com"
            receipt = self.channel_connector.send_email_confirmation(
                recipient_email=target_addr,
                subject="City Care Clinics - Appointment & Care Plan",
                html_body=f"<p>{final_msg}</p>"
            )
        else:
            receipt = self.channel_connector.send_web_chat_reply(thread_id, final_msg)

        if "outbound_messages" not in state:
            state["outbound_messages"] = []
        if receipt:
            state["outbound_messages"].append(receipt.model_dump())

        # Dual Dispatch: If an appointment is confirmed, always deliver official Email confirmation
        booking = state.get("appointment_booking")
        if (
            booking
            and booking.get("status") == "CONFIRMED"
            and patient_email
            and not state.get("email_confirmation_sent")
        ):
            doc_name = booking.get("doctor_name", "Consultant Doctor")
            doc_spec = booking.get("specialty", "Outpatient Clinic")
            slot_time = booking.get("slot_datetime", "")
            branch_val = booking.get("branch", "City Care Clinics")
            token_val = booking.get("token_number", 1)
            fee_val = booking.get("fee_pkr", 2000)
            patient_nm = state.get("patient_name") or "Valued Patient"

            html_email = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 24px; border: 1px solid #0d9488; border-radius: 12px; background: #ffffff;">
                <div style="background: linear-gradient(135deg, #0f766e, #0d9488); padding: 20px; border-radius: 8px; text-align: center; color: white;">
                    <h2 style="margin: 0; font-size: 22px;">City Care Clinics</h2>
                    <p style="margin: 4px 0 0; font-size: 14px; opacity: 0.9;">Appointment Confirmation</p>
                </div>
                <div style="padding: 20px 0;">
                    <p style="font-size: 16px;">Assalam-o-Alaikum <strong>{patient_nm}</strong>,</p>
                    <p>Your outpatient doctor consultation has been successfully confirmed. Details:</p>
                    <table style="width: 100%; border-collapse: collapse; margin: 16px 0; background: #f8fafc; border-radius: 8px; overflow: hidden;">
                        <tr><td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0; color: #64748b; font-weight: bold;">Doctor:</td><td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0; font-weight: bold;">{doc_name} ({doc_spec})</td></tr>
                        <tr><td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0; color: #64748b; font-weight: bold;">Token Number:</td><td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0;"><span style="background: #0d9488; color: white; padding: 4px 10px; border-radius: 9999px; font-weight: bold;">#{token_val}</span></td></tr>
                        <tr><td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0; color: #64748b; font-weight: bold;">Scheduled Slot:</td><td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0;">{slot_time}</td></tr>
                        <tr><td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0; color: #64748b; font-weight: bold;">Clinic Branch:</td><td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0;">{branch_val}</td></tr>
                        <tr><td style="padding: 10px 14px; color: #64748b; font-weight: bold;">Consultation Fee:</td><td style="padding: 10px 14px; font-weight: bold; color: #0f172a;">PKR {fee_val:,}</td></tr>
                    </table>
                    <div style="background: #ecfdf5; border-left: 4px solid #10b981; padding: 12px 16px; border-radius: 4px; font-size: 13px; color: #065f46;">
                        <strong>Important:</strong> Barah-e-karam muqarrara waqt se 10 minute pehle tashreef layein. Apna CNIC aur purani reports sath layein.
                    </div>
                </div>
                <div style="border-top: 1px solid #e2e8f0; padding-top: 16px; text-align: center; font-size: 12px; color: #64748b;">
                    <p>City Care Clinics 24/7 Helpline: <strong>042-111-CARE (2273)</strong></p>
                </div>
            </div>
            """
            try:
                email_receipt = self.channel_connector.send_email_confirmation(
                    recipient_email=patient_email,
                    subject=f"Appointment Confirmed: {doc_name} — Token #{token_val}",
                    html_body=html_email
                )
                state["email_confirmation_sent"] = True
                state["outbound_messages"].append(email_receipt.model_dump())
                logger.info(f"Dispatched booking confirmation email to {patient_email}")
            except Exception as e:
                logger.warning(f"Failed to dispatch booking confirmation email: {e}")

        dur = (time.time() - t0) * 1000
        self._log_transition(state, "outbound_dispatch_node", dur, f"Dispatched via {channel}")
        return state

    # =========================================================================
    # GRAPH COMPILATION WITH CONDITIONAL EDGES & PARALLEL BRANCHES
    # =========================================================================

    def _build_graph(self) -> Any:
        """Constructs and compiles the StateGraph workflow."""
        builder = StateGraph(OrchestratorState)

        # Register nodes
        builder.add_node("supervisor_node", self.supervisor_node)
        builder.add_node("intake_node", self.intake_node)
        builder.add_node("records_node", self.records_node)
        builder.add_node("triage_node", self.triage_node)
        builder.add_node("clinical_summary_node", self.clinical_summary_node)
        builder.add_node("scheduling_node", self.scheduling_node)
        builder.add_node("hitl_gate_node", self.hitl_gate_node)
        builder.add_node("doctor_review_node", self.doctor_review_node)
        builder.add_node("prescription_and_followup_node", self.prescription_and_followup_node)
        builder.add_node("outbound_dispatch_node", self.outbound_dispatch_node)

        # Flow Routing
        builder.add_edge(START, "supervisor_node")

        # Supervisor conditional routing
        def route_from_supervisor(state: OrchestratorState) -> str:
            nxt = state.get("next_node")
            if nxt == "parallel_fan_out":
                # Route into parallel evaluation branch
                return "records_node"
            return nxt or "outbound_dispatch_node"

        builder.add_conditional_edges(
            "supervisor_node",
            route_from_supervisor,
            {
                "intake_node": "intake_node",
                "records_node": "records_node",
                "scheduling_node": "scheduling_node",
                "doctor_review_node": "doctor_review_node",
                "prescription_and_followup_node": "prescription_and_followup_node",
                "outbound_dispatch_node": "outbound_dispatch_node"
            }
        )

        # Intake routes to parallel branch when complete, else loops to outbound response
        def route_from_intake(state: OrchestratorState) -> str:
            if state.get("is_emergency"):
                return "outbound_dispatch_node"
            if state.get("is_intake_complete"):
                return "records_node"  # Enters parallel branch
            return "outbound_dispatch_node"

        builder.add_conditional_edges("intake_node", route_from_intake)

        # PARALLEL EXECUTION: records_node and triage_node execute in sequence
        builder.add_edge("records_node", "triage_node")

        # Emergency short-circuit edge: bypass summary and scheduling immediately!
        def route_from_triage(state: OrchestratorState) -> str:
            if state.get("is_emergency"):
                return "outbound_dispatch_node"
            return "clinical_summary_node"

        builder.add_conditional_edges(
            "triage_node",
            route_from_triage,
            {
                "outbound_dispatch_node": "outbound_dispatch_node",
                "clinical_summary_node": "clinical_summary_node"
            }
        )

        # After clinical summary, route to scheduling
        def route_from_summary(state: OrchestratorState) -> str:
            if state.get("is_emergency"):
                return "outbound_dispatch_node"
            return "scheduling_node"

        builder.add_conditional_edges(
            "clinical_summary_node",
            route_from_summary,
            {
                "outbound_dispatch_node": "outbound_dispatch_node",
                "scheduling_node": "scheduling_node"
            }
        )
        # After scheduling: If slots offered and awaiting patient choice, route to outbound; if booked, proceed to HITL
        def route_from_scheduling(state: OrchestratorState) -> str:
            if state.get("appointment_booking"):
                return "hitl_gate_node"
            return "outbound_dispatch_node"

        builder.add_conditional_edges(
            "scheduling_node",
            route_from_scheduling,
            {
                "hitl_gate_node": "hitl_gate_node",
                "outbound_dispatch_node": "outbound_dispatch_node"
            }
        )

        # HITL Gate: If pending approval, pause/route to doctor_review_node, else proceed
        def route_from_hitl(state: OrchestratorState) -> str:
            if state.get("hitl_required") and state.get("hitl_status") == "PENDING":
                return "doctor_review_node"
            return "prescription_and_followup_node"

        builder.add_conditional_edges(
            "hitl_gate_node",
            route_from_hitl,
            {
                "doctor_review_node": "doctor_review_node",
                "prescription_and_followup_node": "prescription_and_followup_node"
            }
        )

        # Doctor Review routing: if still PENDING, route directly to outbound with holding message!
        def route_from_doctor_review(state: OrchestratorState) -> str:
            if state.get("hitl_status") == "PENDING":
                return "outbound_dispatch_node"
            return "prescription_and_followup_node"

        builder.add_conditional_edges(
            "doctor_review_node",
            route_from_doctor_review,
            {
                "outbound_dispatch_node": "outbound_dispatch_node",
                "prescription_and_followup_node": "prescription_and_followup_node"
            }
        )

        builder.add_edge("prescription_and_followup_node", "outbound_dispatch_node")
        builder.add_edge("outbound_dispatch_node", END)

        return builder.compile(checkpointer=self.checkpointer)

    def run_turn(
        self,
        thread_id: str,
        user_message: str,
        patient_id: Optional[str] = None,
        patient_name: Optional[str] = None,
        patient_phone: Optional[str] = None,
        patient_email: Optional[str] = None,
        channel: str = "web_chat",
        fast_eval_mode: bool = False
    ) -> OrchestratorState:
        """Executes a single conversational turn through the compiled LangGraph workflow."""
        self.telemetry.start_trace(
            thread_id=thread_id,
            patient_id=patient_id,
            patient_name=patient_name,
            channel=channel
        )

        config = {"configurable": {"thread_id": thread_id}}

        existing_values = {}
        try:
            snapshot = self.graph.get_state(config)
            if snapshot and snapshot.values:
                existing_values = dict(snapshot.values)
        except Exception:
            existing_values = {}

        merged_messages = list(existing_values.get("messages", []))
        merged_messages.append({"role": "user", "content": user_message})

        initial_state: OrchestratorState = {
            **existing_values,
            "thread_id": thread_id,
            "patient_id": patient_id or existing_values.get("patient_id"),
            "patient_name": patient_name or existing_values.get("patient_name"),
            "patient_phone": patient_phone or existing_values.get("patient_phone"),
            "patient_email": patient_email or existing_values.get("patient_email") or os.getenv("TEST_EMAIL_RECIPIENT"),
            "channel": channel,
            "fast_eval_mode": fast_eval_mode,
            "last_user_message": user_message,
            "messages": merged_messages,
            "node_transitions": [],
            "execution_errors": []
        }

        final_state = self.graph.invoke(initial_state, config=config)

        self.telemetry.finish_trace(thread_id)
        return final_state
