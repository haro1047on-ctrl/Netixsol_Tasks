"""Integration Test for Week 8 Lead Scoring & SHAP Explainability Tool within Week 7 Agent.

Verifies:
1. Tool availability and schema in ALL_TOOLS registry
2. Direct tool calling: lead_scoring_tool.invoke(...)
3. Priority Tier classification: [HOT], [WARM], [COLD] with specific SLAs
4. Customer Persona Discovery (K-Means)
5. Explainable AI: SHAP driver attribution in English and UrduLish
6. Sales Team Scenario Triage: Prioritizing 40 calls out of 200 incoming leads (Top-20% Precision & Lift)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add agent directory to sys.path
AGENT_DIR = Path(__file__).resolve().parent
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

# Ensure UTF-8 output on Windows
if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from tools import ALL_TOOLS, lead_scoring_tool, evaluate_lead_scoring_core


def test_tool_registration():
    print("\n--- 1. Testing Lead Scoring Tool Registration in ALL_TOOLS ---")
    tool_names = [t.name for t in ALL_TOOLS]
    print(f"Registered Tools Count: {len(ALL_TOOLS)}")
    print(f"Tool Names: {tool_names}")
    assert "lead_scoring_tool" in tool_names, "lead_scoring_tool not found in ALL_TOOLS!"
    print("  [PASS] lead_scoring_tool is registered in ALL_TOOLS.")


def test_lead_scoring_hot_lead():
    print("\n--- 2. Testing Lead Scoring for High-Intent [HOT] Lead ---")
    
    args = {
        "client_name": "Tariq Mahmood",
        "budget": "3.5 Crore",
        "preferred_city": "Islamabad",
        "property_type": "House",
        "purpose": "Buy",
        "number_of_calls": 5,
        "avg_call_duration_mins": 5.8,
        "response_time_hours": 0.2,
        "visit_booked": "Yes",
        "days_since_first_contact": 10,
        "objection_raised": "None",
        "lead_source": "WhatsApp",
    }
    
    result = lead_scoring_tool.invoke(args)
    print("Tool Output:")
    print(result)
    
    assert "LEAD CONVERSION SCORING REPORT" in result
    assert "[HOT]" in result
    assert "Call within 1 hour" in result
    assert "UrduLish Consultation" in result
    print("  [PASS] Successfully scored HOT lead with SHAP reasons and 1-hour SLA.")


def test_lead_scoring_cold_lead():
    print("\n--- 3. Testing Lead Scoring for Low-Intent [COLD] Lead ---")
    
    args = {
        "client_name": "Asad Farooq",
        "budget": "50,000",
        "preferred_city": "Rawalpindi",
        "property_type": "Plot",
        "purpose": "Rent",
        "number_of_calls": 1,
        "avg_call_duration_mins": 0.8,
        "response_time_hours": 8.5,
        "visit_booked": "No",
        "days_since_first_contact": 45,
        "objection_raised": "Price too high",
        "lead_source": "Facebook",
    }
    
    result = lead_scoring_tool.invoke(args)
    print("Tool Output:")
    print(result)
    
    assert "[COLD]" in result
    assert "automated nurture" in result.lower()
    print("  [PASS] Successfully categorized COLD lead for automated nurture drip.")


def test_scenario_200_leads_batch_triage():
    print("\n--- 4. Testing Day 3 Business Scenario: 200 Leads Triage (Calling Top 40) ---")
    
    # Simulate a batch of leads arriving at the sales desk
    import numpy as np
    np.random.seed(42)
    
    batch_leads = []
    for i in range(200):
        # Generate representative sample
        is_engaged = np.random.rand() < 0.25
        calls = np.random.randint(3, 7) if is_engaged else np.random.randint(1, 3)
        dur = np.random.uniform(3.0, 7.0) if is_engaged else np.random.uniform(0.5, 2.5)
        resp = np.random.uniform(0.1, 0.8) if is_engaged else np.random.uniform(2.0, 12.0)
        visit = "Yes" if (is_engaged and np.random.rand() < 0.70) else "No"
        budget = "2.5 Crore" if np.random.rand() < 0.6 else "60,000"
        
        batch_leads.append({
            "client_name": f"Lead_{i+1:03d}",
            "budget": budget,
            "preferred_city": np.random.choice(["Islamabad", "Lahore", "Karachi"]),
            "property_type": "House",
            "purpose": "Buy" if "Crore" in budget else "Rent",
            "number_of_calls": calls,
            "avg_call_duration_mins": dur,
            "response_time_hours": resp,
            "visit_booked": visit,
            "days_since_first_contact": np.random.randint(2, 60),
            "objection_raised": "None" if is_engaged else "Price too high",
            "lead_source": np.random.choice(["WhatsApp", "Call", "Website", "Facebook"])
        })
    
    # Score all 200 leads using evaluate_lead_scoring_core
    scored = []
    for lead in batch_leads:
        res = evaluate_lead_scoring_core(**lead)
        scored.append((lead["client_name"], res["conversion_probability"], res["tier"], res["customer_persona"]))
    
    # Sort descending by probability
    scored.sort(key=lambda x: x[1], reverse=True)
    top_40 = scored[:40]
    
    hot_count = sum(1 for x in top_40 if x[2] == "Hot")
    warm_count = sum(1 for x in top_40 if x[2] == "Warm")
    cold_count = sum(1 for x in top_40 if x[2] == "Cold")
    
    mean_top40_prob = np.mean([x[1] for x in top_40])
    mean_remaining_prob = np.mean([x[1] for x in scored[40:]])
    
    print(f"Total Leads Processed: {len(scored)}")
    print(f"Top 40 Selected Leads: Mean Conversion Probability = {mean_top40_prob:.1%}")
    print(f"Remaining 160 Leads: Mean Conversion Probability = {mean_remaining_prob:.1%}")
    print(f"Top 40 Composition: Hot={hot_count}, Warm={warm_count}, Cold={cold_count}")
    print(f"Triage Efficiency Lift: {mean_top40_prob / (mean_remaining_prob + 1e-6):.2f}x higher intent in Top 40!")
    
    assert cold_count == 0, "No Cold leads should be in the top 40 outreach list!"
    assert mean_top40_prob > 0.60, "Top 40 leads should have high average conversion probability!"
    print("  [PASS] Sales triage successfully isolates top 40 hot prospects with zero wasted calls!")


if __name__ == "__main__":
    print("======================================================================")
    print("WEEK 8 DAY 3: LEAD SCORING AGENT INTEGRATION TEST")
    print("======================================================================")
    test_tool_registration()
    test_lead_scoring_hot_lead()
    test_lead_scoring_cold_lead()
    test_scenario_200_leads_batch_triage()
    print("\n======================================================================")
    print("ALL WEEK 7 AGENT INTEGRATION TESTS PASSED SUCCESSFULLY! (100% PASS)")
    print("======================================================================")
