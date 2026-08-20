"""
================================================================================
LANGGRAPH AFL CHATBOT — INTERACTIVE TERMINAL CLI
Orchestrated Chat, Retrieval & Prediction Engine
================================================================================
"""

import sys
import os
from dotenv import load_dotenv

# Ensure Day4 is in python path
sys.path.append(os.path.dirname(__file__))

from langgraph_afl_agent import afl_app


def print_banner():
    print("=" * 85)
    print("      🏈 LANGGRAPH ORCHESTRATED AFL ASSISTANT — INTERACTIVE TERMINAL 🏈")
    print("=" * 85)
    print(" - System Router : Explicit LangGraph StateGraph (Routing Chat, Retrieval & Predictions)")
    print(" - Predictions   : Match Winners (Win Prob %, Driving Features) & Top Scorers")
    print(" - Retrieval     : Grounded AFL Statistics (Disposals, Goals, Margins, Season Records)")
    print(" - Factual Rules : AFL Game Rules, Terminology (Mark inside 50), & MCG Stadium Info")
    print(" - Guardrails    : Off-topic questions declined & warmly redirected")
    print(" - Commands      : Type '/reset' to clear state, or 'exit' / 'quit' to close")
    print("=" * 85)
    print()


def run_interactive_bot():
    print_banner()

    state = {
        "user_query": "",
        "messages": [],
        "detected_intent": "",
        "entities": {},
        "tool_results": {},
        "validation_status": "",
        "clarification_prompt": None,
        "final_response": ""
    }

    try:
        while True:
            user_input = input("\nUser > ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "q"]:
                print("\nGoodbye! Go footy! 🏈")
                break

            if user_input.lower() == "/reset":
                state = {
                    "user_query": "",
                    "messages": [],
                    "detected_intent": "",
                    "entities": {},
                    "tool_results": {},
                    "validation_status": "",
                    "clarification_prompt": None,
                    "final_response": ""
                }
                print("\n[System State & Memory Reset Successfully]")
                continue

            print("\n[Processing Query via LangGraph StateGraph...]")

            # Update user query in state
            state["user_query"] = user_input

            # Invoke LangGraph app
            final_state = afl_app.invoke(state)

            # Display Metadata
            intent = final_state.get("detected_intent", "unknown").upper()
            status = final_state.get("validation_status", "VALID")
            print(f"[Graph Router: {intent} | Validation: {status}]")

            # Display Agent Response
            print("\nAgent > " + final_state["final_response"])
            print("-" * 85)

            # Preserve state for follow-ups
            state = final_state

    except (KeyboardInterrupt, EOFError):
        print("\n\nSession ended. Goodbye!")


if __name__ == "__main__":
    load_dotenv()
    run_interactive_bot()
