"""
================================================================================
INTERACTIVE AFL CHAT AGENT TERMINAL
================================================================================
An interactive CLI assistant to test the AFL Chat Agent live in your terminal!

Features:
- Live multi-turn dialogue with memory
- Real-time tool call visibility
- Automatic numerical grounding verification
- Commands: /reset (clear memory), /help (show tips), /exit or quit (exit)
"""

import sys
import os
from dotenv import load_dotenv

# Reconfigure stdout for UTF-8 compatibility on Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

load_dotenv()

from afl_chat_agent import AFLChatAgent


def print_banner():
    print("=" * 80)
    print("           AFL DOMAIN-SCOPED CHAT ASSISTANT -- INTERACTIVE TERMINAL")
    print("=" * 80)
    print(" - Domain Scope  : AFL Teams, Players, Season Stats, Match Records & Rules")
    print(" - Retrieval     : Grounded in real CSV datasets (Zero Hallucination)")
    print(" - Refusals      : Off-topic questions declined & redirected to AFL")
    print(" - Commands      : type '/reset' to clear chat memory, 'exit' to quit")
    print("=" * 80)
    print()


def run_interactive_terminal():
    print_banner()

    try:
        agent = AFLChatAgent()
    except Exception as e:
        print(f"[ERROR] Failed to initialize AFL Chat Agent: {e}")
        return

    print("Agent ready! Ask any AFL question (or try an off-topic prompt to test guardrails):\n")

    while True:
        try:
            user_input = input("\nUser > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat. Goodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "/exit", "/quit"]:
            print("Goodbye! Go Footy!")
            break

        if user_input.lower() == "/reset":
            agent.reset()
            print("[INFO] Conversation memory cleared.")
            continue

        if user_input.lower() == "/help":
            print("\n--- QUICK TIPS ---")
            print("1. Stat query    : 'How many disposals did Gary Ablett get in 2018?'")
            print("2. Team query    : 'How did Collingwood perform in the 2023 season?'")
            print("3. Rule query    : 'What is a mark inside 50 in AFL rules?'")
            print("4. Off-topic test: 'Who won the NBA finals?' or 'Write python code'")
            print("5. Multi-turn    : Ask follow-up questions like 'How did he do in round 15?'")
            continue

        print("\n[Thinking...]")
        res = agent.chat(user_input)

        # Print tools used
        if res["tools_called"]:
            print(f"[Tools Invoked: {', '.join(res['tools_called'])}]")
        else:
            print("[Tools Invoked: None (Direct Scope/Refusal Response)]")

        # Print answer
        print(f"\nAgent > {res['answer']}")

        # Print grounding report
        verdict = res["grounding_report"]["verdict"]
        print(f"\n[Grounding Check: {verdict}]")
        print("-" * 80)


if __name__ == "__main__":
    run_interactive_terminal()
