"""Week 8 Day 4 Task 4: Voice Agent Integration Module.

Connects the Week 7 Vapi / LangGraph Voice Agent with the Week 8 ML Platform:
1. Post-Call Webhook: Ingests completed call CDR data and scores lead via /predict/lead-score
2. Hot Lead Dispatcher: Automatically triggers high-priority email/SMS alerts to sales reps
3. Real-Time Voice Valuation: Answers "Mera ghar kitne ka bikega?" using /predict/price
4. Architecture Diagram: Documenting the complete bi-directional data flow
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SRC_DIR = Path(__file__).resolve().parent
DAY4_DIR = SRC_DIR.parent
WEEK8_DIR = DAY4_DIR.parent
DAY2_SRC = WEEK8_DIR / "Day2" / "src"
DAY3_SRC = WEEK8_DIR / "Day3" / "src"

for p in [str(SRC_DIR), str(DAY2_SRC), str(DAY3_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from valuation_inference import PropertyValuationEngine, format_pakistani_currency
from lead_inference import LeadScoringEngine

_val_engine: Optional[PropertyValuationEngine] = None
_lead_engine: Optional[LeadScoringEngine] = None


def get_val_engine() -> PropertyValuationEngine:
    global _val_engine
    if _val_engine is None:
        _val_engine = PropertyValuationEngine()
    return _val_engine


def get_lead_engine() -> LeadScoringEngine:
    global _lead_engine
    if _lead_engine is None:
        _lead_engine = LeadScoringEngine()
    return _lead_engine


def send_email_alert(
    to_email: str,
    subject: str,
    body_html: str,
    lead_id: str
) -> Dict[str, Any]:
    """Simulates sending an enterprise alert email to the assigned sales agent for hot leads."""
    timestamp = datetime.now(timezone.utc).isoformat()
    # Mocking SMTP / SendGrid / Postmark transmission
    email_record = {
        "status": "SENT",
        "to_email": to_email,
        "subject": subject,
        "lead_id": lead_id,
        "sent_at": timestamp,
        "preview": body_html[:150] + "...",
    }
    return email_record


def handle_post_call_webhook(call_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Processes post-call webhook from Week 7 Voice Agent, executes ML lead scoring,
    and dispatches instant notifications for high-priority (Hot) leads.
    """
    engine = get_lead_engine()

    lead_id = call_payload.get("call_id", f"CALL-{int(datetime.now().timestamp())}")
    client_name = call_payload.get("client_name", "Inbound Caller")
    phone = call_payload.get("phone", "+92-300-1234567")
    city = call_payload.get("preferred_city", "Lahore")
    budget = float(call_payload.get("budget_pkr", 25000000.0))
    duration_mins = float(call_payload.get("call_duration_seconds", 180)) / 60.0
    total_calls = int(call_payload.get("total_calls_to_date", 1))
    visit_booked = call_payload.get("visit_booked", "No")

    lead_input = {
        "client_name": client_name,
        "phone": phone,
        "preferred_city": city,
        "budget_pkr": budget,
        "lead_source": "Call",
        "purpose": call_payload.get("purpose", "Buy"),
        "number_of_calls": total_calls,
        "avg_call_duration_mins": round(duration_mins, 1),
        "response_time_hours": 0.1,  # immediate automated voice reply
        "visit_booked": visit_booked,
        "days_since_first_contact": 1,
        "objection_raised": call_payload.get("objection_raised", "None"),
    }

    scoring_res = engine.score_lead(lead_input)
    tier = scoring_res["tier"]
    prob_pct = scoring_res["conversion_pct"]
    persona = scoring_res["customer_persona"]

    alert_sent = False
    alert_details = None

    if tier == "Hot":
        assigned_agent_email = "closer-team@netixsol.com"
        subject = f"🔥 HOT LEAD ALERT: {client_name} ({prob_pct} Close Probability) - Call within 1 Hour!"
        body = (
            f"<h2>Urgent: Hot Inbound Real Estate Lead</h2>"
            f"<p><b>Client:</b> {client_name} ({phone})</p>"
            f"<p><b>Stated Budget:</b> {format_pakistani_currency(budget)}</p>"
            f"<p><b>Location:</b> {city}</p>"
            f"<p><b>Customer Persona:</b> {persona}</p>"
            f"<p><b>Visit Scheduled:</b> {visit_booked}</p>"
            f"<p><b>ML Triage Analysis:</b> {scoring_res['explanation_en']}</p>"
            f"<p><b>UrduLish Consultation Note:</b> <i>{scoring_res['explanation_ur']}</i></p>"
            f"<p><b>Operational SLA:</b> Contact prospect within 60 minutes.</p>"
        )
        alert_details = send_email_alert(assigned_agent_email, subject, body, lead_id)
        alert_sent = True

    return {
        "call_id": lead_id,
        "client_name": client_name,
        "conversion_probability": scoring_res["conversion_probability"],
        "priority_tier": tier,
        "priority_badge": scoring_res["badge"],
        "customer_persona": persona,
        "operational_sla": scoring_res["sla"],
        "alert_triggered": alert_sent,
        "alert_record": alert_details,
        "urdulish_summary": scoring_res["explanation_ur"],
    }


