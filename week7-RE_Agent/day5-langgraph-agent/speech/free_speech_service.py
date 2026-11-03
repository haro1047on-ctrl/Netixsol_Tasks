"""Free-First Speech Synthesis, Transcription & Pakistani Urdu/UrduLish Normalization Service.

Provides:
1. Free Neural Pakistani Urdu TTS via Edge-TTS (ur-PK-UzmaNeural, ur-PK-AsadNeural)
2. Free/Local STT Transcription via Groq Whisper / Faster-Whisper
3. Specialized Urdu/UrduLish Number, Currency (Lakh/Crore) & Plot Size Normalizer
"""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import edge_tts


class UrduTextNormalizer:
    """Normalizes spoken Pakistani Urdu, Roman Urdu, and English code-switching."""

    PAKISTANI_NUMBER_MAP = {
        "ek": 1, "aik": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4,
        "panch": 5, "paanch": 5, "chhay": 6, "che": 6, "saat": 7,
        "aath": 8, "nau": 9, "das": 10, "gyara": 11, "bara": 12,
        "pandrah": 15, "bees": 20, "pachees": 25, "tees": 30,
        "chalees": 40, "pachas": 50, "pachaas": 50, "saath": 60,
        "sattar": 70, "assi": 80, "navve": 90, "sau": 100,
        "dedh": 1.5, "dhai": 2.5, "sawa": 1.25, "sadhe": 0.5,
    }

    @classmethod
    def normalize_currency_pkr(cls, text: str) -> Optional[float]:
        """Extracts and normalizes Pakistani currency expressions (Lakh, Crore) into numeric PKR."""
        t = text.lower().strip()

        # Direct number followed by crore/lakh
        # Example: 1.5 crore, 80 lakh, 3 cr, 50 lacs
        m_crore = re.search(r"(\d+(\.\d+)?)\s*(crore|cr|kror|koti)", t)
        if m_crore:
            return float(m_crore.group(1)) * 10_000_000.0

        m_lakh = re.search(r"(\d+(\.\d+)?)\s*(lakh|lac|lacs|laakh)", t)
        if m_lakh:
            return float(m_lakh.group(1)) * 100_000.0

        # Colloquial Urdu fractions
        if "dedh crore" in t or "deedh crore" in t:
            return 15_000_000.0
        if "dhai crore" in t or "dhaai crore" in t:
            return 25_000_000.0
        if "sawa crore" in t:
            return 12_500_000.0
        if "sadhe teen crore" in t:
            return 35_000_000.0
        if "sadhe char crore" in t:
            return 45_000_000.0

        if "pachas lakh" in t or "pachaas lakh" in t:
            return 5_000_000.0
        if "assi lakh" in t:
            return 8_000_000.0
        if "sattar lakh" in t:
            return 7_000_000.0

        # Pure digits with commas or raw numbers
        m_num = re.search(r"\b(\d{1,3}(,\d{3})+|\d{6,9})\b", t.replace(",", ""))
        if m_num:
            val = float(m_num.group(1).replace(",", ""))
            if val >= 500_000:
                return val

        return None

    @classmethod
    def normalize_plot_size(cls, text: str) -> Tuple[Optional[float], str]:
        """Normalizes land measurements: Kanal, Marla, Sq Yards to standard Marla."""
        t = text.lower().strip()

        # Kanal (1 Kanal = 20 Marla)
        m_kanal = re.search(r"(\d+(\.\d+)?)\s*(kanal|kanals)", t)
        if m_kanal:
            return float(m_kanal.group(1)) * 20.0, "Kanal"

        if "aadha kanal" in t or "adha kanal" in t:
            return 10.0, "Kanal"
        if "dedh kanal" in t:
            return 30.0, "Kanal"
        if "do kanal" in t:
            return 40.0, "Kanal"

        # Marla
        m_marla = re.search(r"(\d+(\.\d+)?)\s*(marla|marle|marlas)", t)
        if m_marla:
            return float(m_marla.group(1)), "Marla"

        if "paanch marla" in t or "panch marla" in t:
            return 5.0, "Marla"
        if "das marla" in t:
            return 10.0, "Marla"

        return None, ""

    @classmethod
    def normalize_phone_number(cls, text: str) -> Optional[str]:
        """Standardizes Pakistani mobile numbers into 03XX-XXXXXXX format."""
        # Find 11 digit local or +92 format
        cleaned = re.sub(r"[\s\-\(\)]", "", text)
        m = re.search(r"(03\d{9})", cleaned)
        if m:
            raw = m.group(1)
            return f"{raw[:4]}-{raw[4:]}"
        m_intl = re.search(r"(\+?923\d{9})", cleaned)
        if m_intl:
            raw = m_intl.group(1).replace("+92", "0")
            return f"{raw[:4]}-{raw[4:]}"
        return None


class FreeSpeechService:
    """100% Free speech synthesis & transcription engine."""

    VOICE_FEMALE_URDU = "ur-PK-UzmaNeural"
    VOICE_MALE_URDU = "ur-PK-AsadNeural"

    def __init__(self, output_dir: Optional[Path] = None):
        if output_dir is None:
            self.output_dir = Path(__file__).resolve().parent.parent / "storage" / "audio"
        else:
            self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def synthesize_speech_async(
        self,
        text: str,
        voice: Optional[str] = None,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        output_filename: Optional[str] = None,
    ) -> Path:
        """Synthesize natural Pakistani Urdu speech using Microsoft Edge Neural TTS."""
        if not voice:
            voice = self.VOICE_FEMALE_URDU

        if not output_filename:
            import uuid
            output_filename = f"speech_{uuid.uuid4().hex[:12]}.mp3"

        out_path = self.output_dir / output_filename
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
        await communicate.save(str(out_path))
        return out_path

    def synthesize_speech(
        self,
        text: str,
        voice: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> Path:
        """Synchronous wrapper for speech synthesis."""
        return asyncio.run(
            self.synthesize_speech_async(
                text=text,
                voice=voice,
                output_filename=output_filename,
            )
        )

    def transcribe_audio_groq_whisper(
        self,
        audio_path: Path,
        prompt: str = "Real estate inquiries in Pakistani Urdu and Roman Urdu (DHA, Bahria Town, Marla, Crore, Lakh).",
    ) -> Dict[str, Any]:
        """Fast speech-to-text using Groq free-tier Whisper API."""
        groq_api_key = os.getenv("GROQ_API_KEY", "")
        if not groq_api_key:
            return {
                "success": False,
                "error": "GROQ_API_KEY is not configured.",
                "transcript": "",
            }

        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)
            with open(audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(audio_path.name, file.read()),
                    model="whisper-large-v3",
                    prompt=prompt,
                    language="ur",
                    response_format="json",
                )
            return {
                "success": True,
                "transcript": transcription.text,
                "provider": "groq-whisper-large-v3",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "transcript": "",
            }


# Singleton instance
default_free_speech_service = FreeSpeechService()
