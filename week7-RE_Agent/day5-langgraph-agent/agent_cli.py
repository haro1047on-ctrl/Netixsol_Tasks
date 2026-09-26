"""Interactive CLI for testing Day 5 LangGraph AI Agent."""
from __future__ import annotations

import json
import sys
import uuid

from graph import run_agent_turn
from logger import default_agent_logger
from state import create_initial_state


def run_interactive_cli():
    """Run an interactive conversation loop in the terminal."""
    session_id = f"session_{uuid.uuid4().hex[:6]}"
    default_agent_logger.session_id = session_id
    state = create_initial_state(session_id=session_id)

    print("\n" + "=" * 75)
    print(" 🏡  REALESTATE HUB — WEEK 7 DAY 5 LANGGRAPH AI AGENT CLI  🏡 ")
    print("=" * 75)
    print(f" Session ID: {session_id}")
    print(" Type your message in Urdu, Roman Urdu, or English.")
    print(" Special commands: 'state' (view current state), 'export' (save traces), 'exit' (quit)")
    print("=" * 75 + "\n")

    # Initial turn: Greeting
    initial_res = run_agent_turn("Hello", current_state=state, session_id=session_id)
    state = initial_res
    print(f"\n🤖 [AI Agent]: {state.get('final_response')}\n")

    while True:
        try:
            user_input = input("👤 [You]: ").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit", "q"):
                print("\nSaving execution traces...")
                traces = default_agent_logger.export_traces()
                print(f"✅ Traces exported:\n   JSON: {traces.get('json_path')}\n   Markdown: {traces.get('md_path')}")
                print("Exiting. Allah Hafiz!\n")
                break

            if user_input.lower() == "state":
                print("\n--- CURRENT AGENT STATE ---")
                clean_state = {
                    "intent": state.get("intent"),
                    "budget": state.get("budget"),
                    "property_preferences": state.get("property_preferences"),
                    "user_profile": state.get("user_profile"),
                    "appointment_status": state.get("appointment_status"),
                    "clarification_needed": state.get("clarification_needed"),
                    "validation_errors": state.get("validation_errors"),
                    "last_node": state.get("last_node"),
                }
                print(json.dumps(clean_state, indent=2))
                print("---------------------------\n")
                continue

            if user_input.lower() == "export":
                traces = default_agent_logger.export_traces()
                print(f"✅ Traces exported:\n   JSON: {traces.get('json_path')}\n   Markdown: {traces.get('md_path')}\n")
                continue

            # Process turn through LangGraph
            state = run_agent_turn(user_input, current_state=state, session_id=session_id)
            print(f"\n🤖 [AI Agent]: {state.get('final_response')}\n")

            if state.get("last_node") == "GoodbyeNode":
                default_agent_logger.export_traces()
                break

        except (KeyboardInterrupt, EOFError):
            default_agent_logger.export_traces()
            print("\nSession ended. Traces saved.\n")
            break


if __name__ == "__main__":
    run_interactive_cli()
