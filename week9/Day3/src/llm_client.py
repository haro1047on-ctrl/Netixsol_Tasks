"""City Care Clinics - Unified LLM Client for Specialist Agents.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Provides structured inference with Google Gemini (gemini-3.8-flash) as primary high-speed provider,
Groq (qwen/qwen3.8-27b) with OTPM rate-limit management, and deterministic offline safety fallback.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger("citycare.llm")


class UnifiedLLMClient:
    """Production Multi-Provider LLM Client (Gemini 3.8 Flash + Groq + Safe Fallback)."""

    def __init__(
        self,
        primary_provider: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.gemini_api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        self.groq_api_key = (os.getenv("GROQ_API_KEY") or "").strip()

        # Provider selection
        configured_provider = (primary_provider or os.getenv("LLM_PROVIDER") or "").lower()
        if configured_provider in ["gemini", "google"] and self.gemini_api_key:
            self.provider = "gemini"
        elif configured_provider == "groq" and self.groq_api_key:
            self.provider = "groq"
        elif self.gemini_api_key:
            self.provider = "gemini"
        elif self.groq_api_key:
            self.provider = "groq"
        else:
            self.provider = "offline"

        # Model names
        self.gemini_model_name = os.getenv("GEMINI_MODEL") or "gemini-3.8-flash"
        self.groq_model_name = model_name or os.getenv("GROQ_MODEL") or "qwen/qwen3.8-27b"

        # Initialize clients
        self.gemini_model = None
        self.groq_client = None

        if self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel(self.gemini_model_name)
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")

        if self.groq_api_key:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=self.groq_api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Groq client: {e}")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
        response_format_json: bool = False
    ) -> str:
        """Generates text from LLM with automatic multi-provider failover."""
        # Determine call order based on chosen provider
        providers_to_try = []
        if self.provider == "groq":
            providers_to_try = ["groq", "gemini"]
        elif self.provider == "gemini":
            providers_to_try = ["gemini", "groq"]
        else:
            providers_to_try = ["groq", "gemini"]

        for prov in providers_to_try:
            if prov == "groq" and self.groq_client:
                try:
                    messages = []
                    if system_prompt:
                        messages.append({"role": "system", "content": system_prompt})
                    messages.append({"role": "user", "content": prompt})

                    kwargs: Dict[str, Any] = {
                        "model": self.groq_model_name,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": min(max_tokens, 250)  # Constrain to stay under Groq 1000 OTPM ceiling
                    }
                    if response_format_json:
                        kwargs["response_format"] = {"type": "json_object"}

                    response = self.groq_client.chat.completions.create(**kwargs)
                    if response and response.choices and response.choices[0].message.content:
                        return response.choices[0].message.content.strip()
                except Exception as e:
                    logger.warning(f"Groq generation error: {e}. Attempting failover...")

            elif prov == "gemini" and self.gemini_model:
                try:
                    full_prompt = prompt
                    if system_prompt:
                        full_prompt = f"System Instructions:\n{system_prompt}\n\nUser Message:\n{prompt}"

                    generation_config: Dict[str, Any] = {
                        "temperature": temperature,
                        "max_output_tokens": min(max_tokens, 600),
                    }
                    if response_format_json:
                        generation_config["response_mime_type"] = "application/json"

                    response = self.gemini_model.generate_content(
                        full_prompt,
                        generation_config=generation_config
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception as e:
                    logger.warning(f"Gemini generation error: {e}. Attempting failover...")

        # Safe offline fallback if all providers fail
        if response_format_json:
            return json.dumps({
                "status": "FALLBACK_PARSED",
                "extracted": prompt[:150]
            })
        return "City Care Clinics Assistant is operating in verified offline safety mode."

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        fallback_default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generates and safely parses JSON object from LLM output."""
        system_with_json = (system_prompt or "") + "\nRespond with valid RFC 8259 JSON only."
        raw_output = self.generate(
            prompt=prompt,
            system_prompt=system_with_json,
            temperature=0.1,
            response_format_json=True
        )

        try:
            return json.loads(raw_output)
        except Exception:
            clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_output.strip())
            try:
                return json.loads(clean)
            except Exception:
                return fallback_default or {}
