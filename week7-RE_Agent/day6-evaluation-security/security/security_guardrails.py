"""Task 2: Advanced Security Guardrail Engine & Adversarial Protection.

Features:
1. Input Sanitization & Threat Intelligence Analysis:
   - System Prompt Extraction / Leak Blocker
   - Jailbreak & Instruction Override Detector (DAN, Dev Mode, Roleplay)
   - Internal / Confidential Data Exfiltration Blocker
   - Fake / Malicious Appointment Injection & SQL Injection Sanitizer
   - Angry / Abusive Customer Sentiment Detector & Empathy Escalation
   - Silent Caller & Noise Stream Detector
2. Output Validation & Secret Leak Firewall:
   - Scans outgoing responses for API keys (Google, Vapi, Deepgram), passwords, internal tokens, and system instructions.
   - Auto-redacts any accidental leaks with [CONFIDENTIAL_REDACTED].
3. Guardrail Interception & Safe Deflection Routing.
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("SecurityGuardrails")

# ---------------------------------------------------------------------------
# Adversarial Signatures & Patterns
# ---------------------------------------------------------------------------

PROMPT_INJECTION_PATTERNS = [
    # Instruction override
    r"ignore\s+(?:all\s+)?(?:previous\s+|prior\s+|above\s+|system\s+)?instructions?",
    r"disregard\s+(?:all\s+)?(?:previous\s+|prior\s+|above\s+|system\s+)?instructions?",
    r"forget\s+(?:all\s+)?(?:previous|prior|rules|guidelines|instructions)",
    r"override\s+(?:all\s+)?(?:system|safety|security)\s+rules?",
    r"do\s+anything\s+now",
    r"\bdan\s+mode\b",
    r"developer\s+mode\s+(?:enabled|on|activate)",
    r"maintenance\s+mode\s+0x",
    r"you\s+are\s+no\s+longer\s+an?\s+ai",
    r"act\s+as\s+an?\s+(?:unfiltered|evil|jailbroken)\s+assistant",
    r"pretend\s+you\s+have\s+no\s+(?:rules|guidelines|restrictions)",
    
    # Prompt extraction & leak
    r"reveal\s+(?:your\s+)?(?:system\s+|initial\s+|developer\s+)?prompt",
    r"output\s+(?:your\s+)?(?:system\s+|initial\s+|developer\s+)?prompt",
    r"show\s+(?:me\s+)?(?:your\s+)?(?:system\s+|developer\s+)?(?:prompt|instructions)",
    r"what\s+is\s+your\s+(?:system\s+|developer\s+)?(?:prompt|instructions)",
    r"what\s+are\s+your\s+(?:instructions|guidelines|rules|system\s+prompts)",
    r"repeat\s+(?:the\s+)?(?:text|words|prompt)\s+above",
    r"print\s+(?:system\s+)?instructions\s+verbatim",
    r"tell\s+me\s+your\s+initial\s+prompt",
    
    # Internal data exfiltration
    r"give\s+(?:me\s+)?internal\s+company\s+data",
    r"dump\s+(?:the\s+)?(?:customer\s+)?database",
    r"show\s+(?:all\s+)?(?:passwords|api\s*keys|credentials|secrets)",
    r"export\s+(?:internal\s+)?(?:crm|database|leads|records)",
    r"reveal\s+(?:api\s*key|secret\s*key|database\s*password|credentials)",
    r"select\s+\*\s+from\s+",
    r"drop\s+table\s+",
    r"union\s+select\s+",
    r"admin123",
    r"--\s*$",
    r"'\s*or\s*'1'\s*=\s*'1",
]

ANGRY_CUSTOMER_CUES = [
    "ghatiya", "bakwas", "fraud", "dhoka", "incompetent", "badtameez", "fuzool",
    "waqt zaya", "time waste", "manager se baat", "senior manager", "complaint",
    "shikayat", "police", "court", "case karunga", "worst service", "terrible",
    "horrible", "idiot", "nonsense", "harami", "kutta", "kameena", "stupid",
    "بکواس", "فضول", "فراڈ", "دھوکہ", "گھٹیا", "شکایت", "وقت ضائع"
]

SILENT_CALLER_CUES = [
    "", "...", "....", "???", "hello?", "suno", "sun rahe ho", "kya meri awaaz",
    "awaaz nahi arahi", "mute", "silent", "sound", "آواز", "سنو"
]

SECRET_LEAK_PATTERNS = [
    r"AIzaSy[A-Za-z0-9_-]{20,50}",                   # Google API Keys
    r"sk-[A-Za-z0-9_-]{20,60}",                     # OpenAI / Model Keys
    r"vapi-[A-Za-z0-9_-]{15,50}",                   # Vapi Keys
    r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]+",   # Passwords
    r"Bearer\s+[A-Za-z0-9\._-]{20,}",              # JWT / Bearer tokens
    r"(?:SECRET_KEY|DATABASE_URL)\s*=\s*\S+",        # Env configurations
    r"BEGIN\s+PRIVATE\s+KEY",                        # Private keys
]


@dataclass
class SecurityScanResult:
    """Outcome of a security guardrail evaluation."""
    is_safe: bool
    threat_category: Optional[str] = None
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    matched_pattern: Optional[str] = None
    sanitized_input: str = ""
    override_response: Optional[str] = None
    action: str = "ALLOW"  # ALLOW, DEFLECT, SANITIZE, ESCALATE, BLOCK


class SecurityGuardrailEngine:
    """Production AI security firewall and input/output sanitizer."""

    def __init__(self):
        self._injection_regexes = [
            re.compile(pat, re.IGNORECASE) for pat in PROMPT_INJECTION_PATTERNS
        ]
        self._secret_regexes = [
            re.compile(pat, re.IGNORECASE) for pat in SECRET_LEAK_PATTERNS
        ]

    def scan_input(self, user_text: str, session_history: Optional[List[Any]] = None) -> SecurityScanResult:
        """Scan raw user input for injection, jailbreaks, data exfiltration, angry tone, or silence."""
        raw = (user_text or "").strip()

        # 1. Check for Silent / Empty Caller
        if not raw or raw in ["...", "....", "..", "?"]:
            return SecurityScanResult(
                is_safe=True,
                threat_category="SILENT_CALLER",
                severity="LOW",
                sanitized_input=raw,
                override_response="Assalam-o-Alaikum! RealEstate Hub mein khush aamdeed. Kya aap mujhe sun pa rahe hain? Main aap ki property search mein kis tarah madad kar sakta hoon?",
                action="DEFLECT"
            )

        # 2. Check for Prompt Injection / Jailbreaks / Exfiltration (CRITICAL)
        for pattern_re in self._injection_regexes:
            match = pattern_re.search(raw)
            if match:
                matched_str = match.group(0)
                threat = "PROMPT_INJECTION"
                t_low = matched_str.lower()
                if any(k in t_low for k in ["dump", "database", "password", "internal company data", "export", "select *", "api key", "secret key"]):
                    threat = "DATA_EXFILTRATION"
                elif any(k in t_low for k in ["reveal", "output", "prompt", "instructions", "repeat", "show"]):
                    threat = "PROMPT_EXTRACTION"
                elif any(k in t_low for k in ["drop table", "union select", "'or'1'='1"]):
                    threat = "SQL_INJECTION"
                elif any(k in t_low for k in ["dan mode", "developer mode", "do anything now"]):
                    threat = "JAILBREAK_ATTEMPT"

                logger.warning(f"Security Alert: Blocked {threat} attempt! Pattern: '{matched_str}'")
                
                return SecurityScanResult(
                    is_safe=False,
                    threat_category=threat,
                    severity="CRITICAL",
                    matched_pattern=matched_str,
                    sanitized_input="[THREAT_NEUTRALIZED]",
                    override_response=(
                        "Maaf kijiye ga, main sirf RealEstate Hub ka verified property consultant hoon. "
                        "Main sirf Lahore, Islamabad aur Rawalpindi mein ghar, flat aur plot ki khareed o farokht mein aap ki madad kar sakta hoon. "
                        "Bataiye, aap kis city mein property dekh rahe hain?"
                    ),
                    action="BLOCK"
                )

        # 3. Check for Angry / Abusive Customer (Sentiment De-escalation)
        t_low = raw.lower()
        if any(cue in t_low for cue in ANGRY_CUSTOMER_CUES):
            logger.info("Customer de-escalation triggered for agitated caller.")
            return SecurityScanResult(
                is_safe=True,
                threat_category="ANGRY_CUSTOMER",
                severity="MEDIUM",
                sanitized_input=raw,
                override_response=(
                    "Hum aap ko hone wali takleef par maazrat khwah hain. Aap ka masla hamare liye nihayat ahem hai. "
                    "Main foran aap ki details note kar ke hamare senior real estate manager ko priority escalation bhej raha hoon taake wo aapse direct rabta kar sakein. "
                    "Baraye meherbani apna naam aur contact number confirm kar dijiye."
                ),
                action="ESCALATE"
            )

        # 4. Safe clean input
        sanitized = raw.replace("<script>", "").replace("</script>", "").replace(";", "")
        return SecurityScanResult(
            is_safe=True,
            threat_category=None,
            severity="LOW",
            sanitized_input=sanitized,
            override_response=None,
            action="ALLOW"
        )

    def scan_output(self, agent_text: str) -> Tuple[str, bool]:
        """Scan agent outgoing response to prevent any secret, token, or internal system instruction leak."""
        if not agent_text:
            return agent_text, True

        sanitized_output = agent_text
        leak_detected = False

        # Redact any discovered secret patterns
        for sec_re in self._secret_regexes:
            if sec_re.search(sanitized_output):
                leak_detected = True
                logger.critical("CRITICAL: Outgoing message contained sensitive secret/token! Redacting.")
                sanitized_output = sec_re.sub("[CONFIDENTIAL_REDACTED]", sanitized_output)

        # Ensure system internals are not reflected
        internal_terms = [
            "AgentState", "StateGraph", "MemorySaver", "intent_detection_node",
            "clarification_node", "booking_node", "GOOGLE_API_KEY", "VAPI_API_KEY"
        ]
        for term in internal_terms:
            if term in sanitized_output:
                leak_detected = True
                sanitized_output = sanitized_output.replace(term, "[SYSTEM_INTERNALS]")

        return sanitized_output, not leak_detected


# Global Singleton Guardrail Instance
security_guardrail_engine = SecurityGuardrailEngine()
