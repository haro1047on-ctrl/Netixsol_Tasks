"""Task 3: Tool Integration Registry for Day 5 LangGraph Agent."""
from __future__ import annotations

from tools.search_tools import property_search_tool, search_properties_core
from tools.availability_tools import (
    availability_checker_tool,
    check_property_availability,
    check_slot_availability,
)
from tools.calendar_tools import (
    calendar_tool,
    create_calendar_event,
    update_calendar_event,
    cancel_calendar_event,
)
from tools.email_tools import email_tool, send_appointment_email
from tools.crm_tools import crm_tool, upsert_lead, log_appointment, get_appointment
from tools.rag_tools import rag_search_tool, search_kb_core

ALL_TOOLS = [
    property_search_tool,
    availability_checker_tool,
    calendar_tool,
    email_tool,
    crm_tool,
    rag_search_tool,
]

__all__ = [
    "ALL_TOOLS",
    "property_search_tool",
    "search_properties_core",
    "availability_checker_tool",
    "check_property_availability",
    "check_slot_availability",
    "calendar_tool",
    "create_calendar_event",
    "update_calendar_event",
    "cancel_calendar_event",
    "email_tool",
    "send_appointment_email",
    "crm_tool",
    "upsert_lead",
    "log_appointment",
    "get_appointment",
    "rag_search_tool",
    "search_kb_core",
]
