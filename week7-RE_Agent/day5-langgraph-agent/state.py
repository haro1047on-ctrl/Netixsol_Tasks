"""Task 1: LangGraph State Design for RealEstate Hub Agent.

Defines the centralized state dictionary used across all graph nodes,
tool executions, routing conditions, and validation layers.
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langchain_core.messages import BaseMessage


class UserProfile(TypedDict, total=False):
    """Client identity and contact information."""
    name: str
    phone: str
    email: str
    city: str
    lead_id: str
    notes: str


class PropertyPreferences(TypedDict, total=False):
    """Extracted and accumulated client property search criteria."""
    city: str
    locality: str
    property_type: str  # House, Flat, Upper Portion, Lower Portion, Plot
    purpose: str        # For Sale, For Rent
    area_marla: Optional[float]
    bedrooms: Optional[int]
    baths: Optional[int]
    desired_amenities: List[str]
    investment_goal: bool


class AppointmentStatus(TypedDict, total=False):
    """Active property visit appointment details and status."""
    appointment_id: str
    lead_id: str
    property_id: str
    property_title: str
    date_str: str
    time_str: str
    status: str  # none, scheduled, rescheduled, cancelled, pending_clarification, slot_unavailable
    agent_name: str
    calendar_event_id: str
    calendar_link: str
    email_id: str
    notes: str
    visit_started: bool
    date_asked_flag: bool
    time_asked_flag: bool
    phone_asked_flag: bool


class ToolExecutionRecord(TypedDict, total=False):
    """Detailed record of an executed tool call for state tracking."""
    tool_name: str
    input_params: Dict[str, Any]
    output_result: Any
    timestamp: str
    status: str  # success, error, rejected_by_validation
    message: str


class AgentState(TypedDict, total=False):
    """Primary LangGraph Agent State.

    Holds the complete conversational, preference, booking, tool-calling,
    and validation lifecycle for the AI agent.
    """
    # 1. Conversation History (supports appending messages)
    conversation_history: Annotated[List[BaseMessage], operator.add]
    messages: Annotated[List[BaseMessage], operator.add]  # Alias for LangGraph standard tools

    # 2. User Profile
    user_profile: UserProfile

    # 3. Property Preferences
    property_preferences: PropertyPreferences

    # 4. Budget in PKR
    budget: Optional[float]

    # 5. Detected Intent
    # (greeting, recommendation, rag, booking, rescheduling, cancellation, email, goodbye, clarification, unknown)
    intent: str

    # 6. Tool Outputs and Execution History
    tool_outputs: Annotated[List[Dict[str, Any]], operator.add]

    # 7. Appointment Status
    appointment_status: AppointmentStatus

    # Additional Robustness & Validation State
    clarification_needed: bool
    clarification_prompt: str
    last_clarification_type: str
    consecutive_unclear_count: int
    validation_errors: Annotated[List[str], operator.add]
    recommended_properties: List[Dict[str, Any]]
    rag_context: str
    rag_sources: List[str]
    last_node: str
    final_response: str
    raw_user_input: str
    session_id: str
    step_count: int


def create_initial_state(session_id: str = "default_session") -> AgentState:
    """Helper to generate a clean, initialized AgentState."""
    return {
        "conversation_history": [],
        "messages": [],
        "user_profile": {
            "name": "",
            "phone": "",
            "email": "",
            "city": "",
            "lead_id": "",
            "notes": "",
        },
        "property_preferences": {
            "city": "",
            "locality": "",
            "property_type": "",
            "purpose": "",
            "area_marla": None,
            "bedrooms": None,
            "baths": None,
            "desired_amenities": [],
            "investment_goal": False,
        },
        "budget": None,
        "intent": "greeting",
        "tool_outputs": [],
        "appointment_status": {
            "appointment_id": "",
            "lead_id": "",
            "property_id": "",
            "property_title": "",
            "date_str": "",
            "time_str": "",
            "status": "none",
            "agent_name": "Ahmed Raza",
            "calendar_event_id": "",
            "calendar_link": "",
            "email_id": "",
            "notes": "",
        },
        "clarification_needed": False,
        "clarification_prompt": "",
        "last_clarification_type": "",
        "consecutive_unclear_count": 0,
        "validation_errors": [],
        "recommended_properties": [],
        "rag_context": "",
        "rag_sources": [],
        "last_node": "START",
        "final_response": "",
        "raw_user_input": "",
        "session_id": session_id,
        "step_count": 0,
    }
