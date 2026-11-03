"""RealEstate Hub Unified AI Voice Agent & ML Platform — Master Runner.

Provides a unified interface across all Week 7 (Telephony Voice Agent, LangGraph, RAG, Scheduling)
and Week 8 (ML Property Valuation, Lead Scoring, Customer Personas, MLOps) capabilities.

Usage:
  python run_unified_agent.py --cli        # Interactive conversational CLI (UrduLish, Valuation, Booking)
  python run_unified_agent.py --serve      # Start unified FastAPI server (Vapi SSE + ML Serving + Speech)
  python run_unified_agent.py --dashboard  # Launch Streamlit Executive Dashboard
  python run_unified_agent.py --test       # Run master verification test suite (100% automated pass)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Paths configuration
WORKSPACE_ROOT = Path(__file__).resolve().parent
WEEK7_AGENT_DIR = WORKSPACE_ROOT / "week7-RE_Agent" / "day5-langgraph-agent"
WEEK7_DAY6_DIR = WORKSPACE_ROOT / "week7-RE_Agent" / "day6-evaluation-security"
WEEK8_DAY2_DIR = WORKSPACE_ROOT / "week8" / "Day2"
WEEK8_DAY3_DIR = WORKSPACE_ROOT / "week8" / "Day3"
WEEK8_DAY4_DIR = WORKSPACE_ROOT / "week8" / "Day4"

# Add all relevant source directories to sys.path
for p in [
    str(WEEK7_AGENT_DIR),
    str(WEEK7_DAY6_DIR),
    str(WEEK8_DAY2_DIR / "src"),
    str(WEEK8_DAY3_DIR / "src"),
    str(WEEK8_DAY4_DIR / "src"),
]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Set Windows stdout UTF-8 encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def run_cli():
    """Launch interactive conversational CLI with real-time valuation, lead scoring, and appointment scheduling."""
    import uuid
    from graph import run_agent_turn
    from logger import default_agent_logger
    from state import create_initial_state

    session_id = f"session_{uuid.uuid4().hex[:6]}"
    default_agent_logger.session_id = session_id
    state = create_initial_state(session_id=session_id)

    print("\n" + "=" * 80)
    print(" 🏡  REALESTATE HUB UNIFIED AI VOICE AGENT — INTERACTIVE CONSULTANT  🏡 ")
    print("=" * 80)
    print(f" Session ID: {session_id}")
    print(" Active Engines:")
    print("   • CatBoost Property Valuation Engine (R²=0.988 with Quantile Bands)")
    print("   • LightGBM Lead Conversion Classifier (PR-AUC 0.562 & K-Means Personas)")
    print("   • LangGraph 9-Node Stateful Conversational Machine (UrduLish)")
    print("   • Verified SQL Database (750 Listings) & ChromaDB RAG")
    print(" Commands: 'state' (inspect AgentState), 'export' (save traces), 'exit' (quit)")
    print("=" * 80 + "\n")

    initial_turn = run_agent_turn("Hello", current_state=state, session_id=session_id)
    state = initial_turn
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
                print("Allah Hafiz!\n")
                break

            if user_input.lower() == "state":
                import json
                clean_state = {
                    "intent": state.get("intent"),
                    "budget": state.get("budget"),
                    "property_preferences": state.get("property_preferences"),
                    "user_profile": state.get("user_profile"),
                    "appointment_status": state.get("appointment_status"),
                    "clarification_needed": state.get("clarification_needed"),
                    "last_node": state.get("last_node"),
                }
                print("\n--- CURRENT AGENT STATE ---")
                print(json.dumps(clean_state, indent=2))
                print("---------------------------\n")
                continue

            if user_input.lower() == "export":
                traces = default_agent_logger.export_traces()
                print(f"✅ Traces exported:\n   JSON: {traces.get('json_path')}\n   Markdown: {traces.get('md_path')}\n")
                continue

            # Process turn through unified LangGraph
            state = run_agent_turn(user_input, current_state=state, session_id=session_id)
            print(f"\n🤖 [AI Agent]: {state.get('final_response')}\n")

        except (KeyboardInterrupt, EOFError):
            default_agent_logger.export_traces()
            print("\nSession ended. Traces saved.\n")
            break


def run_serve():
    """Start unified FastAPI server hosting both Vapi/WebRTC streaming and Week 8 ML endpoints."""
    import uvicorn
    from vapi_server import app as unified_app

    print("\n" + "=" * 80)
    print(" 🚀 STARTING UNIFIED REALESTATE HUB PRODUCTION API SERVER")
    print("=" * 80)
    print(" • Telephony & WebRTC SSE Endpoint: POST /vapi/llm/chat/completions")
    print(" • Free Neural Urdu TTS Endpoint:   POST /voice/synthesize")
    print(" • ML Valuation Endpoints:          POST /predict/price, POST /explain/price")
    print(" • ML Lead Scoring Endpoints:       POST /predict/lead-score, POST /explain/lead")
    print(" • Batch Prediction Endpoint:       POST /predict/batch")
    print(" • Health & Telemetry Probes:       GET /health, GET /metrics")
    print(" • Interactive Swagger Docs:        http://localhost:8000/docs")
    print("=" * 80 + "\n")

    uvicorn.run(unified_app, host="0.0.0.0", port=8000)


def run_dashboard():
    """Launch Streamlit Executive Dashboard."""
    dashboard_path = WEEK8_DAY4_DIR / "app_dashboard.py"
    print(f"\n🚀 Launching Streamlit Executive Dashboard from {dashboard_path} ...\n")
    cmd = [sys.executable, "-m", "streamlit", "run", str(dashboard_path)]
    subprocess.run(cmd)


def run_test():
    """Run master test suite across Week 7 and Week 8 modules."""
    print("\n" + "=" * 80)
    print(" 🧪 RUNNING REALESTATE HUB UNIFIED MASTER VERIFICATION SUITE")
    print("=" * 80 + "\n")

    # 1. Day 5 LangGraph Core Suite
    print("▶️ [1/5] Testing LangGraph State Machine & Business Invariants...")
    res1 = subprocess.run([sys.executable, str(WEEK7_AGENT_DIR / "test_day5_agent.py")])
    if res1.returncode != 0:
        print("❌ LangGraph Core Suite failed!")
        sys.exit(1)

    # 2. Week 8 Valuation Integration
    print("\n▶️ [2/5] Testing Property Valuation ML Tool Integration...")
    res2 = subprocess.run([sys.executable, str(WEEK7_AGENT_DIR / "test_valuation_agent_integration.py")])
    if res2.returncode != 0:
        print("❌ Valuation ML Integration failed!")
        sys.exit(1)

    # 3. Week 8 Lead Scoring Integration
    print("\n▶️ [3/5] Testing Lead Scoring ML Tool Integration...")
    res3 = subprocess.run([sys.executable, str(WEEK7_AGENT_DIR / "test_lead_scoring_agent_integration.py")])
    if res3.returncode != 0:
        print("❌ Lead Scoring ML Integration failed!")
        sys.exit(1)

    # 4. Day 6 Security Guardrails & Health Check
    print("\n▶️ [4/5] Testing Production Pre-flight Health & Security Guardrails...")
    res4a = subprocess.run([sys.executable, str(WEEK7_DAY6_DIR / "run_day6.py"), "--health"])
    res4b = subprocess.run([sys.executable, str(WEEK7_DAY6_DIR / "run_day6.py"), "--security"])
    if res4a.returncode != 0 or res4b.returncode != 0:
        print("❌ Security Guardrails Suite failed!")
        sys.exit(1)

    # 5. Free Speech Service & Normalizer
    print("\n▶️ [5/5] Testing Free-First Pakistani Urdu Speech Synthesis & Normalizer...")
    res5 = subprocess.run([
        sys.executable, "-c",
        """
