"""City Care Clinics - Multi-Channel Ingress & Egress Connector.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 4: Orchestration, Memory & Human-in-the-Loop
Connects the Multi-Agent System to:
1. Web Chat (Interactive bidirectional session)
2. WhatsApp Cloud API (Outbound messaging and inbound simulated webhooks)
3. Urdu Voice Notes via Whisper / Speech-to-Text Pipeline
4. Automated Email Confirmations & Follow-up Scheduling Engine
"""
from __future__ import annotations

import base64
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

# Windows console UTF-8 safety
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
WEEK9_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
for p in [SRC_DIR, DAY2_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from mcp_servers.notifications_server import send_email_summary, send_whatsapp_message


class InboundMessage(BaseModel):
    """Normalized inbound communication across all channels."""
    channel: str = Field(description="web_chat, whatsapp, voice_note, or telephony")
    thread_id: str
    sender_id: str  # Phone number, web session ID, or patient ID
    text_content: str
    audio_base64: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OutboundMessage(BaseModel):
    """Normalized outbound dispatch receipt."""
    channel: str
    recipient: str
    message_type: str  # text, audio, html_email
    body: str
    status: str
    delivery_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AudioTranscriber:
    """Urdu Audio / Voice Note Transcription Service."""

    def transcribe_urdu_audio(self, audio_data: bytes | str) -> str:
        """Transcribes audio payload to normalized UrduLish text."""
        # Simulated high-fidelity Whisper Urdu translation pipeline
        # Supports both string simulation and raw audio bytes
        if isinstance(audio_data, str) and not audio_data.startswith("=="):
            return audio_data  # Direct text simulation

        # Default fallback for simulated voice notes
        return "Doctor sahib, mere 5 saal ke betay ko kal se 102 bukhar hai aur ultiyan aa rahi hain."


from services.reminder_service import get_reminder_service


class ScheduledReminderQueue:
    """Database-backed persistent queue for automated follow-up messages."""

    def __init__(self):
        self.reminder_service = get_reminder_service()
        self.queue: List[Dict[str, Any]] = []

    def schedule_message(
        self,
        recipient_phone: str,
        message_text: str,
        delay_hours: int,
        label: str
    ) -> Dict[str, Any]:
        """Schedules automated outbound message persistently after specified interval."""
        res = self.reminder_service.schedule_custom_reminder(
            recipient=recipient_phone,
            channel="WHATSAPP",
            message_text=message_text,
            delay_hours=delay_hours,
            label=label
        )
        item = {
            "schedule_id": res.get("schedule_id", f"SCH_{uuid.uuid4().hex[:8].upper()}"),
            "recipient": recipient_phone,
            "text": message_text,
            "delay_hours": delay_hours,
            "label": label,
            "status": "QUEUED",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self.queue.append(item)
        return item

    def get_pending_reminders(self) -> List[Dict[str, Any]]:
        """Queries pending reminders from persistent database."""
        pending_records = self.reminder_service.get_pending_due_reminders()
        return [
            {
                "schedule_id": r.id,
                "recipient": r.recipient,
                "text": r.body,
                "label": r.subject or r.notification_type,
                "status": r.status,
                "scheduled_for": r.scheduled_for.isoformat() if r.scheduled_for else None
            }
            for r in pending_records
        ]


class ChannelConnector:
    """Production Multi-Channel Gateway for City Care Clinics."""

    def __init__(self):
        self.transcriber = AudioTranscriber()
        self.scheduler = ScheduledReminderQueue()
        self.outbound_log: List[OutboundMessage] = []

    def process_inbound(self, raw_input: Dict[str, Any]) -> InboundMessage:
        """Normalizes heterogeneous channel inputs into standardized InboundMessage."""
        ch = raw_input.get("channel", "web_chat")
        thread_id = raw_input.get("thread_id", f"TH_{uuid.uuid4().hex[:8]}")
        sender = raw_input.get("sender_id", "ANONYMOUS")
        text = raw_input.get("text_content", "")

        # If incoming is an Urdu voice note, run through speech-to-text
        if ch == "voice_note" or raw_input.get("audio_data"):
            audio_bytes = raw_input.get("audio_data") or b""
            text = self.transcriber.transcribe_urdu_audio(audio_bytes)

        return InboundMessage(
            channel=ch,
            thread_id=thread_id,
            sender_id=sender,
            text_content=text,
            audio_base64=raw_input.get("audio_base64")
        )

    def send_web_chat_reply(self, thread_id: str, reply_text: str) -> OutboundMessage:
        """Dispatches response to interactive web session."""
        out = OutboundMessage(
            channel="web_chat",
            recipient=thread_id,
            message_type="text",
            body=reply_text,
            status="DELIVERED",
            delivery_id=f"WEB_{uuid.uuid4().hex[:8]}"
        )
        self.outbound_log.append(out)
        return out

    def send_whatsapp(self, phone: str, message_text: str) -> OutboundMessage:
        """Dispatches WhatsApp message via Notifications FastMCP server."""
        receipt = send_whatsapp_message(recipient_phone=phone, message_text=message_text)
        out = OutboundMessage(
            channel="whatsapp",
            recipient=phone,
            message_type="text",
            body=message_text,
            status=receipt.get("status", "DELIVERED"),
            delivery_id=receipt.get("message_id", f"WA_{uuid.uuid4().hex[:8]}")
        )
        self.outbound_log.append(out)
        return out

    def send_email_confirmation(
        self,
        recipient_email: str,
        subject: str,
        html_body: str
    ) -> OutboundMessage:
        """Dispatches appointment confirmation or SOAP brief via Email FastMCP server."""
        receipt = send_email_summary(
            recipient_email=recipient_email,
            subject=subject,
            body_html=html_body
        )
        out = OutboundMessage(
            channel="email",
            recipient=recipient_email,
            message_type="html_email",
            body=html_body,
            status=receipt.get("status", "SENT"),
            delivery_id=receipt.get("message_id", f"EML_{uuid.uuid4().hex[:8]}")
        )
        self.outbound_log.append(out)
        return out

    def schedule_followup(
        self,
        phone: str,
        message_text: str,
        delay_hours: int,
        label: str
    ) -> Dict[str, Any]:
        """Queues automated 48-hour or 7-day outbound follow-up message."""
        return self.scheduler.schedule_message(
            recipient_phone=phone,
            message_text=message_text,
            delay_hours=delay_hours,
            label=label
        )
