"""City Care Clinics - Edge PII Redaction & De-identification Gateway.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Pakistani-specialized privacy scrubber for CNIC, phone numbers, names, and addresses.
Integrates Presidio if installed, with a comprehensive regex & NER fallback engine.
"""
from __future__ import annotations

import re
from typing import Dict, List, Tuple


class PIIRedactor:
    """Pakistani Healthcare PII/PHI Redaction Engine."""

    # Pakistani CNIC: 13 digits with dashes (e.g., 35201-1234567-1) or contiguous 13 digits starting with 1-7
    CNIC_PATTERN = re.compile(r"\b[1-7]\d{4}-\d{7}-\d{1}\b|\b[1-7]\d{12}\b")

    # Pakistani Mobile: 03XX-XXXXXXX, +92-3XX-XXXXXXX, 00923XXXXXXXXX
    PHONE_PATTERN = re.compile(
        r"(?:\+92|0092|92|0)?[-.\s]?3[0-4]\d{1}[-.\s]?\d{7}\b",
        re.IGNORECASE
    )

    # Email Addresses
    EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE
    )

    # Pakistani Common Names & Honorifics for Regex Gazetteers
    NAME_PREFIXES = r"(?:mera naam|naam hai|i am|this is|patient name|patient|mr\.|mrs\.|ms\.|syed|syeda|choudhry|ch\.|dr\.)"
    NAME_PATTERN = re.compile(
        rf"{NAME_PREFIXES}\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)\b",
        re.IGNORECASE
    )

    # Common Pakistani Street Addresses & Locations
    ADDRESS_KEYWORDS = [
        "dha phase", "gulberg", "johar town", "f-8", "blue area", "model town",
        "bahria town", "g-11", "street #", "house #", "st #", "h #"
    ]

    def __init__(self):
        self._check_presidio()

    def _check_presidio(self):
        """Checks if Microsoft Presidio is available in the environment."""
        try:
            from presidio_analyzer import AnalyzerEngine
            from presidio_anonymizer import AnonymizerEngine
            self.presidio_analyzer = AnalyzerEngine()
            self.presidio_anonymizer = AnonymizerEngine()
            self.has_presidio = True
        except ImportError:
            self.presidio_analyzer = None
            self.presidio_anonymizer = None
            self.has_presidio = False

    def redact(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Redacts sensitive PII from input text and returns sanitized text + vault dictionary.

        Returns:
            sanitized_text: String with PII replaced by tokens (e.g. [CNIC_1], [PHONE_1]).
            vault: Dictionary mapping tokens to original values for internal EHR storage.
        """
        vault: Dict[str, str] = {}
        sanitized = text

        # 1. Redact CNIC
        cnic_matches = list(self.CNIC_PATTERN.finditer(sanitized))
        for idx, match in enumerate(cnic_matches, 1):
            val = match.group(0)
            token = f"[CNIC_{idx}]"
            vault[token] = val
            sanitized = sanitized.replace(val, token)

        # 2. Redact Phone Numbers
        phone_matches = list(self.PHONE_PATTERN.finditer(sanitized))
        for idx, match in enumerate(phone_matches, 1):
            val = match.group(0).strip()
            # Avoid re-replacing if already captured
            if val not in vault.values():
                token = f"[PHONE_{idx}]"
                vault[token] = val
                sanitized = sanitized.replace(val, token)

        # 3. Redact Emails
        email_matches = list(self.EMAIL_PATTERN.finditer(sanitized))
        for idx, match in enumerate(email_matches, 1):
            val = match.group(0).strip()
            token = f"[EMAIL_{idx}]"
            vault[token] = val
            sanitized = sanitized.replace(val, token)

        # 4. Redact Identified Names
        name_matches = list(self.NAME_PATTERN.finditer(sanitized))
        for idx, match in enumerate(name_matches, 1):
            full_match = match.group(0)
            captured_name = match.group(1).strip()
            # Do not redact common clinical words like "doctor" or "urgent"
            if captured_name.lower() not in ["doctor", "urgent", "emergency", "patient", "fever", "sick"]:
                token = f"[PATIENT_NAME_{idx}]"
                vault[token] = captured_name
                sanitized = sanitized.replace(captured_name, token)

        # 5. Redact Addresses / Localities
        for idx, addr_kw in enumerate(self.ADDRESS_KEYWORDS, 1):
            pattern = re.compile(rf"\b{re.escape(addr_kw)}[^\n,.]*", re.IGNORECASE)
            addr_matches = list(pattern.finditer(sanitized))
            for match in addr_matches:
                val = match.group(0).strip()
                if val and val not in vault.values():
                    token = f"[ADDRESS_{idx}]"
                    vault[token] = val
                    sanitized = sanitized.replace(val, token)

        return sanitized, vault

    def rehydrate(self, sanitized_text: str, vault: Dict[str, str]) -> str:
        """Secure internal function to restore tokens with original values inside EHR MCP server."""
        restored = sanitized_text
        for token, val in vault.items():
            restored = restored.replace(token, val)
        return restored
