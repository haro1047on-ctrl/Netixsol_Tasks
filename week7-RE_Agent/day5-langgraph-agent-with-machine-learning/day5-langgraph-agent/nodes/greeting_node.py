"""Task 2: Greeting Node for RealEstate Hub Agent in natural UrduLish."""
from __future__ import annotations

from typing import Any, Dict
from langchain_core.messages import AIMessage

from logger import default_agent_logger
from state import AgentState


def greeting_node(state: AgentState) -> Dict[str, Any]:
    """Provide natural, concise UrduLish greeting."""
    step = default_agent_logger.log_node_entry("GreetingNode", state.get("last_node", "START"), state)
    
    greeting_text = (
        "Walikum as Salam! RealEstate Hub mein khush aamdeed. Main aap ka property consultant hoon. "
        "Bataiye, aap ghar dekh rahe hain ya flat?"
    )

    output = {
        "final_response": greeting_text,
        "conversation_history": [AIMessage(content=greeting_text)],
        "last_node": "GreetingNode",
        "intent": "greeting",
    }

    default_agent_logger.log_node_exit(
        step,
        output,
        reasoning="Provided natural UrduLish greeting without plot.",
    )
    return output
