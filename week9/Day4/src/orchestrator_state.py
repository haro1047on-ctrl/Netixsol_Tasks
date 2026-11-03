"""City Care Clinics - Multi-Agent Orchestrator State Definition.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 4: Orchestration, Memory & Human-in-the-Loop
Defines the shared typed state dictionary for LangGraph supervisor and specialist nodes.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, Sequence
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


class OrchestratorState(TypedDict, total=False):
    """Shared state dictionary passed across all LangGraph nodes in the clinic multi-agent system."""
    
    # Session & Identity
    thread_id: str
    patient_id: Optional[str]
    patient_phone: Optional[str]
    patient_name: Optional[str]
    patient_email: Optional[str]
    is_returning_patient: bool
    channel: str  # 'web_chat', 'whatsapp', 'voice', 'email'
    fast_eval_mode: bool
    
    # Conversational History & Messages
    messages: List[Dict[str, Any]]
    last_user_message: str
    
    # Memory Context
    short_term_context: Dict[str, Any]
    long_term_memory: Dict[str, Any]
    
    # Task 1: Intake Form
    intake_form: Dict[str, Any]
    is_intake_complete: bool
    
    # Task 2: Triage Assessment
    triage_decision: Dict[str, Any]
    urgency_tier: str  # 'EMERGENCY', 'URGENT', 'ROUTINE'
    is_emergency: bool
    matched_specialty: str
    
    # Task 3: Scheduling & Booking
    doctor_preference: Dict[str, Any]
    matched_doctors: List[Dict[str, Any]]
    offered_slots: List[str]
    selected_doctor_id: Optional[str]
    selected_slot: Optional[str]
    appointment_booking: Dict[str, Any]
    google_calendar_event: Dict[str, Any]
    
    # Task 4: Records & Clinical Pre-Visit Summary
    ehr_chart: Dict[str, Any]
    pre_visit_soap: Dict[str, Any]
    
    # Task 5: Prescription & Follow-up
    draft_prescription_orders: List[Dict[str, Any]]
    prescription_safety_review: Dict[str, Any]
    followup_plan: Dict[str, Any]
    
    # Human-In-The-Loop (HITL) Doctor Oversight
    hitl_required: bool
    hitl_reason: Optional[str]  # 'LAB_RESULT_EXPLANATION', 'PRESCRIPTION_MESSAGE', 'LOW_CONFIDENCE_TRIAGE'
    hitl_status: str  # 'NONE', 'PENDING', 'APPROVED', 'EDITED', 'REJECTED'
    hitl_draft_content: Optional[str]
    hitl_doctor_edits: Optional[str]
    hitl_doctor_notes: Optional[str]
    hitl_approved_by: Optional[str]
    
    # Outbound Communications
    outbound_messages: List[Dict[str, Any]]
    final_patient_response: str
    
    # Supervisor Routing & Execution Logging
    next_node: Optional[str]
    trace_id: str
    node_transitions: List[Dict[str, Any]]
    execution_errors: List[str]
