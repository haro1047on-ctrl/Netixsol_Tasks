"""Task 2: Goodbye Node in natural UrduLish."""
from __future__ import annotations

from typing import Any, Dict
from langchain_core.messages import AIMessage

from logger import default_agent_logger
from state import AgentState


def goodbye_node(state: AgentState) -> Dict[str, Any]:
    """Provide a warm closing in UrduLish."""
    step = default_agent_logger.log_node_entry("GoodbyeNode", state.get("last_node", "IntentDetectionNode"), state)

    appt = state.get("appointment_status", {})
    if appt.get("status") == "scheduled":
        summary = f" Yaad rahe, aap ka **{appt.get('property_title')}** ka visit **{appt.get('date_str')} {appt.get('time_str')}** par confirmed hai."
    else:
        summary = ""

    closing_text = (
        f"RealEstate Hub se rabta karne ka shukriya!{summary} "
        f"Agar aap ko mazeed koi maloomat chahiye ho toh zaroor bataye ga. Allah Hafiz!"
    )

    output = {
        "final_response": closing_text,
        "conversation_history": [AIMessage(content=closing_text)],
        "last_node": "GoodbyeNode",
    }

    default_agent_logger.log_node_exit(step, output, reasoning="Delivered consultation wrap-up in UrduLish.")
    return output
