"""Task 2: LangGraph Orchestration & Graph Construction.

Builds and compiles the central StateGraph with dynamic conditional routing,
all 9 nodes + clarification safeguard loop, state persistence, and execution tracing.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from logger import default_agent_logger
from nodes import (
    booking_node,
    cancellation_node,
    clarification_node,
    email_node,
    goodbye_node,
    greeting_node,
    intent_detection_node,
    rag_node,
    recommendation_node,
    rescheduling_node,
)
from state import AgentState, create_initial_state


def route_after_intent(state: AgentState) -> str:
    """Conditional router determining the next node from intent detection and validation flags."""
    # 1. Validation Safeguard: Ask clarification instead of guessing
    if state.get("clarification_needed", False):
        return "clarification"

    intent = (state.get("intent") or "greeting").lower().strip()
    
    # 2. Intent Routing Map
    routing_map = {
        "greeting": "greeting",
        "recommendation": "recommendation",
        "booking": "booking",
        "rescheduling": "rescheduling",
        "cancellation": "cancellation",
        "rag": "rag",
        "email": "email",
        "goodbye": "goodbye",
        "off_topic": "clarification",
    }
    return routing_map.get(intent, "greeting")


def build_realestate_graph(checkpointer: Optional[Any] = None) -> Any:
    """Construct and compile the full LangGraph agent workflow."""
    builder = StateGraph(AgentState)

    # 1. Register all nodes
    builder.add_node("intent_detection", intent_detection_node)
    builder.add_node("greeting", greeting_node)
    builder.add_node("clarification", clarification_node)
    builder.add_node("recommendation", recommendation_node)
    builder.add_node("booking", booking_node)
    builder.add_node("rescheduling", rescheduling_node)
    builder.add_node("cancellation", cancellation_node)
    builder.add_node("rag", rag_node)
    builder.add_node("email", email_node)
    builder.add_node("goodbye", goodbye_node)

    # 2. Add entry edge
    builder.add_edge(START, "intent_detection")

    # 3. Add dynamic conditional routing from intent_detection
    builder.add_conditional_edges(
        "intent_detection",
        route_after_intent,
        {
            "clarification": "clarification",
            "greeting": "greeting",
            "recommendation": "recommendation",
            "booking": "booking",
            "rescheduling": "rescheduling",
            "cancellation": "cancellation",
            "rag": "rag",
            "email": "email",
            "goodbye": "goodbye",
        },
    )

    # 4. Add edges to END
    builder.add_edge("greeting", END)
    builder.add_edge("clarification", END)
    builder.add_edge("recommendation", END)
    builder.add_edge("booking", END)
    builder.add_edge("rescheduling", END)
    builder.add_edge("cancellation", END)
    builder.add_edge("rag", END)
    builder.add_edge("email", END)
    builder.add_edge("goodbye", END)

    # Compile with memory checkpointer
    cp = checkpointer if checkpointer is not None else MemorySaver()
    return builder.compile(checkpointer=cp)


# Singleton compiled graph instance
compiled_realestate_agent = build_realestate_graph()


def run_agent_turn(
    user_message: str,
    current_state: Optional[AgentState] = None,
    session_id: str = "session_001",
) -> AgentState:
    """Execute a single conversational turn through the LangGraph pipeline."""
    if current_state is None:
        state = create_initial_state(session_id=session_id)
    else:
        state = dict(current_state)

    state["raw_user_input"] = user_message
    state["session_id"] = session_id
    state["step_count"] = state.get("step_count", 0) + 1

    config = {"configurable": {"thread_id": session_id}}
    result_state = compiled_realestate_agent.invoke(state, config=config)
    return result_state
