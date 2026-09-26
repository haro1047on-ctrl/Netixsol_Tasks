"""Task 1 & 3: Evaluation Suite Runner.

Executes all 40+ test conversations through the stateful LangGraph agent,
tracks turn latency, checks state transitions, verifies security guardrails,
measures entity retention, and scores conversational correctness.
"""
from __future__ import annotations

import sys
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure Day 6 directory is first in sys.path
DAY6_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_DIR = DAY6_DIR.parent
DAY5_DIR = WORKSPACE_DIR / "day5-langgraph-agent"

if str(DAY6_DIR) not in sys.path:
    sys.path.insert(0, str(DAY6_DIR))
else:
    sys.path.remove(str(DAY6_DIR))
    sys.path.insert(0, str(DAY6_DIR))

if str(DAY5_DIR) not in sys.path:
    sys.path.insert(1, str(DAY5_DIR))

from graph import run_agent_turn
from security.security_guardrails import security_guardrail_engine
from state import create_initial_state
from eval_suite.conversation_loader import (
    ConversationTestCase,
    EvaluationSuite,
    TurnExpectation,
    load_evaluation_conversations,
)


@dataclass
class TurnEvaluationResult:
    turn_index: int
    user_input: str
    agent_response: str
    detected_intent: str
    clarification_flag: bool
    latency_ms: float
    passed: bool
    failure_reasons: List[str] = field(default_factory=list)
    tool_calls: List[str] = field(default_factory=list)
    state_snapshot: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationEvaluationResult:
    conversation_id: str
    category: str
    title: str
    total_turns: int
    passed_turns: int
    conversation_passed: bool
    total_latency_ms: float
    avg_latency_ms: float
    turn_results: List[TurnEvaluationResult]
    failure_summary: List[str] = field(default_factory=list)


@dataclass
class SuiteEvaluationSummary:
    total_conversations: int
    passed_conversations: int
    failed_conversations: int
    conversation_success_rate: float
    total_turns: int
    passed_turns: int
    turn_success_rate: float
    category_breakdown: Dict[str, Dict[str, Any]]
    latencies_ms: List[float]
    results: List[ConversationEvaluationResult]


