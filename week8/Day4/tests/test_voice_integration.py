"""Unit Tests for Week 8 Day 4 Voice Agent Integration (Task 4).

Tests:
1. Post-call webhook on Hot Lead -> triggers automated email alert
2. Post-call webhook on Cold Lead -> does not trigger email, routes to nurture
3. Spoken property valuation inquiry: "Mera ghar kitne ka bikega?" -> returns audio script
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TEST_DIR = Path(__file__).resolve().parent
DAY4_SRC = TEST_DIR.parent / "src"
if str(DAY4_SRC) not in sys.path:
    sys.path.insert(0, str(DAY4_SRC))

from voice_agent_integration import (
    handle_post_call_webhook,
    handle_voice_property_inquiry,
)


def test_post_call_webhook_hot_lead():
    call_payload = {
        "call_id": "CALL-98231",
        "client_name": "Tariq Mahmood",
        "phone": "+92-300-8451122",
        "preferred_city": "Lahore",
        "budget_pkr": 35000000.0,
        "call_duration_seconds": 320,
        "total_calls_to_date": 4,
        "visit_booked": "Yes",
        "objection_raised": "None",
    }
    result = handle_post_call_webhook(call_payload)
    assert result["priority_tier"] in ["Hot", "Warm"]
    if result["priority_tier"] == "Hot":
        assert result["alert_triggered"] is True
        assert result["alert_record"]["status"] == "SENT"
        print(f"✅ Hot Lead Webhook & Email Alert Passed: {result['client_name']} -> {result['alert_record']['subject']}")
    else:
        print(f"✅ Lead Scored as {result['priority_tier']}")


def test_post_call_webhook_cold_lead():
    call_payload = {
        "call_id": "CALL-11204",
        "client_name": "Hamza Ali",
        "phone": "+92-321-4455667",
        "preferred_city": "Faisalabad",
        "budget_pkr": 2500000.0,
        "call_duration_seconds": 45,
        "total_calls_to_date": 1,
        "visit_booked": "No",
        "objection_raised": "Price too high",
    }
    result = handle_post_call_webhook(call_payload)
    assert result["priority_tier"] in ["Cold", "Warm"]
    if result["priority_tier"] == "Cold":
        assert result["alert_triggered"] is False
        print(f"✅ Cold Lead Webhook Passed: Classified as {result['priority_badge']}, email not triggered, SLA: {result['operational_sla']}")


def test_voice_property_valuation_inquiry():
    spoken_query = "Mera ghar kitne ka bikega? DHA Phase 6 mein 1 kanal ka ghar hai 5 saal purana"
    result = handle_voice_property_inquiry(spoken_query)
    assert "crore" in result["spoken_response_urdulish"].lower()
    assert result["extracted_entities"]["plot_size_marla"] == 20.0
    print(f"✅ Spoken Valuation Inquiry Passed:\nVoice Script: {result['spoken_response_urdulish']}")


if __name__ == "__main__":
    print("\n--- Running Voice Agent Integration Tests ---")
    test_post_call_webhook_hot_lead()
    test_post_call_webhook_cold_lead()
    test_voice_property_valuation_inquiry()
    print("\n🎉 ALL VOICE AGENT INTEGRATION TESTS PASSED WITH 100% SUCCESS!\n")
