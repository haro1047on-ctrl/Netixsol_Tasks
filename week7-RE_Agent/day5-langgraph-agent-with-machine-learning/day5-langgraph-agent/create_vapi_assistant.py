"""Create or update the Vapi Assistant for Day 5 LangGraph Agent on your separate Vapi account."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent
ENV_PATH = CURRENT_DIR / ".env"
load_dotenv(ENV_PATH, override=True)

API_BASE = "https://api.vapi.ai"


def _sync_env_file(key: str, value: str) -> None:
    if not ENV_PATH.exists():
        return
    text = ENV_PATH.read_text(encoding="utf-8")
    pattern = rf"^{key}\s*=.*$"
    new_line = f"{key}={value}"
    if re.search(pattern, text, flags=re.MULTILINE):
        text = re.sub(pattern, new_line, text, flags=re.MULTILINE)
    else:
        text += f"\n{new_line}\n"
    ENV_PATH.write_text(text, encoding="utf-8")
    os.environ[key] = value


def _request(method: str, path: str, body: dict, private_key: str) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(body).encode("utf-8"),
        method=method,
        headers={
            "Authorization": f"Bearer {private_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "realestate-hub-langgraph-vapi/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise SystemExit(f"Vapi API returned {e.code}: {detail}")


def build_config(public_url: str) -> dict:
    model_name = os.getenv("GEMINI_LLM_MODEL", "gemini-3.5-flash-lite")
    transcriber_model = os.getenv("VAPI_TRANSCRIBER_MODEL", "nova-3")
    transcriber_language = os.getenv("VAPI_TRANSCRIBER_LANGUAGE", "ur")
    voice_provider = os.getenv("VAPI_VOICE_PROVIDER", "vapi")
    voice_id = os.getenv("VAPI_VOICE_ID", "Elliot")
    assistant_name = os.getenv("VAPI_ASSISTANT_NAME", "RealEstate Hub LangGraph Agent")
    first_message = os.getenv(
        "VAPI_FIRST_MESSAGE",
        "Assalam-o-Alaikum! RealEstate Hub mein khush aamdeed. Main aap ka property consultant hoon. Bataiye, aap ghar dekh rahe hain ya flat?"
    )

    return {
        "name": assistant_name,
        "language": transcriber_language,
        "firstMessage": first_message,
        "model": {
            "provider": "custom-llm",
            "url": f"{public_url.rstrip('/')}/vapi/llm",
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": "RealEstate Hub Day 5 LangGraph AI Agent. You communicate in Urdu / Roman Urdu (UrduLish) to assist clients with property search and bookings in Pakistan."
                }
            ],
        },
        "transcriber": {
            "provider": "deepgram",
            "model": transcriber_model,
            "language": transcriber_language,
            "smartFormat": True,
            "keyterm": [
                "DHA", "Bahria Town", "Gulberg", "Johar Town", "Model Town",
                "Islamabad", "Lahore", "Rawalpindi", "PKR", "crore", "lakh",
                "RealEstate Hub", "Marla", "Kanal",
            ],
        },
        "voice": {
            "provider": voice_provider,
            "voiceId": voice_id,
        },
        "clientMessages": ["transcript", "conversation-update", "speech-update"],
    }


def main():
    load_dotenv(ENV_PATH, override=True)
    private_key = os.getenv("VAPI_PRIVATE_KEY", "").strip()

    if not private_key:
        print("\n" + "=" * 70)
        print("⚠️  VAPI_PRIVATE_KEY is missing in day5-langgraph-agent/.env")
        print("   Please open day5-langgraph-agent/.env and paste your Private Key:")
        print("   VAPI_PRIVATE_KEY=your_private_key_here")
        print("   (Get it from Vapi Dashboard -> API Keys -> Private Key)")
        print("=" * 70 + "\n")
        sys.exit(1)

    existing_id = os.getenv("VAPI_ASSISTANT_ID", "").strip()
    public_url = os.getenv("BACKEND_PUBLIC_URL", "").strip().rstrip("/")

    if not public_url:
        print("\n⚠️  BACKEND_PUBLIC_URL is missing. Please set your ngrok URL in day5-langgraph-agent/.env\n")
        sys.exit(1)

    config = build_config(public_url=public_url)

    if existing_id:
        print(f"Updating existing Vapi Assistant ID: {existing_id} ...")
        result = _request("PATCH", f"/assistant/{existing_id}", config, private_key)
        print(f"[OK] Successfully updated assistant {existing_id} ({result.get('name')}).")
    else:
        print("Creating new Vapi Assistant on your separate account...")
        result = _request("POST", "/assistant", config, private_key)
        new_id = str(result.get("id"))
        _sync_env_file("VAPI_ASSISTANT_ID", new_id)
        print(f"\n[OK] Successfully created new Vapi Assistant!")
        print(f"   Name: {result.get('name')}")
        print(f"   Assistant ID: {new_id}")
        print(f"   Saved VAPI_ASSISTANT_ID to day5-langgraph-agent/.env")

    print(f"   Webhook Custom LLM URL: {public_url}/vapi/llm/chat/completions\n")


if __name__ == "__main__":
    main()
