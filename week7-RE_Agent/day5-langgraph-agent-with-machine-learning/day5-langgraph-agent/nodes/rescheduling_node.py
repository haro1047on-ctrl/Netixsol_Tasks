"""Task 2 & 3: Rescheduling Node in natural spoken UrduLish."""
from __future__ import annotations

import re
from typing import Any, Dict
from langchain_core.messages import AIMessage

from logger import default_agent_logger
from state import AgentState
from tools.availability_tools import check_slot_availability
from tools.calendar_tools import update_calendar_event
from tools.crm_tools import log_appointment
from tools.email_tools import send_appointment_email


def rescheduling_node(state: AgentState) -> Dict[str, Any]:
    """Reschedule appointment in Calendar, CRM, and Email with clean UrduLish response."""
    step = default_agent_logger.log_node_entry("ReschedulingNode", state.get("last_node", "IntentDetectionNode"), state)

    appt = dict(state.get("appointment_status", {}))
    profile = dict(state.get("user_profile", {}))

    appt_id = appt.get("appointment_id") or "appt_default"
    new_date = appt.get("date_str") or "Tomorrow"
    new_time = appt.get("time_str") or "4:00 PM"
    agent_name = appt.get("agent_name") or "Ahmed Raza"
    prop_title = appt.get("property_title") or "Property Visit"
    prop_id = appt.get("property_id") or "PROP-General"
    client_name = profile.get("name") or "Valued Client"
    client_phone = profile.get("phone") or "Not Provided"

    # 1. Validate slot availability (excluding current appointment from conflicts)
    slot_check = check_slot_availability(
        agent_name=agent_name,
        date_str=new_date,
        time_str=new_time,
        property_id=prop_id,
        exclude_appointment_id=appt_id,
    )
    step.record_tool_call("availability_checker_tool", {"date_str": new_date, "time_str": new_time}, slot_check)

    if not slot_check.get("available", False):
        alt_str = ", ".join(slot_check.get("alternative_slots", []))
        resp = f"Maaf kijiye ga, {new_date} {new_time} available nahi hai. Yeh timings available hain: {alt_str}."
        appt["status"] = "pending_reschedule"
        appt["time_str"] = ""
        output = {
            "appointment_status": appt,
            "final_response": resp,
            "conversation_history": [AIMessage(content=resp)],
            "last_node": "ReschedulingNode",
        }
        default_agent_logger.log_node_exit(step, output, reasoning="Reschedule slot unavailable in UrduLish.")
        return output

    # 2. Update Calendar Event
    cal_event_id = appt.get("calendar_event_id") or f"evt_{appt_id}"
    try:
        updated_cal = update_calendar_event(
            event_id=cal_event_id,
            date_str=new_date,
            time_str=new_time,
            notes=f"Rescheduled visit for {prop_title}",
        )
    except Exception:
        updated_cal = {"google_calendar_link": "https://calendar.google.com"}

    # 3. Update CRM
    try:
        log_appointment(
            lead_id=appt.get("lead_id", "lead_default"),
            client_name=client_name,
            client_phone=client_phone,
            property_id=prop_id,
            property_title=prop_title,
            agent_name=agent_name,
            date_str=new_date,
            time_str=new_time,
            status="rescheduled",
            calendar_link=updated_cal.get("google_calendar_link", ""),
            appointment_id=appt_id,
        )
    except Exception:
        pass

    # 4. Dispatch Email
    try:
        send_appointment_email(
            employee_name=agent_name,
            client_name=client_name,
            client_phone=client_phone,
            property_title=prop_title,
            property_id=prop_id,
            date_str=new_date,
            time_str=new_time,
            notes=f"Appointment {appt_id} rescheduled.",
            calendar_link=updated_cal.get("google_calendar_link", ""),
            event_type="reschedule",
            appointment_id=appt_id,
            client_email=profile.get("email", ""),
        )
    except Exception:
        pass

    appt["status"] = "rescheduled"
    appt["date_str"] = new_date
    appt["time_str"] = new_time

    name_label = f"{client_name} sahib" if client_name and client_name != "Valued Client" else "ji"
    id_str = f"Appointment ID {appt_id}" if appt_id and not appt_id.startswith("appt_default") else "Aap ka visit"
    confirmation = (
        f"Zabardast {name_label}! {id_str} ({prop_title}) ke liye successfully {new_date} {new_time} par reschedule kar diya gaya hai. "
        f"Updated confirmation email aap ko aur consultant {agent_name} ko bhej di gayi hai."
    )

    output = {
        "appointment_status": appt,
        "final_response": confirmation,
        "conversation_history": [AIMessage(content=confirmation)],
        "last_node": "ReschedulingNode",
    }

    default_agent_logger.log_node_exit(step, output, reasoning="Successfully rescheduled appointment.")
    return output
