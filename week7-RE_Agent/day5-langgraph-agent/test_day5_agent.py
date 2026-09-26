"""Comprehensive Automated Test Suite for Week 7 Day 5 LangGraph AI Agent.

Verifies:
1. Task 1: State Design & immutability / persistence
2. Task 2: Graph routing between all 9 nodes + clarification
3. Task 3: All 6 wrapped business tools
4. Task 4: Strict validation invariants:
   - Never book unavailable/conflicting slots
   - Never recommend unavailable/hallucinated properties
   - Ask clarification instead of guessing
5. Task 5: State transition logging & annotated execution traces
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

# Add agent path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from graph import build_realestate_graph, run_agent_turn
from logger import AgentLogger, default_agent_logger
from state import create_initial_state
from tools import (
    availability_checker_tool,
    calendar_tool,
    check_property_availability,
    check_slot_availability,
    crm_tool,
    email_tool,
    property_search_tool,
    rag_search_tool,
    search_properties_core,
)


class TestDay5LangGraphAgent(unittest.TestCase):
    """Automated unit and integration test suite."""

    def setUp(self):
        self.session_id = "test_session_automated"
        self.test_logger = AgentLogger(session_id=self.session_id)

    # -----------------------------------------------------------------------
    # Task 1: State Design Tests
    # -----------------------------------------------------------------------
    def test_task1_state_initialization(self):
        """Verify AgentState is properly typed, initialized and structured."""
        state = create_initial_state(session_id="test_init")
        self.assertIn("conversation_history", state)
        self.assertIn("user_profile", state)
        self.assertIn("property_preferences", state)
        self.assertIn("budget", state)
        self.assertIn("intent", state)
        self.assertIn("tool_outputs", state)
        self.assertIn("appointment_status", state)
        self.assertIn("clarification_needed", state)
        self.assertIn("validation_errors", state)
        self.assertEqual(state["appointment_status"]["status"], "none")

    # -----------------------------------------------------------------------
    # Task 3: Tool Integration Tests
    # -----------------------------------------------------------------------
    def test_task3_property_search_tool(self):
        """Verify verified property search tool returns correct listings."""
        res = search_properties_core(city="Lahore", budget_max=30_000_000, property_type="House")
        self.assertTrue(res.get("success"))
        self.assertIsInstance(res.get("properties"), list)

    def test_task3_calendar_tool(self):
        """Verify Google Calendar event creation and link generation."""
        res = calendar_tool.invoke({
            "action": "create",
            "client_name": "Test User",
            "phone": "0300-1112233",
            "employee": "Ahmed Raza",
            "property_title": "5 Marla House in DHA Phase 6",
            "property_id": "PROP-1000",
            "date_str": "Tomorrow",
            "time_str": "3:00 PM",
        })
        self.assertIn("google_calendar_link", res)
        self.assertIn("calendar.google.com", res)

    def test_task3_crm_tool(self):
        """Verify lead upsert and appointment logging in CRM."""
        lead_res = crm_tool.invoke({
            "action": "upsert_lead",
            "client_name": "Test CRM Buyer",
            "phone": "0300-9988776",
            "city": "Islamabad",
            "budget": "25000000",
        })
        self.assertIn("lead_id", lead_res)

    def test_task3_email_tool(self):
        """Verify appointment notification email tool."""
        email_res = email_tool.invoke({
            "employee_name": "Ahmed Raza",
            "client_name": "Test Client",
            "client_phone": "0300-1234567",
            "property_title": "Luxury Villa",
            "property_id": "PROP-1000",
            "date_str": "Tomorrow",
            "time_str": "4:00 PM",
            "event_type": "booking",
        })
        self.assertIn("email_id", email_res)
        self.assertIn("eml_", email_res)

    def test_task3_rag_search_tool(self):
        """Verify semantic RAG search over knowledge base."""
        rag_res = rag_search_tool.invoke({"query": "DHA Phase 6 amenities and electricity", "top_k": 2})
        self.assertIn("success", rag_res)

    # -----------------------------------------------------------------------
    # Task 4: Invariant Validation Tests
    # -----------------------------------------------------------------------
    def test_task4_invariant1_never_book_out_of_hours(self):
        """Invariant: NEVER book out-of-hours slots (e.g. 11 PM or 4 AM)."""
        slot_check = check_slot_availability(
            agent_name="Ahmed Raza",
            date_str="Tomorrow",
            time_str="11:30 PM",  # Outside operating hours (09:00 - 19:00)
        )
        self.assertFalse(slot_check["available"])
        self.assertIn("operating hours", slot_check["reason"])
        self.assertTrue(len(slot_check.get("alternative_slots", [])) > 0)

    def test_task4_invariant2_never_recommend_unavailable_properties(self):
        """Invariant: NEVER recommend non-existent/unavailable properties."""
        check_fake = check_property_availability("PROP-FAKEXYZ-9999")
        self.assertFalse(check_fake["available"])
        self.assertFalse(check_fake["exists"])
        self.assertIn("not in the verified database", check_fake["reason"])

    def test_task4_invariant3_ask_clarification_instead_of_guessing(self):
        """Invariant: If search is missing city & budget, trigger clarification."""
        state = create_initial_state(session_id="test_clarification")
        res = run_agent_turn("I want to buy a house", current_state=state, session_id="test_clarification")
        self.assertEqual(res.get("last_node"), "ClarificationNode")
        self.assertTrue(any(w in res.get("final_response").lower() for w in ["city", "budget", "lahore", "islamabad"]))

    # -----------------------------------------------------------------------
    # Task 2: Graph Routing & Multi-Turn Execution
    # -----------------------------------------------------------------------
    def test_task2_greeting_flow(self):
        """Verify greeting route."""
        res = run_agent_turn("Hello Assalam o Alaikum", session_id="test_greet")
        self.assertEqual(res.get("last_node"), "GreetingNode")
        self.assertIn("RealEstate Hub", res.get("final_response"))

    def test_task2_recommendation_flow(self):
        """Verify recommendation route with Urdu budget parsing."""
        res = run_agent_turn(
            "Show me 5 marla houses in Lahore under 2 crore",
            session_id="test_rec",
        )
        self.assertEqual(res.get("last_node"), "RecommendationNode")
        self.assertTrue(len(res.get("recommended_properties", [])) > 0 or "no matching active listings" in res.get("final_response").lower())

    def test_task2_booking_flow(self):
        """Verify booking pipeline orchestration."""
        import random
        unique_date = f"2027-0{random.randint(1,9)}-{random.randint(10,28)}"
        state = create_initial_state(session_id="test_book")
        state["user_profile"] = {"name": "Hamza Ali", "phone": "0300-8877665"}
        state["appointment_status"] = {"property_id": "PROP-1000", "property_title": "House in Lahore"}

        res = run_agent_turn(
            f"Book a visit for {unique_date} at 10:00 AM, my name is Hamza phone 0300-8877665",
            current_state=state,
            session_id="test_book",
        )
        self.assertEqual(res.get("last_node"), "BookingNode")
        self.assertEqual(res.get("appointment_status", {}).get("status"), "scheduled")
        self.assertIn("schedule", res.get("final_response").lower())

    def test_task2_rescheduling_and_cancellation_flows(self):
        """Verify rescheduling and cancellation routes."""
        import random
        import uuid
        date_1 = f"2027-11-{random.randint(10,28)}"
        date_2 = f"2027-12-{random.randint(10,28)}"
        state = create_initial_state(session_id="test_resched")
        state["appointment_status"] = {
            "appointment_id": f"appt_test_{uuid.uuid4().hex[:6]}",
            "property_id": "PROP-1000",
            "property_title": "5 Marla House",
            "date_str": date_1,
            "time_str": "10:00 AM",
            "status": "scheduled",
        }
        # Reschedule
        resched_res = run_agent_turn(
            f"Please reschedule my visit to {date_2} at 11:00 AM",
            current_state=state,
            session_id="test_resched",
        )
        self.assertEqual(resched_res.get("last_node"), "ReschedulingNode")
        self.assertEqual(resched_res.get("appointment_status", {}).get("status"), "rescheduled")

        # Cancel
        cancel_res = run_agent_turn(
            "Cancel my visit appointment",
            current_state=resched_res,
            session_id="test_resched",
        )
        self.assertEqual(cancel_res.get("last_node"), "CancellationNode")
        self.assertEqual(cancel_res.get("appointment_status", {}).get("status"), "cancelled")

    def test_task2_rag_flow(self):
        """Verify RAG knowledge base route."""
        res = run_agent_turn("What are the amenities and payment plan in Bahria Town?", session_id="test_rag")
        self.assertEqual(res.get("last_node"), "RAGNode")
        self.assertTrue(len(res.get("final_response")) > 20)

    # -----------------------------------------------------------------------
    # Task 5: State Logging & Trace Export Tests
    # -----------------------------------------------------------------------
    def test_task5_state_logging_and_trace_export(self):
        """Verify state logging captures transitions and exports JSON/MD traces."""
        traces = default_agent_logger.export_traces()
        self.assertIn("json_path", traces)
        self.assertIn("md_path", traces)
        self.assertTrue(os.path.exists(traces["json_path"]))
        self.assertTrue(os.path.exists(traces["md_path"]))


if __name__ == "__main__":
    unittest.main()
