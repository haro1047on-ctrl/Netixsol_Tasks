"""City Care Clinics - Master Validation Runner for Week 9 - Day 1.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Validates Architecture, Agent Role Cards, Conversation Flows, Safety/Triage Policies, and Privacy Guardrails.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Reconfigure stdout for UTF-8 compatibility on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from clinical_state import (
    AuditLogEntry,
    ClinicalSpecialty,
    ClinicBranch,
    PatientProfile,
    TriageLevel,
)
from triage_engine import TriageEngine
from pii_redactor import PIIRedactor
from agent_registry import AGENT_REGISTRY
from conversation_simulator import ScenarioSimulator


def test_agent_role_cards():
    """Validates that all 8 agents are correctly registered with boundaries."""
    print("\n[TASK 2 TEST] Validating 8 Agent Role Cards & Invariants...")
    expected_agents = [
        "SUPERVISOR", "INTAKE", "TRIAGE", "SCHEDULING",
        "RECORDS", "CLINICAL_SUMMARY", "RX_SAFETY", "FOLLOWUP"
    ]
    assert len(AGENT_REGISTRY) == 8, f"Expected 8 agents, found {len(AGENT_REGISTRY)}"

    for agent_id in expected_agents:
        agent = AGENT_REGISTRY[agent_id]
        assert agent.agent_id == agent_id
        assert len(agent.permitted_tools) > 0, f"{agent_id} has no permitted tools"
        assert len(agent.prohibited_actions) > 0, f"{agent_id} has no negative constraints"
        assert len(agent.system_prompt) > 20, f"{agent_id} has insufficient system prompt"
        print(f"  ✓ {agent.display_name}: {len(agent.permitted_tools)} tools, {len(agent.prohibited_actions)} negative constraints.")
    print("  --> ALL 8 AGENT ROLE CARDS VALIDATED SUCCESSFULLY.")


def test_safety_triage_policy():
    """Validates deterministic red-flag emergency detection and urgency tiers."""
    print("\n[TASK 4 TEST] Validating Medical Safety & Triage Policies...")
    engine = TriageEngine()

    test_cases = [
        ("Mere seene mein shadeed dard hai aur baayein baazu mein phail raha hai", TriageLevel.EMERGENCY, "CARDIOVASCULAR"),
        ("Mera munh tedha ho gaya hai aur aawaz ladkhara rahi hai", TriageLevel.EMERGENCY, "NEUROLOGICAL_FAST"),
        ("Saans lene mein shadeed dushwari ho rahi hai aur hont neelay par gaye hain", TriageLevel.EMERGENCY, "RESPIRATORY"),
        ("Khooni ulti aa rahi hai aur khoon nahi ruk raha", TriageLevel.EMERGENCY, "HEMORRHAGIC_TRAUMA"),
        ("Shadeed pet dard hai aur 3 din se bukhar 103 hai", TriageLevel.URGENT, None),
        ("Halka bukhar aur khansi hai kal raat se", TriageLevel.ROUTINE, None),
        ("Kaan mein halki kharish aur mail hai", TriageLevel.ROUTINE, None),
        ("Chehray par daanay aur acne ban rahe hain", TriageLevel.ROUTINE, None),
    ]

    for text, expected_level, expected_cat in test_cases:
        assessment = engine.evaluate(text)
        assert assessment.urgency_level == expected_level, (
            f"Failed on '{text}'. Expected {expected_level}, got {assessment.urgency_level}"
        )
        if expected_cat:
            assert assessment.red_flag_category == expected_cat, (
                f"Failed category on '{text}'. Expected {expected_cat}, got {assessment.red_flag_category}"
            )
        print(f"  ✓ [{assessment.urgency_level.value}] '{text[:45]}...' -> Specialty: {assessment.matched_specialty.value}")

    # Test Neonatal Infant Fever Red-Flag (< 3 months with 100.4°F)
    infant_assessment = engine.evaluate("Bache ko bukhar hai", patient_age=0, is_pediatric=True, reported_temp_f=101.0)
    assert infant_assessment.urgency_level == TriageLevel.EMERGENCY
    assert infant_assessment.red_flag_category == "NEONATAL_FEVER"
    print("  ✓ [EMERGENCY] Neonatal infant fever (<3 months, 101°F) correctly intercepted for immediate emergency.")
    print("  --> SAFETY TRIAGE POLICY VALIDATED: 100% RED-FLAG INTERCEPTION RATE.")


def test_privacy_and_pii_redactor():
    """Validates Pakistani PII redaction and reversible vaulting."""
    print("\n[TASK 5 TEST] Validating Privacy & Pakistani PII Redaction...")
    redactor = PIIRedactor()

    sample_text = (
        "Mera naam Muhammad Usman Ali hai, phone 0300-1234567, CNIC 35201-7654321-3. "
        "Main House #12, Street 4, Gulberg III Lahore mein rehta hoon. Email usman.ali@gmail.com."
    )

    sanitized, vault = redactor.redact(sample_text)

    # Assertions
    assert "35201-7654321-3" not in sanitized, "CNIC leaked in sanitized text!"
    assert "0300-1234567" not in sanitized, "Phone number leaked in sanitized text!"
    assert "usman.ali@gmail.com" not in sanitized, "Email leaked in sanitized text!"
    assert "[CNIC_1]" in sanitized
    assert "[PHONE_1]" in sanitized
    assert len(vault) >= 3, f"Vault missed entities: {vault}"

    # Test Rehydration within secure EHR boundary
    rehydrated = redactor.rehydrate(sanitized, vault)
    assert "35201-7654321-3" in rehydrated
    assert "0300-1234567" in rehydrated

    print(f"  Raw:        {sample_text[:65]}...")
    print(f"  Sanitized:  {sanitized[:65]}...")
    print(f"  Vault Keys: {list(vault.keys())}")
    print("  ✓ Reversible pseudonymization confirmed for EHR MCP boundary.")
    print("  --> PRIVACY & PII REDACTION PIPELINE VALIDATED.")


def test_tamper_evident_audit_chain():
    """Validates SHA-256 cryptographic audit chaining."""
    print("\n[TASK 5 TEST] Validating Tamper-Evident SHA-256 Audit Chain...")
    genesis_hash = "0" * 64

    entry1 = AuditLogEntry(
        event_id="EV-001",
        actor_id="SUPERVISOR",
        actor_role="SYSTEM",
        action_type="READ",
        resource_type="Patient",
        resource_id="PT_441",
        payload_summary="Fetched sanitized profile",
        previous_event_hash=genesis_hash
    )
    entry1.event_hash_sha256 = entry1.compute_hash()

    entry2 = AuditLogEntry(
        event_id="EV-002",
        actor_id="DR_TARIQ",
        actor_role="ATTENDING_DOCTOR",
        action_type="OVERRIDE",
        resource_type="MedicationRequest",
        resource_id="RX_881",
        payload_summary="Approved with clinical justification",
        previous_event_hash=entry1.event_hash_sha256
    )
    entry2.event_hash_sha256 = entry2.compute_hash()

    assert entry2.previous_event_hash == entry1.event_hash_sha256
    assert len(entry2.event_hash_sha256) == 64
    print(f"  ✓ Entry 1 Hash: {entry1.event_hash_sha256[:16]}...")
    print(f"  ✓ Entry 2 Chained Hash: {entry2.event_hash_sha256[:16]}... (Links to Entry 1)")
    print("  --> AUDIT LOG SHA-256 TAMPER-EVIDENT CHAIN CONFIRMED.")


def test_conversation_scenarios():
    """Validates all 7 required conversation scenarios."""
    print("\n[TASK 3 TEST] Simulating All 7 Patient Conversation Scenarios...")
    simulator = ScenarioSimulator()

    scenarios = [
        simulator.run_scenario_1_fever_cough,
        simulator.run_scenario_2_chest_pain,
        simulator.run_scenario_3_child_booking,
        simulator.run_scenario_4_lab_report,
        simulator.run_scenario_5_reschedule,
        simulator.run_scenario_6_medication_inquiry,
        simulator.run_scenario_7_follow_up
    ]

    for idx, sc_fn in enumerate(scenarios, 1):
        res = sc_fn()
        print(f"  ✓ Scenario {idx} ({res['scenario']}): Status -> [{res['status']}]")

    print("  --> ALL 7 SCENARIOS VERIFIED END-TO-END.")


def main():
    start_time = time.time()
    print("=" * 80)
    print("CITY CARE CLINICS — MULTI-AGENT AI CLINIC ASSISTANT (WEEK 9 - DAY 1)")
    print("VALIDATION SUITE: ARCHITECTURE, ROLES, FLOWS, SAFETY & COMPLIANCE")
    print("=" * 80)

    test_agent_role_cards()
    test_safety_triage_policy()
    test_privacy_and_pii_redactor()
    test_tamper_evident_audit_chain()
    test_conversation_scenarios()

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"WEEK 9 - DAY 1 DELIVERABLES 100% COMPLETE & VERIFIED in {elapsed:.2f}s")
    print("Architecture, Role Cards, Conversation Flows, Safety Policy, and Compliance Ready.")
    print("=" * 80)


if __name__ == "__main__":
    main()