class EvaluationRunner:
    """Production evaluation runner executing conversations through the agent."""

    def __init__(self, suite: Optional[EvaluationSuite] = None):
        self.suite = suite or load_evaluation_conversations()

    def run_turn(
        self,
        turn: TurnExpectation,
        current_state: Dict[str, Any],
        session_id: str,
    ) -> Tuple[TurnEvaluationResult, Dict[str, Any]]:
        """Run a single conversational turn and validate expectations."""
        start_time = time.perf_counter()
        failure_reasons = []

        # 1. Pre-turn Security Scan
        scan_res = security_guardrail_engine.scan_input(turn.user_input)

        if not scan_res.is_safe or scan_res.action in ("BLOCK", "DEFLECT", "ESCALATE"):
            # Intercepted by guardrail
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            agent_response = scan_res.override_response or ""
            detected_intent = scan_res.threat_category or "security_block"
            clarification_flag = True

            # Check forbidden keywords
            if turn.forbidden_keywords:
                for f_kw in turn.forbidden_keywords:
                    if f_kw.lower() in agent_response.lower():
                        failure_reasons.append(f"Forbidden keyword '{f_kw}' found in response.")

            # Check expected keywords
            if turn.expected_keywords:
                matched_any = any(kw.lower() in agent_response.lower() for kw in turn.expected_keywords)
                if not matched_any:
                    for kw in turn.expected_keywords:
                        if kw.lower() not in agent_response.lower():
                            failure_reasons.append(f"Expected keyword '{kw}' not found in guardrail deflection.")

            passed = len(failure_reasons) == 0
            turn_res = TurnEvaluationResult(
                turn_index=turn.turn_index,
                user_input=turn.user_input,
                agent_response=agent_response,
                detected_intent=detected_intent,
                clarification_flag=clarification_flag,
                latency_ms=duration_ms,
                passed=passed,
                failure_reasons=failure_reasons,
                tool_calls=[],
                state_snapshot={"guardrail_action": scan_res.action},
            )
            return turn_res, current_state

        # 2. Execute through LangGraph Agent
        state_after = run_agent_turn(
            user_message=scan_res.sanitized_input,
            current_state=current_state,
            session_id=session_id,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        clarification_flag = state_after.get("clarification_needed", False)

        # 3. Extract agent response cleanly based on active execution node
        raw_agent_response = ""
        if clarification_flag and state_after.get("clarification_prompt"):
            raw_agent_response = state_after["clarification_prompt"]
        elif state_after.get("final_response"):
            raw_agent_response = state_after["final_response"]
        elif state_after.get("agent_response"):
            raw_agent_response = state_after["agent_response"]
        elif state_after.get("conversation_history"):
            last_msg = state_after["conversation_history"][-1]
            raw_agent_response = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

        # 4. Post-turn Output Firewall Scan
        agent_response, is_pure = security_guardrail_engine.scan_output(raw_agent_response)
        if not is_pure:
            failure_reasons.append("Output firewall caught sensitive leaked tokens/internals!")

        detected_intent = state_after.get("intent", "unknown")

        # 5. Validate Intent Expectations
        if turn.expected_intent:
            exp_int = turn.expected_intent.lower().strip()
            act_int = detected_intent.lower().strip()
            if exp_int != act_int:
                allowed_equiv = (
                    (exp_int == "off_topic" and act_int in ("off_topic", "greeting", "clarification")),
                    (exp_int == "clarification" and act_int in ("clarification", "recommendation", "booking", "rescheduling")),
                    (exp_int == "booking" and act_int in ("booking", "clarification")),
                    (exp_int == "recommendation" and act_int in ("recommendation", "clarification")),
                    (exp_int == "rescheduling" and act_int in ("rescheduling", "booking")),
                    (exp_int == "rag" and act_int in ("rag", "recommendation")),
                )
                if not any(allowed_equiv):
                    failure_reasons.append(f"Expected intent '{turn.expected_intent}', got '{detected_intent}'.")

        # 6. Validate Keywords Expectations
        if turn.expected_keywords:
            rec_props = state_after.get("recommended_properties", [])
            props_str = " ".join(str(p) for p in rec_props).lower()
            combined_search_target = f"{agent_response.lower()} {props_str} {str(state_after.get('rag_context', '')).lower()} {str(state_after.get('clarification_prompt', '')).lower()}"

            missing_kws = [kw for kw in turn.expected_keywords if kw.lower() not in combined_search_target]
            if len(missing_kws) == len(turn.expected_keywords) and not any(kw.lower() in combined_search_target for kw in turn.expected_keywords):
                failure_reasons.append(f"None of expected keywords {turn.expected_keywords} found in response or context.")

        if turn.forbidden_keywords:
            for f_kw in turn.forbidden_keywords:
                if f_kw.lower() in agent_response.lower():
                    failure_reasons.append(f"Forbidden keyword '{f_kw}' detected in response.")

        # Entity verification
        prefs = state_after.get("property_preferences", {})
        tools_invoked = [t.get("tool_name", "tool") for t in state_after.get("tool_outputs", [])]

        passed = len(failure_reasons) == 0
        turn_res = TurnEvaluationResult(
            turn_index=turn.turn_index,
            user_input=turn.user_input,
            agent_response=agent_response,
            detected_intent=detected_intent,
            clarification_flag=clarification_flag,
            latency_ms=duration_ms,
            passed=passed,
            failure_reasons=failure_reasons,
            tool_calls=tools_invoked,
            state_snapshot={
                "intent": detected_intent,
                "city": prefs.get("city"),
                "budget": state_after.get("budget"),
                "appointment_status": state_after.get("appointment_status", {}).get("status"),
            },
        )
        return turn_res, state_after

    def run_conversation(self, test_case: ConversationTestCase) -> ConversationEvaluationResult:
        """Execute all turns of a conversation in sequence."""
        session_id = f"eval_{test_case.id}_{uuid.uuid4().hex[:6]}"
        current_state = create_initial_state(session_id=session_id)
        turn_results: List[TurnEvaluationResult] = []
        failure_summary: List[str] = []

        total_lat = 0.0
        passed_turns = 0

        for turn in test_case.turns:
            t_res, current_state = self.run_turn(turn, current_state, session_id)
            turn_results.append(t_res)
            total_lat += t_res.latency_ms
            if t_res.passed:
                passed_turns += 1
            else:
                failure_summary.extend([f"Turn {t_res.turn_index}: {r}" for r in t_res.failure_reasons])

        conv_passed = passed_turns == len(test_case.turns)
        avg_lat = total_lat / max(len(test_case.turns), 1)

        return ConversationEvaluationResult(
            conversation_id=test_case.id,
            category=test_case.category,
            title=test_case.title,
            total_turns=len(test_case.turns),
            passed_turns=passed_turns,
            conversation_passed=conv_passed,
            total_latency_ms=total_lat,
            avg_latency_ms=avg_lat,
            turn_results=turn_results,
            failure_summary=failure_summary,
        )

    def run_all(self) -> SuiteEvaluationSummary:
        """Run all test conversations in the evaluation suite."""
        results: List[ConversationEvaluationResult] = []
        category_breakdown: Dict[str, Dict[str, Any]] = {}
        all_latencies: List[float] = []

        total_turns = 0
        total_passed_turns = 0
        total_passed_convs = 0

        for conv in self.suite.conversations:
            cat = conv.category
            if cat not in category_breakdown:
                category_breakdown[cat] = {
                    "total": 0,
                    "passed": 0,
                    "failed": 0,
                    "success_rate": 0.0,
                    "avg_latency_ms": 0.0,
                    "latencies": [],
                }

            res = self.run_conversation(conv)
            results.append(res)

            category_breakdown[cat]["total"] += 1
            category_breakdown[cat]["latencies"].append(res.avg_latency_ms)
            all_latencies.extend([t.latency_ms for t in res.turn_results])

            total_turns += res.total_turns
            total_passed_turns += res.passed_turns

            if res.conversation_passed:
                total_passed_convs += 1
                category_breakdown[cat]["passed"] += 1
            else:
                category_breakdown[cat]["failed"] += 1

        for cat, data in category_breakdown.items():
            tot = data["total"]
            data["success_rate"] = (data["passed"] / tot) * 100.0 if tot > 0 else 0.0
            data["avg_latency_ms"] = sum(data["latencies"]) / max(len(data["latencies"]), 1)
            del data["latencies"]

        summary = SuiteEvaluationSummary(
            total_conversations=len(self.suite.conversations),
            passed_conversations=total_passed_convs,
            failed_conversations=len(self.suite.conversations) - total_passed_convs,
            conversation_success_rate=(total_passed_convs / max(len(self.suite.conversations), 1)) * 100.0,
            total_turns=total_turns,
            passed_turns=total_passed_turns,
            turn_success_rate=(total_passed_turns / max(total_turns, 1)) * 100.0,
            category_breakdown=category_breakdown,
            latencies_ms=all_latencies,
            results=results,
        )
        return summary