import sys
sys.path.insert(0, r'week7-RE_Agent/day5-langgraph-agent')
from speech.free_speech_service import UrduTextNormalizer, default_free_speech_service
assert UrduTextNormalizer.normalize_currency_pkr('1.5 crore') == 15000000.0
assert UrduTextNormalizer.normalize_plot_size('1 kanal')[0] == 20.0
audio = default_free_speech_service.synthesize_speech('RealEstate Hub AI Voice Agent tayyar hai.')
assert audio.exists() and audio.stat().st_size > 1000
print('  [PASS] Free Edge-TTS & Urdu normalization verified.')
"""
    ])
    if res5.returncode != 0:
        print("❌ Free Speech Service failed!")
        sys.exit(1)

    print("\n" + "=" * 80)
    print(" ✅ ALL UNIFIED SYSTEM TESTS COMPLETED WITH 100% SUCCESS!")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="RealEstate Hub Unified Master Runner")
    parser.add_argument("--cli", action="store_true", help="Launch interactive conversational CLI")
    parser.add_argument("--serve", action="store_true", help="Start unified FastAPI production server")
    parser.add_argument("--dashboard", action="store_true", help="Launch Streamlit Executive Dashboard")
    parser.add_argument("--test", action="store_true", help="Run master verification test suite")

    args = parser.parse_args()

    if args.cli:
        run_cli()
    elif args.serve:
        run_serve()
    elif args.dashboard:
        run_dashboard()
    elif args.test:
        run_test()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
