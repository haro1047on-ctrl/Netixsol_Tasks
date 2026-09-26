"""Task 2 & 3: Email Node."""
from __future__ import annotations

from typing import Any, Dict
from langchain_core.messages import AIMessage

from logger import default_agent_logger
from state import AgentState
from tools.email_tools import send_appointment_email


def email_node(state: AgentState) -> Dict[str, Any]:
    """Send client or agent summary email via Email Tool."""
    step = default_agent_logger.log_node_entry("EmailNode", state.get("last_node", "IntentDetectionNode"), state)

    profile = state.get("user_profile", {})
    appt = state.get("appointment_status", {})
    rec_props = state.get("recommended_properties", [])

    client_name = profile.get("name") or "Valued Client"
    client_phone = profile.get("phone") or "Not Provided"
    agent_name = appt.get("agent_name") or "Ahmed Raza"

    if rec_props:
        prop = rec_props[0]
        prop_title = f"{prop.get('property_type', 'Property')} in {prop.get('locality', 'Lahore')}"
        prop_id = prop.get("property_id", "PROP-General")
    else:
        prop_title = appt.get("property_title") or "Property Consultation"
        prop_id = appt.get("property_id") or "PROP-General"

    email_res = send_appointment_email(
        employee_name=agent_name,
        client_name=client_name,
        client_phone=client_phone,
        property_title=prop_title,
        property_id=prop_id,
        date_str=appt.get("date_str") or "Upcoming",
        time_str=appt.get("time_str") or "Pending",
        requirements=f"Client requested property dossier and visit information.",
        calendar_link=appt.get("calendar_link", ""),
        event_type="booking" if appt.get("status") == "scheduled" else "inquiry",
    )
    step.record_tool_call("email_tool", {"action": "send_email", "to": agent_name}, email_res)

    response_text = (
        f"📧 **Email Dispatched Successfully!**\n\n"
        f"A comprehensive property dossier and inquiry notification for **{prop_title}** "
        f"has been emailed to consultant **{agent_name}** (`{email_res.get('recipient')}`).\n"
        f"Our team will follow up directly with you shortly."
    )

    output = {
        "final_response": response_text,
        "conversation_history": [AIMessage(content=response_text)],
        "last_node": "EmailNode",
    }

    default_agent_logger.log_node_exit(step, output, reasoning="Dispatched property details email.")
    return output
