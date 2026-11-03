"""
src/data/schemas.py
===================
Zarya Digital Bank (Pakistan) — Data Typing & Unified JSON Schemas
Defines Pydantic v2 schemas for intent classification, ticketing payloads,
security flags, conversational messages, and dataset records.
"""

from enum import Enum
import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class IntentEnum(str, Enum):
    """Primary high-level banking domain categories."""
    ACCOUNT_BALANCE = "Account_Balance"
    TRANSFERS_PAYMENTS = "Transfers_Payments"
    CARDS = "Cards"
    LOANS_PRODUCTS = "Loans_Products"
    COMPLAINTS = "Complaints"
    FRAUD_SCAMS = "Fraud_Scams"
    OUT_OF_SCOPE = "Out_Of_Scope"


class LanguageEnum(str, Enum):
    """Detected language register."""
    URDULISH = "UrduLish"
    ROMAN_URDU = "Roman_Urdu"
    URDU_NASTALIQ = "Urdu_Nastaliq"
    ENGLISH = "English"


class SentimentEnum(str, Enum):
    """Emotional state of customer."""
    POSITIVE = "Positive"
    NEUTRAL = "Neutral"
    FRUSTRATED = "Frustrated"
    PANICKED = "Panicked"
    ANGRY = "Angry"


class PriorityEnum(str, Enum):
    """Operational routing urgency."""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL_P1 = "Critical_P1"


class SeverityEnum(str, Enum):
    """SLA Severity for ticket dispatch."""
    P1_CRITICAL = "P1_Critical"
    P2_URGENT = "P2_Urgent"
    P3_NORMAL = "P3_Normal"
    P4_LOW = "P4_Low"


class DepartmentEnum(str, Enum):
    """Target department within Core Banking / CRM."""
    PAYMENT_OPERATIONS = "Payment_Operations"
    CARD_SERVICES = "Card_Services"
    DISPUTE_RESOLUTION = "Dispute_Resolution"
    FRAUD_PREVENTION_UNIT = "Fraud_Prevention_Unit"
    GENERAL_SUPPORT = "General_Support"
    BRANCHLESS_BANKING = "Branchless_Banking"


class SecurityFlagTypeEnum(str, Enum):
    """Security violation and sensitive data types."""
    NONE = "None"
    OTP_PHISHING = "OTP_Phishing"
    PIN_SKIMMING = "PIN_Skimming"
    PROMPT_INJECTION = "Prompt_Injection"
    PII_EXPOSURE = "PII_Exposure"


class TicketDetails(BaseModel):
    """Core Banking CRM Ticket payload."""
    category: str = Field(..., description="Ticket classification matching intent or sub-intent.")
    title: str = Field(..., min_length=5, max_length=200, description="Concise summary title.")
    description: str = Field(..., min_length=10, description="Full context description.")
    severity: SeverityEnum = Field(..., description="SLA priority rating.")
    suggested_action: str = Field(..., min_length=5, description="Recommended remediation step.")
    assigned_department: DepartmentEnum = Field(..., description="Target routing queue.")


class SecurityFlag(BaseModel):
    """Security Shield inspection status."""
    detected_sensitive_request: bool = Field(
        default=False,
        description="True if an attempt to solicit/disclose OTP, PIN, CVV, or passwords was detected."
    )
    refusal_triggered: bool = Field(
        default=False,
        description="True if the model or guardrail refused to process the request."
    )
    flag_type: SecurityFlagTypeEnum = Field(
        default=SecurityFlagTypeEnum.NONE,
        description="Type of sensitive violation detected."
    )


class ZaryaBankingAssistantResponse(BaseModel):
    """
    Unified JSON output schema for Zarya Digital Bank Assistant.
    Every model generation must strictly parse against this schema.
    """
    intent: IntentEnum = Field(..., description="High-level banking domain category.")
    sub_intent: str = Field(..., min_length=2, description="Specific granular banking action.")
    language: LanguageEnum = Field(default=LanguageEnum.URDULISH, description="Detected customer language.")
    sentiment: SentimentEnum = Field(default=SentimentEnum.NEUTRAL, description="Customer sentiment.")
    priority: PriorityEnum = Field(default=PriorityEnum.MEDIUM, description="Operational routing urgency.")
    urgency_score: float = Field(..., ge=0.0, le=1.0, description="Urgency score between 0.0 and 1.0.")
    requires_ticket: bool = Field(..., description="True if a back-office ticket must be created.")
    ticket_details: Optional[TicketDetails] = Field(
        default=None,
        description="Details for CRM ticket if requires_ticket is True."
    )
    security_flag: SecurityFlag = Field(
        default_factory=SecurityFlag,
        description="Security analysis and refusal status."
    )
    rag_context_used: bool = Field(
        default=False,
        description="True if ChromaDB policy documents were referenced in answering."
    )
    response_urdu_lish: str = Field(
        ...,
        min_length=5,
        description="Polite, empathetic customer response in Roman Urdu / UrduLish."
    )
    response_english: str = Field(
        ...,
        min_length=5,
        description="Standard business English translation of the response."
    )
    suggested_next_steps: List[str] = Field(
        default_factory=list,
        description="Actionable next steps or instructions for the customer."
    )

    @field_validator("ticket_details", mode="after")
    @classmethod
    def validate_ticket_consistency(cls, v: Optional[TicketDetails], info) -> Optional[TicketDetails]:
        requires_ticket = info.data.get("requires_ticket", False)
        if requires_ticket and v is None:
            raise ValueError("ticket_details must be provided when requires_ticket is True.")
        return v


class ChatMessage(BaseModel):
    """Single message turn in ChatML format."""
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., min_length=1)


class TrainingConversation(BaseModel):
    """Standardized training conversation record."""
    id: str = Field(..., description="Unique dataset record identifier.")
    messages: List[ChatMessage] = Field(..., min_length=2)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_multiturn: bool = Field(default=False)
    language: LanguageEnum = Field(default=LanguageEnum.URDULISH)
    category: IntentEnum = Field(...)


def parse_assistant_response(raw_text: str) -> ZaryaBankingAssistantResponse:
    """
    Robustly extract and validate JSON from model output text.
    Handles optional markdown fences (```json ... ```) or conversational prefix chatter.
    """
    clean_text = raw_text.strip()

    # Match JSON inside markdown code fence if present
    fence_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    match = re.search(fence_pattern, clean_text, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
    else:
        # Search for first '{' and last '}'
        start_idx = clean_text.find("{")
        end_idx = clean_text.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = clean_text[start_idx : end_idx + 1].strip()
        else:
            raise ValueError(f"No JSON object detected in raw model output: {raw_text[:200]}")

    parsed_dict = json.loads(json_str)
    return ZaryaBankingAssistantResponse(**parsed_dict)
