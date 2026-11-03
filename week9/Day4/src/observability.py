"""City Care Clinics - Observability & Telemetry Framework.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 4: Orchestration, Memory & Human-in-the-Loop
Provides end-to-end tracing compatible with Langfuse / LangSmith schemas:
1. Conversation & Session Tracing (Thread ID, Patient ID, Channel)
2. Agent-Level Span Execution Timing (Latency ms per node)
3. Tool Call Auditing (Inputs, execution time, and outputs)
4. Token Usage & Financial Cost Accounting
5. Clinical Escalations & Human-in-the-Loop Override Tracking
6. Exporters for 3 Annotated Patient Journey Traces
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Windows console UTF-8 safety
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class ToolExecutionSpan(BaseModel):
    """Audit record for a tool call made by an agent."""
    tool_name: str
    input_args: Dict[str, Any]
    output_summary: str
    duration_ms: float
    status: str = "SUCCESS"


class AgentNodeSpan(BaseModel):
    """Trace span for a single agent node execution in the supervisor graph."""
    span_id: str = Field(default_factory=lambda: f"span_{uuid.uuid4().hex[:8]}")
    node_name: str
    agent_role: str
    start_time_iso: str
    end_time_iso: str
    duration_ms: float
    input_state_summary: str
    output_state_summary: str
    tool_calls: List[ToolExecutionSpan] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: float = 0.0
    status: str = "SUCCESS"


class ConversationTrace(BaseModel):
    """Complete root trace for an outpatient encounter thread."""
    trace_id: str = Field(default_factory=lambda: f"tr_{uuid.uuid4().hex[:12]}")
    thread_id: str
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None
    channel: str = "web_chat"
    start_time_iso: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    end_time_iso: Optional[str] = None
    total_duration_ms: float = 0.0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_estimated_cost_usd: float = 0.0
    spans: List[AgentNodeSpan] = Field(default_factory=list)
    emergency_escalation_triggered: bool = False
    hitl_interrupt_triggered: bool = False
    doctor_override_applied: bool = False
    final_status: str = "COMPLETED"
    journey_annotation: Optional[str] = None


class TelemetryTracker:
    """Production observability engine capturing runtime metrics and traces."""

    COST_PER_1K_PROMPT_USD = 0.0001
    COST_PER_1K_COMPLETION_USD = 0.0002

    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.join(base_dir, "data", "traces")
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.active_traces: Dict[str, ConversationTrace] = {}
        self.completed_traces: List[ConversationTrace] = []

    def start_trace(
        self,
        thread_id: str,
        patient_id: Optional[str] = None,
        patient_name: Optional[str] = None,
        channel: str = "web_chat"
    ) -> ConversationTrace:
        """Initializes a new root trace for a conversation thread."""
        tr = ConversationTrace(
            thread_id=thread_id,
            patient_id=patient_id,
            patient_name=patient_name,
            channel=channel
        )
        self.active_traces[thread_id] = tr
        return tr

    def record_node_span(
        self,
        thread_id: str,
        node_name: str,
        agent_role: str,
        duration_ms: float,
        input_summary: str,
        output_summary: str,
        prompt_tokens: int = 150,
        completion_tokens: int = 80,
        tool_calls: Optional[List[ToolExecutionSpan]] = None,
        status: str = "SUCCESS"
    ) -> AgentNodeSpan:
        """Records an individual agent node execution span."""
        tr = self.active_traces.get(thread_id)
        if not tr:
            tr = self.start_trace(thread_id)

        now_iso = datetime.now(timezone.utc).isoformat()
        cost = (
            (prompt_tokens / 1000.0) * self.COST_PER_1K_PROMPT_USD +
            (completion_tokens / 1000.0) * self.COST_PER_1K_COMPLETION_USD
        )

        span = AgentNodeSpan(
            node_name=node_name,
            agent_role=agent_role,
            start_time_iso=now_iso,
            end_time_iso=now_iso,
            duration_ms=round(duration_ms, 2),
            input_state_summary=input_summary,
            output_state_summary=output_summary,
            tool_calls=tool_calls or [],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            estimated_cost_usd=round(cost, 6),
            status=status
        )

        tr.spans.append(span)
        tr.total_prompt_tokens += prompt_tokens
        tr.total_completion_tokens += completion_tokens
        tr.total_estimated_cost_usd = round(tr.total_estimated_cost_usd + cost, 6)
        tr.total_duration_ms = round(tr.total_duration_ms + duration_ms, 2)

        return span

    def mark_emergency(self, thread_id: str) -> None:
        tr = self.active_traces.get(thread_id)
        if tr:
            tr.emergency_escalation_triggered = True

    def mark_hitl(self, thread_id: str, doctor_override: bool = False) -> None:
        tr = self.active_traces.get(thread_id)
        if tr:
            tr.hitl_interrupt_triggered = True
            if doctor_override:
                tr.doctor_override_applied = True

    def finish_trace(self, thread_id: str, annotation: Optional[str] = None) -> ConversationTrace:
        """Closes a conversation trace and persists it to disk."""
        tr = self.active_traces.pop(thread_id, None)
        if not tr:
            tr = ConversationTrace(thread_id=thread_id)

        tr.end_time_iso = datetime.now(timezone.utc).isoformat()
        if annotation:
            tr.journey_annotation = annotation

        self.completed_traces.append(tr)

        # Persist to disk
        file_path = os.path.join(self.log_dir, f"{tr.trace_id}.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(tr.model_dump(), f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        return tr

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Calculates global telemetry averages."""
        if not self.completed_traces:
            return {
                "total_traces": 0,
                "avg_duration_ms": 0.0,
                "avg_cost_usd": 0.0,
                "total_tokens": 0,
                "emergency_rate_pct": 0.0,
                "hitl_rate_pct": 0.0
            }

        total = len(self.completed_traces)
        avg_dur = sum(t.total_duration_ms for t in self.completed_traces) / total
        avg_cost = sum(t.total_estimated_cost_usd for t in self.completed_traces) / total
        tot_tok = sum(t.total_prompt_tokens + t.total_completion_tokens for t in self.completed_traces)
        emerg_cnt = sum(1 for t in self.completed_traces if t.emergency_escalation_triggered)
        hitl_cnt = sum(1 for t in self.completed_traces if t.hitl_interrupt_triggered)

        return {
            "total_traces": total,
            "avg_duration_ms": round(avg_dur, 2),
            "avg_cost_usd": round(avg_cost, 6),
            "total_tokens": tot_tok,
            "emergency_rate_pct": round((emerg_cnt / total) * 100, 1),
            "hitl_rate_pct": round((hitl_cnt / total) * 100, 1)
        }
