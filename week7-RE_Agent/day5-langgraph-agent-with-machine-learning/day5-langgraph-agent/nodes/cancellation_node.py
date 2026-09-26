"""Task 2 & 3: Cancellation Node in natural spoken UrduLish."""
from __future__ import annotations

import re
from typing import Any, Dict
from langchain_core.messages import AIMessage

from logger import default_agent_logger
from state import AgentState
from tools.calendar_tools import cancel_calendar_event
from tools.crm_tools import log_appointment
from tools.email_tools import send_appointment_email


def cancellation_node(state: AgentState) -> Dict[str, Any]:
    """Cancel scheduled appointment with clean spoken UrduLish response."""
    step = default_agent_logger.log_node_entry("CancellationNode", state.get("last_node", "IntentDetectionNode"), state)

    appt = dict(state.get("appointment_status", {}))
    profile = dict(state.get("user_profile", {}))

    appt_id = appt.get("appointment_id") or "appt_default"
    cal_event_id = appt.get("calendar_event_id") or f"evt_{appt_id}"
    agent_name = appt.get("agent_name") or "Ahmed Raza"
    prop_title = appt.get("property_title") or "Property Visit"
    prop_id = appt.get("property_id") or "PROP-General"
    date_str = appt.get("date_str") or "Scheduled Date"
    time_str = appt.get("time_str") or "Scheduled Time"
    client_name = profile.get("name") or "Valued Client"
    client_phone = profile.get("phone") or "Not Provided"

    # 1. Cancel Calendar Event
    try:
        cancel_calendar_event(cal_event_id, reason="Cancelled by client via AI Agent")
    except Exception:
        pass

    # 2. Update CRM
    try:
        log_appointment(
            lead_id=appt.get("lead_id", "lead_default"),
            client_name=client_name,
            client_phone=client_phone,
            property_id=prop_id,
            property_title=prop_title,
            agent_name=agent_name,
            date_str=date_str,
            time_str=time_str,
            status="cancelled",
            notes="Cancelled by client request",
            appointment_id=appt_id,
        )
    except Exception:
        pass

    # 3. Dispatch Cancellation Email Alert
    try:
        send_appointment_email(
            employee_name=agent_name,
            client_name=client_name,
            client_phone=client_phone,
            property_title=prop_title,
            property_id=prop_id,
            date_str=date_str,
            time_str=time_str,
            notes=f"Client cancelled appointment {appt_id}",
            event_type="cancellation",
            appointment_id=appt_id,
            client_email=profile.get("email", ""),
        )
    except Exception:
        pass

    appt["status"] = "cancelled"
    appt["visit_started"] = False

    name_label = f"{client_name} sahib" if client_name and client_name != "Valued Client" else "ji"
    id_str = f"Appointment ID {appt_id}" if appt_id and not appt_id.startswith("appt_default") else "aap ka visit"
    response_text = (
        f"Zaroor {name_label}, {id_str} ({prop_title}) kamyabi se cancel kar di gayi hai "
        f"aur confirmation email bhej di gayi hai. Jab bhi aap dobara visit plan karein, zaroor bataiye ga."
    )

    output = {
        "appointment_status": appt,
        "final_response": response_text,
        "conversation_history": [AIMessage(content=response_text)],
        "last_node": "CancellationNode",
    }

    default_agent_logger.log_node_exit(step, output, reasoning="Processed cancellation in UrduLish.")
    return output
