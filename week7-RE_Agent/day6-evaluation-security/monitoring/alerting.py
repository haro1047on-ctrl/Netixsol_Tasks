"""Task 4: Production Alerting & Anomaly Detection System."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from monitoring.metrics_collector import MetricsCollector, metrics_collector
from day6_config import SLO_LATENCY_P95_MS, SLO_MAX_ERROR_RATE, SLO_MIN_SUCCESS_RATE

logger = logging.getLogger("ProductionAlerting")


@dataclass
class AlertNotification:
    severity: str  # INFO, WARNING, CRITICAL
    alert_name: str
    message: str
    timestamp: str
    current_value: float
    threshold_value: float


class AlertManager:
    """Evaluates telemetry against SLAs and dispatches production alerts."""

    def __init__(self, collector: Optional[MetricsCollector] = None):
        self.collector = collector or metrics_collector
        self.active_alerts: List[AlertNotification] = []

    def check_slos(self) -> List[AlertNotification]:
        """Check all operational SLOs and trigger alerts if thresholds breached."""
        snap = self.collector.get_snapshot()
        alerts: List[AlertNotification] = []
        now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # 1. Latency Check
        if snap.p95_turn_latency_ms > SLO_LATENCY_P95_MS:
            alerts.append(AlertNotification(
                severity="CRITICAL",
                alert_name="HighTurnLatency",
                message=f"P95 Turn Latency of {snap.p95_turn_latency_ms}ms exceeds threshold of {SLO_LATENCY_P95_MS}ms!",
                timestamp=now_str,
                current_value=snap.p95_turn_latency_ms,
                threshold_value=SLO_LATENCY_P95_MS,
            ))

        # 2. API Failure Spike Check
        if snap.total_turns_processed > 10:
            error_rate = snap.api_failures_total / max(snap.total_turns_processed, 1)
            if error_rate > SLO_MAX_ERROR_RATE:
                alerts.append(AlertNotification(
                    severity="CRITICAL",
                    alert_name="HighApiErrorRate",
                    message=f"API error rate of {error_rate * 100:.1f}% exceeds max threshold of {SLO_MAX_ERROR_RATE * 100:.1f}%!",
                    timestamp=now_str,
                    current_value=round(error_rate, 3),
                    threshold_value=SLO_MAX_ERROR_RATE,
                ))

        # 3. Calendar Service Failures
        if snap.calendar_failures_total > 3:
            alerts.append(AlertNotification(
                severity="WARNING",
                alert_name="CalendarFailuresDetected",
                message=f"Multiple Google Calendar creation failures ({snap.calendar_failures_total}) detected.",
                timestamp=now_str,
                current_value=snap.calendar_failures_total,
                threshold_value=3,
            ))

        # 4. RAG Miss Rate
        if snap.rag_queries_total > 10:
            rag_miss_rate = snap.rag_misses_total / max(snap.rag_queries_total, 1)
            if rag_miss_rate > 0.15:
                alerts.append(AlertNotification(
                    severity="WARNING",
                    alert_name="HighRAGMissRate",
                    message=f"RAG Knowledge Miss rate is high ({rag_miss_rate * 100:.1f}%). Vector store re-indexing recommended.",
                    timestamp=now_str,
                    current_value=round(rag_miss_rate, 3),
                    threshold_value=0.15,
                ))

        # 5. Low Voice Confidence
        if snap.voice_avg_confidence < 0.80 and snap.total_turns_processed > 5:
            alerts.append(AlertNotification(
                severity="WARNING",
                alert_name="LowVoiceTranscriptionConfidence",
                message=f"Deepgram ASR average confidence is low ({snap.voice_avg_confidence:.2f}). Check microphone & background noise.",
                timestamp=now_str,
                current_value=snap.voice_avg_confidence,
                threshold_value=0.80,
            ))

        self.active_alerts = alerts
        for a in alerts:
            if a.severity == "CRITICAL":
                logger.critical(f"PRODUCTION ALERT [{a.alert_name}]: {a.message}")
            else:
                logger.warning(f"PRODUCTION ALERT [{a.alert_name}]: {a.message}")

        return alerts


alert_manager = AlertManager()
