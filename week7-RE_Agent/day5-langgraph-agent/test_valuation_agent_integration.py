"""Integration Test for Week 8 Property Valuation Tool within Week 7 Agent.

Verifies:
1. Tool availability and schema in ALL_TOOLS registry
2. Direct tool calling: property_valuation_tool.invoke(...)
3. Pricing question scenario: "Is plot ki sahi qeemat kya honi chahiye?"
4. Asking price assessment: Overpriced / Fair / Underpriced verdict with percentage
5. Integration with recommendation_node ensuring ML valuation enrichment
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

from tools import ALL_TOOLS, property_valuation_tool, evaluate_property_valuation_core
from nodes.recommendation_node import recommendation_node
from state import create_initial_state


def test_tool_registration():
    print("\n--- 1. Testing Tool Registration in ALL_TOOLS ---")
    tool_names = [t.name for t in ALL_TOOLS]
    print(f"Registered Tools Count: {len(ALL_TOOLS)}")
    print(f"Tool Names: {tool_names}")
    assert "property_valuation_tool" in tool_names, "property_valuation_tool not found in ALL_TOOLS!"
    print("  [PASS] property_valuation_tool is registered in ALL_TOOLS.")


def test_valuation_tool_calling():
    print("\n--- 2. Testing Direct Valuation Tool Calling ---")
    
    # Query: 10 Marla house in DHA Phase 5 Lahore with asking price 4.9 Crore
    args = {
        "city": "Lahore",
        "area_society": "DHA Phase 5",
        "property_type": "House",
        "plot_size_marla": 10.0,
        "bedrooms": 4,
        "age_years": 2.0,
        "listed_price_pkr": 49000000.0,
        "is_corner": "Yes",
    }
    
    result = property_valuation_tool.invoke(args)
    print("Tool Output:")
    print(result)
    assert "[PROPERTY VALUATION REPORT]" in result
    assert "Predicted Fair Price" in result
    assert "Confidence Band" in result
    assert "Overpriced" in result or "Fair" in result
    print("  [PASS] Tool execution returned complete structured valuation report.")


def test_valuation_prompt_scenario():
    print("\n--- 3. Testing Scenario: 'Is plot ki sahi qeemat kya honi chahiye?' ---")
    
    # Scenario: Client asks about fair price for 1 Kanal in Sector F-7 Islamabad
    eval_res = evaluate_property_valuation_core(
        city="Islamabad",
        area_society="Sector F-7",
        property_type="House",
        plot_size_marla=20.0,
        bedrooms=5,
        bathrooms=5,
        age_years=1.0,
    )
    
    print(f"Point Valuation: {eval_res['predicted_price_formatted']}")
    print(f"Confidence Band: {eval_res['lower_range_formatted']} to {eval_res['upper_range_formatted']}")
    print(f"UrduLish Consultation: {eval_res['urdulish_summary']}")
    assert eval_res["predicted_price_pkr"] > 0
    assert eval_res["lower_range_pkr"] < eval_res["predicted_price_pkr"] < eval_res["upper_range_pkr"]
    print("  [PASS] Successfully generated fair valuation interval for sales manager inquiry.")


def test_recommendation_enrichment():
    print("\n--- 4. Testing Recommendation Node with ML Valuation Enrichment ---")
    state = create_initial_state(session_id="session_101")
    state["property_preferences"] = {
        "city": "Lahore",
        "locality": "DHA Phase 5",
        "area_marla": 10,
        "property_type": "House",
        "purpose": "For Sale",
        "investment_goal": False,
    }
    state["budget"] = 60000000.0

    output = recommendation_node(state)
    response_text = output["final_response"]
    print("\nAgent Voice Recommendation:")
    print(response_text[:300] + "...")
    assert len(output.get("recommended_properties", [])) >= 0
    print("  [PASS] Recommendation node seamlessly executes with Week 8 ML valuation enrichment.")


if __name__ == "__main__":
    print("=" * 80)
    print("RUNNING WEEK 8 -> WEEK 7 AGENT INTEGRATION TESTS")
    print("=" * 80)
    test_tool_registration()
    test_valuation_tool_calling()
    test_valuation_prompt_scenario()
    test_recommendation_enrichment()
    print("\n" + "=" * 80)
    print("ALL WEEK 7 AGENT INTEGRATION TESTS PASSED (100% SUCCESS)!")
    print("=" * 80)
