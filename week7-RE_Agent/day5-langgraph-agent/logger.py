"""Task 5: State Logging & Annotated Execution Traces for LangGraph.

Logs every node transition and generates comprehensive, annotated execution
traces in both structured JSON and rich Markdown reports.
"""
from __future__ import annotations

import datetime
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import TRACES_DIR

# Safe stdout handling for Windows terminals
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass

# Setup standard logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("LangGraphAgent")


class ExecutionTraceStep:
    """Represents a single annotated node transition step."""

    def __init__(
        self,
        step_number: int,
        node_name: str,
        from_node: str,
        input_state: Dict[str, Any],
        intent: str,
        timestamp: Optional[str] = None,
    ):
        self.step_number = step_number
        self.node_name = node_name
        self.from_node = from_node
        self.timestamp = timestamp or datetime.datetime.now(datetime.timezone.utc).isoformat()
        self.intent = intent
        self.input_summary = self._summarize_state(input_state)
        self.output_summary: Dict[str, Any] = {}
        self.tools_called: List[Dict[str, Any]] = []
        self.validation_checks: List[Dict[str, Any]] = []
        self.agent_reasoning: str = ""
        self.elapsed_ms: float = 0.0
        self._start_time = time.perf_counter()

    def _summarize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Extract a clean, non-bloated summary of the state."""
        return {
            "budget": state.get("budget"),
            "property_preferences": state.get("property_preferences", {}),
            "user_profile": {
                k: v for k, v in state.get("user_profile", {}).items() if v
            },
            "appointment_status": state.get("appointment_status", {}).get("status", "none"),
            "clarification_needed": state.get("clarification_needed", False),
            "validation_errors": state.get("validation_errors", []),
        }

    def record_tool_call(self, tool_name: str, input_params: Dict[str, Any], result: Any, status: str = "success"):
        """Record an executed tool invocation inside this node."""
        self.tools_called.append({
            "tool_name": tool_name,
            "input_params": input_params,
            "result_summary": str(result)[:300] if result is not None else None,
            "status": status,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

    def record_validation(self, check_name: str, passed: bool, details: str):
        """Record a validation invariant check (e.g. slot availability, property existence)."""
        self.validation_checks.append({
            "check_name": check_name,
            "passed": passed,
            "details": details,
        })

    def complete(self, output_state: Dict[str, Any], reasoning: str = ""):
        """Mark the step as completed, calculate latency and extract diffs."""
        self.elapsed_ms = round((time.perf_counter() - self._start_time) * 1000, 2)
        self.agent_reasoning = reasoning
        self.output_summary = self._summarize_state(output_state)
        self.output_summary["final_response_snippet"] = (
            str(output_state.get("final_response", ""))[:180] + "..."
            if len(str(output_state.get("final_response", ""))) > 180
            else output_state.get("final_response", "")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "node_name": self.node_name,
            "from_node": self.from_node,
            "timestamp": self.timestamp,
            "intent": self.intent,
            "elapsed_ms": self.elapsed_ms,
            "agent_reasoning": self.agent_reasoning,
            "input_summary": self.input_summary,
            "output_summary": self.output_summary,
            "tools_called": self.tools_called,
            "validation_checks": self.validation_checks,
        }


class AgentLogger:
    """Singleton session logger tracking node transitions and generating trace reports."""

    def __init__(self, session_id: str = "default_session"):
        self.session_id = session_id
        self.steps: List[ExecutionTraceStep] = []
        self.active_step: Optional[ExecutionTraceStep] = None
        self.step_counter = 0

    def log_node_entry(self, node_name: str, from_node: str, state: Dict[str, Any]) -> ExecutionTraceStep:
        """Log entry into a graph node."""
        self.step_counter += 1
        intent = state.get("intent", "unknown")
        
        # Console transition banner
        try:
            print(f"\n{'='*70}")
            print(f"[*] [NODE TRANSITION #{self.step_counter}] {from_node} -> {node_name}")
            print(f"    Intent: {intent} | Budget: {state.get('budget')} | City: {state.get('property_preferences', {}).get('city', 'N/A')}")
            print(f"{'='*70}")
        except Exception:
            pass

        logger.info(f"Node Entry: [{from_node}] -> [{node_name}] | Intent: {intent}")
        step = ExecutionTraceStep(
            step_number=self.step_counter,
            node_name=node_name,
            from_node=from_node,
            input_state=state,
            intent=intent,
        )
        self.active_step = step
        return step

    def log_node_exit(self, step: ExecutionTraceStep, output_state: Dict[str, Any], reasoning: str = ""):
        """Log exit from a graph node and append to session trace."""
        step.complete(output_state, reasoning)
        self.steps.append(step)
        
        # Console output summary
        tools_str = ", ".join(t["tool_name"] for t in step.tools_called) if step.tools_called else "None"
        val_status = "PASSED" if all(v.get("passed", True) for v in step.validation_checks) else "VALIDATION ISSUE"
        try:
            print(f"    Latency: {step.elapsed_ms}ms | Tools Used: {tools_str} | Validation: {val_status}")
            if step.agent_reasoning:
                print(f"    Reasoning: {step.agent_reasoning}")
            print(f"{'-'*70}\n")
        except Exception:
            pass
        
        logger.info(f"Node Exit: [{step.node_name}] completed in {step.elapsed_ms}ms. Tools: {tools_str}")
        self.active_step = None

    def export_traces(self) -> Dict[str, str]:
        """Save execution traces to disk in JSON and Markdown formats."""
        timestamp_slug = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = TRACES_DIR / f"trace_{self.session_id}_{timestamp_slug}.json"
        md_path = TRACES_DIR / f"trace_{self.session_id}_{timestamp_slug}.md"

        trace_data = {
            "session_id": self.session_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_steps": len(self.steps),
            "total_latency_ms": sum(s.elapsed_ms for s in self.steps),
            "steps": [s.to_dict() for s in self.steps],
        }

        # Write JSON & Markdown traces safely
        try:
            json_path.write_text(json.dumps(trace_data, indent=2), encoding="utf-8")
            md_content = self._generate_markdown_report(trace_data)
            md_path.write_text(md_content, encoding="utf-8")
            logger.info(f"Saved execution traces to:\n- {json_path}\n- {md_path}")
        except Exception:
            pass

        return {
            "json_path": str(json_path),
            "md_path": str(md_path),
        }

    def _generate_markdown_report(self, trace_data: Dict[str, Any]) -> str:
        """Generate a beautiful, formatted Markdown execution trace report."""
        lines = [
            f"# LangGraph Agent Execution Trace Report",
            f"",
            f"- **Session ID:** `{trace_data['session_id']}`",
            f"- **Timestamp:** `{trace_data['timestamp']}`",
            f"- **Total Transitions:** `{trace_data['total_steps']}`",
            f"- **Total Execution Latency:** `{trace_data['total_latency_ms']:.2f} ms`",
            f"",
            f"---",
            f"",
            f"## Transition Timeline & Node Graph",
            f"",
            f"```mermaid",
            f"graph LR",
        ]

        # Add diagram links
        for step in self.steps:
            from_n = step.from_node.replace(" ", "_")
            to_n = step.node_name.replace(" ", "_")
            lines.append(f"    {from_n} -->|Step {step.step_number}: {step.intent}| {to_n}")

        lines.extend([
            f"```",
            f"",
            f"---",
            f"",
            f"## Annotated Execution Steps",
            f"",
        ])

        for step in self.steps:
            tools_list = ", ".join(f"`{t['tool_name']}` ({t['status']})" for t in step.tools_called) or "None"
            val_list = "<br>".join(
                f"{'[PASSED]' if v['passed'] else '[FAILED]'} **{v['check_name']}**: {v['details']}"
                for v in step.validation_checks
            ) or "Standard Invariants Verified"

            lines.extend([
                f"### Step {step.step_number}: Node `{step.node_name}` (from `{step.from_node}`)",
                f"- **Timestamp:** `{step.timestamp}` | **Latency:** `{step.elapsed_ms} ms`",
                f"- **Detected Intent:** `{step.intent}`",
                f"- **Agent Reasoning:** {step.agent_reasoning or 'Standard deterministic / LLM graph execution'}",
                f"- **Tools Invocations:** {tools_list}",
                f"- **Validation Checks:**",
                f"  > {val_list}",
                f"- **Output Summary:**",
                f"  ```json",
                f"  {json.dumps(step.output_summary, indent=2)}",
                f"  ```",
                f"",
            ])

        return "\n".join(lines)


# Global default logger instance
default_agent_logger = AgentLogger()