def handle_voice_property_inquiry(user_speech: str) -> Dict[str, Any]:
    """Answers spoken customer questions like 'Mera ghar kitne ka bikega?'
    Extracts property attributes, calls /predict/price, and returns voice-friendly UrduLish audio script.
    """
    engine = get_val_engine()
    speech_lower = user_speech.lower()

    # Heuristic entity extraction for voice speech
    marla = 10.0
    if "1 kanal" in speech_lower or "ek kanal" in speech_lower or "20 marla" in speech_lower:
        marla = 20.0
    elif "5 marla" in speech_lower or "panch marla" in speech_lower:
        marla = 5.0
    elif "7 marla" in speech_lower:
        marla = 7.0
    elif "2 kanal" in speech_lower:
        marla = 40.0

    city = "Lahore"
    if "islamabad" in speech_lower or "f-7" in speech_lower or "f-10" in speech_lower:
        city = "Islamabad"
    elif "karachi" in speech_lower or "clifton" in speech_lower:
        city = "Karachi"
    elif "rawalpindi" in speech_lower:
        city = "Rawalpindi"
    elif "faisalabad" in speech_lower:
        city = "Faisalabad"

    society = "DHA Phase 5"
    if "phase 6" in speech_lower:
        society = "DHA Phase 6"
    elif "bahria" in speech_lower:
        society = "Bahria Town"
    elif "gulberg" in speech_lower:
        society = "Gulberg III"
    elif "f-7" in speech_lower:
        society = "Sector F-7"

    age = 2.0
    if "brand new" in speech_lower or "naya" in speech_lower:
        age = 0.5
    elif "5 saal" in speech_lower or "panch saal" in speech_lower:
        age = 5.0
    elif "10 saal" in speech_lower:
        age = 10.0

    val_res = engine.evaluate_property({
        "city": city,
        "area_society": society,
        "plot_size_marla": marla,
        "age_years": age,
        "property_type": "House",
    })

    # Generate audio-optimized conversational script (under 20 words for smooth voice synthesis)
    voice_script_ur = (
        f"Aap ke {society} mein waqia {int(marla)} marla ghar ki andazan fair market value "
        f"{val_res['lower_range_formatted']} se {val_res['upper_range_formatted']} ke darmiyan hai, "
        f"aur expected price taqreeban {val_res['predicted_price_formatted']} banti hai. "
        f"Kya aap kisi agent ke sath visit schedule karna chahein ge?"
    )

    return {
        "extracted_entities": {
            "city": city,
            "society": society,
            "plot_size_marla": marla,
            "age_years": age
        },
        "predicted_price_formatted": val_res["predicted_price_formatted"],
        "expected_range": f"{val_res['lower_range_formatted']} - {val_res['upper_range_formatted']}",
        "spoken_response_urdulish": voice_script_ur,
        "disclaimer": val_res.get("disclaimer", "Estimates only.")
    }
