"""Week 8 Day 3 Extension Tool: AI Lead Scoring, Segmentation & SHAP Explainability Engine.

Integrates the Week 8 Machine Learning Lead Scoring model (LightGBM/CatBoost + SHAP + K-Means Personas)
into the Week 7 Real Estate Voice & LangGraph Agent.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union
from langchain_core.tools import tool

# Reference Week 8 Day 3 directories
WEEK8_DAY3_DIR = Path(__file__).resolve().parent.parent.parent.parent / "week8" / "Day3"
WEEK8_SRC_DIR = WEEK8_DAY3_DIR / "src"

if str(WEEK8_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(WEEK8_SRC_DIR))

_LEAD_ENGINE: Optional[Any] = None


def get_lead_scoring_engine() -> Any:
    """Returns singleton instance of LeadScoringEngine."""
    global _LEAD_ENGINE
    if _LEAD_ENGINE is None:
        try:
            from lead_inference import LeadScoringEngine
            _LEAD_ENGINE = LeadScoringEngine()
        except Exception as e:
            print(f"Warning: Could not initialize full ML lead scoring engine: {e}")
            return None
    return _LEAD_ENGINE


def parse_budget_to_pkr(budget_input: Union[str, float, int]) -> float:
    """Converts Pakistani colloquial budget strings (e.g. '2.5 Crore', '150 Lacs') to PKR."""
    if isinstance(budget_input, (int, float)):
        return float(budget_input)

    text = str(budget_input).strip().lower().replace(",", "")
    num_match = re.search(r"(\d+(\.\d+)?)", text)
    if not num_match:
        return 15000000.0  # 1.5 Cr default

    val = float(num_match.group(1))
    if any(k in text for k in ["crore", "cr", "kror"]):
        return val * 10000000.0
    elif any(k in text for k in ["lac", "lakh"]):
        return val * 100000.0
    elif any(k in text for k in ["k", "thousand"]):
        return val * 1000.0
    return val


def evaluate_lead_scoring_core(
    client_name: str = "Lead Prospect",
    budget: Union[str, float, int] = "2.5 Crore",
    preferred_city: str = "Islamabad",
    property_type: str = "House",
    purpose: str = "Buy",
    number_of_calls: int = 4,
    avg_call_duration_mins: float = 4.5,
    response_time_hours: float = 0.3,
    visit_booked: str = "Yes",
    days_since_first_contact: int = 15,
    objection_raised: str = "None",
    lead_source: str = "WhatsApp",
) -> Dict[str, Any]:
    """Core evaluation function for lead scoring, tiering, personas, and explainability."""
    engine = get_lead_scoring_engine()
    budget_pkr = parse_budget_to_pkr(budget)

    lead_data = {
        "client_name": client_name,
        "budget_pkr": budget_pkr,
        "preferred_city": preferred_city,
        "property_type": property_type,
        "purpose": purpose,
        "number_of_calls": int(number_of_calls),
        "avg_call_duration_mins": float(avg_call_duration_mins),
        "response_time_hours": float(response_time_hours),
        "visit_booked": visit_booked,
        "days_since_first_contact": int(days_since_first_contact),
        "objection_raised": objection_raised,
        "lead_source": lead_source,
    }

    if engine is None:
        # Fallback heuristic if models are not loaded
        is_hot = visit_booked == "Yes" and number_of_calls >= 3
        tier = "Hot" if is_hot else "Warm"
        prob = 0.85 if is_hot else 0.45
        return {
            "client_name": client_name,
            "tier": tier,
            "badge": f"[{tier.upper()}]",
            "conversion_probability": prob,
            "conversion_pct": f"{prob*100:.1f}%",
            "customer_persona": "Serious First-Time Homebuyer",
            "sla": "Call within 1 hour" if is_hot else "Call within 24 hours",
            "explanation_ur": f"Yeh lead {tier} hai kyun ke visit {'confirm' if is_hot else 'pending'} hai.",
            "next_best_action_en": "Contact immediately." if is_hot else "Send brochure on WhatsApp.",
            "consultation_statement": f"[{tier.upper()}] {client_name} (Conversion: {prob*100:.1f}%)"
        }

    return engine.score_lead(lead_data)


@tool
def lead_scoring_tool(
    client_name: str,
    budget: str,
    preferred_city: str = "Lahore",
    property_type: str = "House",
    purpose: str = "Buy",
    number_of_calls: int = 3,
    avg_call_duration_mins: float = 3.5,
    response_time_hours: float = 0.5,
    visit_booked: str = "Yes",
    days_since_first_contact: int = 14,
    objection_raised: str = "None",
    lead_source: str = "WhatsApp",
) -> str:
    """Predicts conversion probability and priority tier (HOT/WARM/COLD) for incoming leads.
    
    Identifies customer personas (First-Time Buyer, Overseas Investor, Budget Renter),
    explains predictions in plain English and UrduLish using SHAP values, and recommends
    the Next Best Action (call within 1 hour, send WhatsApp property options, or automated drip).
    
    Args:
        client_name: Full name of the lead (e.g. 'Zubair Sheikh')
        budget: Stated budget in PKR or colloquial text (e.g. '2.5 Crore', '150 Lacs', '45,000')
        preferred_city: Target city (Lahore, Karachi, Islamabad, Rawalpindi, Faisalabad)
        property_type: Type of property (House, Flat, Plot, Commercial)
        purpose: 'Buy' or 'Rent'
        number_of_calls: Total phone interactions to date
        avg_call_duration_mins: Average call length in minutes
        response_time_hours: Hours taken by client to respond to inquiries
        visit_booked: 'Yes' or 'No' whether an in-person site visit is scheduled
        days_since_first_contact: Days since initial inquiry was received
        objection_raised: Primary objection ('None', 'Price too high', 'Location too far', 'Waiting for family approval')
        lead_source: Channel of contact ('WhatsApp', 'Call', 'Website', 'Facebook')
        
    Returns:
        Formatted Lead Scoring Consultation Report with priority tier, SLA, persona, and UrduLish rationale.
    """
    res = evaluate_lead_scoring_core(
        client_name=client_name,
        budget=budget,
        preferred_city=preferred_city,
        property_type=property_type,
        purpose=purpose,
        number_of_calls=number_of_calls,
        avg_call_duration_mins=avg_call_duration_mins,
        response_time_hours=response_time_hours,
        visit_booked=visit_booked,
        days_since_first_contact=days_since_first_contact,
        objection_raised=objection_raised,
        lead_source=lead_source,
    )

    badge = res.get("badge", f"[{res['tier'].upper()}]")
    drivers_str = ", ".join(res.get("top_positive_drivers", ["High engagement"]))

    report = [
        "=" * 60,
        f"  LEAD CONVERSION SCORING REPORT: {badge}",
        "=" * 60,
        f"Client: {res['client_name']} | Source: {lead_source} | City: {preferred_city}",
        f"Stated Budget: {budget} | Purpose: {purpose} ({property_type})",
        "-" * 60,
        f"Conversion Probability: {res['conversion_pct']} (Raw: {res['conversion_probability']})",
        f"Priority Tier: {badge} | SLA: {res['sla']}",
        f"Customer Persona: {res['customer_persona']}",
        f"Persona Profile: {res.get('persona_description', '')}",
        "-" * 60,
        "EXPLAINABLE AI INSIGHTS (SHAP DRIVERS):",
        f"Key Factors: {drivers_str}",
        f"English Consultation: {res['explanation_en']}",
        f"UrduLish Consultation: {res['explanation_ur']}",
        "-" * 60,
        f"RECOMMENDED NEXT BEST ACTION: {res['next_best_action_en']}",
        f"Urdu Action Plan: {res['next_best_action_ur']}",
        "=" * 60,
    ]
    return "\n".join(report)
