"""Task 4: Clarification Node in natural UrduLish."""
from __future__ import annotations

from typing import Any, Dict
from langchain_core.messages import AIMessage

from logger import default_agent_logger
from state import AgentState


def clarification_node(state: AgentState) -> Dict[str, Any]:
    """Politely prompt the user for missing parameters in natural UrduLish."""
    step = default_agent_logger.log_node_entry("ClarificationNode", state.get("last_node", "IntentDetectionNode"), state)

    prompt = state.get("clarification_prompt")
    if not prompt:
        prefs = state.get("property_preferences", {})
        budget = state.get("budget")
        pt = prefs.get("property_type", "ghar").lower()
        if not prefs.get("city"):
            prompt = "Aap kis city mein dekhna chahenge? Hamare paas Lahore, Islamabad aur Rawalpindi mein options available hain."
        elif not budget and prefs.get("area_marla") is None:
            prompt = f"Aap kitne marla ka {pt} dekh rahe hain aur aapka approximate budget kitna hai?"
        else:
            prompt = "Baraye meherbani apni requirements thori mazeed wazeh bataiye taake main behtareen options dikha sakoon."

    step.record_validation(
        check_name="Clarification Safeguard",
        passed=True,
        details=f"Prompted user for clarification in UrduLish: '{prompt}'",
    )

    output = {
        "final_response": prompt,
        "conversation_history": [AIMessage(content=prompt)],
        "clarification_needed": False,
        "last_node": "ClarificationNode",
    }

    default_agent_logger.log_node_exit(
        step,
        output,
        reasoning="Requested clarification from user in UrduLish.",
    )
    return output
