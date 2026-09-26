"""Vapi Voice Server Powered by Week 7 Day 5 LangGraph AI Agent.

Exposes an OpenAI-compatible Custom LLM endpoint (/vapi/llm/chat/completions)
so Vapi can call the Day 5 LangGraph state machine, tool orchestrator, and
validation engine in real time during live phone or web voice calls.
Also serves the real estate website and secure APIs.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import urllib.request
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles

from graph import run_agent_turn
from logger import default_agent_logger
from state import AgentState, create_initial_state
from config import get_engine
from sqlalchemy import text

# Security and Guardrails imports
from security.auth import verify_api_key, verify_vapi_signature
from security.rate_limiter import check_rate_limit
from security.audit_logger import AuditLogMiddleware
from security.request_validator import RequestValidationMiddleware
from guardrails import input_guard, output_guard

# Learning imports
from learning.dataset import log_full_conversation
from learning.intent_classifier import train as train_classifier

logger = logging.getLogger("VapiServer")

app = FastAPI(title="RealEstate Hub LangGraph Voice Agent (Vapi)")

# Middlewares
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VAPI_TRANSCRIBER_MODEL = os.getenv("VAPI_TRANSCRIBER_MODEL", "nova-3")
VAPI_TRANSCRIBER_LANGUAGE = os.getenv("VAPI_TRANSCRIBER_LANGUAGE", "ur")
VAPI_VOICE_PROVIDER = os.getenv("VAPI_VOICE_PROVIDER", "vapi")
VAPI_VOICE_ID = os.getenv("VAPI_VOICE_ID", "Elliot")
VAPI_ASSISTANT_NAME = os.getenv("VAPI_ASSISTANT_NAME", "RealEstate Hub LangGraph Agent")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "").strip().rstrip("/")
FIRST_MESSAGE = os.getenv(
    "VAPI_FIRST_MESSAGE",
    "Assalam-o-Alaikum! RealEstate Hub mein khush aamdeed. Main aap ka property consultant hoon. Bataiye, aap ghar dekh rahe hain ya flat?"
)

# Persistent in-memory session states keyed by Vapi call ID
CALL_SESSIONS: Dict[str, AgentState] = {}
TOTAL_TURNS = 0


def get_active_ngrok_url() -> str | None:
    """Auto-detect public URL from local ngrok client."""
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={"User-Agent": "realestate-hub/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for t in data.get("tunnels", []):
                if t.get("proto") == "https" and t.get("public_url"):
                    return str(t["public_url"]).strip().rstrip("/")
    except Exception:
        pass
    return None


def get_backend_public_url() -> str:
    ngrok_url = get_active_ngrok_url()
    if ngrok_url:
        return ngrok_url
    return os.getenv("BACKEND_PUBLIC_URL", "").strip().rstrip("/")


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "engine": "LangGraph",
        "backend_public_url": get_backend_public_url(),
        "transcriber": f"Deepgram ({VAPI_TRANSCRIBER_MODEL}, {VAPI_TRANSCRIBER_LANGUAGE})",
        "voice": f"{VAPI_VOICE_PROVIDER} ({VAPI_VOICE_ID})",
    }


@app.get("/vapi/assistant-config")
async def vapi_assistant_config():
    """Inline assistant configuration for Vapi."""
    url = get_backend_public_url()
    if not url:
        return JSONResponse(
            {"error": "BACKEND_PUBLIC_URL is not set and no ngrok tunnel detected."},
            status_code=500,
        )
    return {
        "name": VAPI_ASSISTANT_NAME,
        "language": VAPI_TRANSCRIBER_LANGUAGE,
        "firstMessage": FIRST_MESSAGE,
        "model": {
            "provider": "custom-llm",
            "url": f"{url}/vapi/llm",
            "model": "gemini-2.5-flash",
            "messages": [
                {
                    "role": "system",
                    "content": "RealEstate Hub LangGraph AI Agent. You communicate in Urdu / Roman Urdu (UrduLish) to assist clients with property search and bookings in Pakistan."
                }
            ],
        },
        "transcriber": {
            "provider": "deepgram",
            "model": VAPI_TRANSCRIBER_MODEL,
            "language": VAPI_TRANSCRIBER_LANGUAGE,
            "smartFormat": True,
            "keyterm": ["DHA", "Bahria Town", "Gulberg", "Islamabad", "Lahore", "crore", "lakh"],
        },
        "voice": {
            "provider": VAPI_VOICE_PROVIDER,
            "voiceId": VAPI_VOICE_ID,
        },
    }


def _openai_chunk(model: str, content: str | None = None, finish_reason: str | None = None, cid: str = "", include_role: bool = False) -> dict:
    delta: dict[str, Any] = {}
    if include_role:
        delta["role"] = "assistant"
    if content is not None:
        delta["content"] = content
    return {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


async def _stream_langgraph_response(user_text: str, call_id: str, model: str):
    """Execute LangGraph turn and stream response chunks to Vapi."""
    global TOTAL_TURNS
    cid = f"chatcmpl-{uuid.uuid4().hex[:20]}"

    # Instant role chunk (<1ms) for TTFB
    yield f"data: {json.dumps(_openai_chunk(model, None, None, cid, include_role=True))}\n\n"

    # Input Guardrail Check
    is_safe_input, fallback_input_msg = input_guard.check(user_text)
    if not is_safe_input:
        words = fallback_input_msg.split(" ")
        step = 5
        for i in range(0, len(words), step):
            piece = " ".join(words[i:i + step])
            if i + step < len(words): piece += " "
            yield f"data: {json.dumps(_openai_chunk(model, piece, None, cid))}\n\n"
            await asyncio.sleep(0.02)
        yield f"data: {json.dumps(_openai_chunk(model, None, 'stop', cid))}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Retrieve or initialize session state
    if call_id not in CALL_SESSIONS:
        CALL_SESSIONS[call_id] = create_initial_state(session_id=call_id)

    state = CALL_SESSIONS[call_id]

    try:
        # Run turn through LangGraph StateGraph
        updated_state = await asyncio.to_thread(
            run_agent_turn,
            user_message=user_text,
            current_state=state,
            session_id=call_id,
        )
        CALL_SESSIONS[call_id] = updated_state
        raw_answer = updated_state.get("final_response", "Ji, main aap ki kya madad kar sakta hoon?")
        intent = updated_state.get("intent", "recommendation")
    except Exception as e:
        logger.exception("Error during LangGraph turn processing: %s", e)
        raw_answer = "Maaf kijiye ga, system mein rabta nahi ho saka. Baraye meherbani dobara bataiye."
        intent = "error"

    # Output Guardrail Check
    is_safe_output, safe_answer = output_guard.check(raw_answer)
    
    # Log turn for continual learning
    try:
        log_full_conversation(call_id, [{
            "user_message": user_text,
            "agent_message": safe_answer,
            "intent": intent
        }])
        TOTAL_TURNS += 1
        if TOTAL_TURNS % 10 == 0:
            asyncio.create_task(asyncio.to_thread(train_classifier, True))
    except Exception as e:
        logger.error(f"Failed to log conversation turn: {e}")

    # Stream words cleanly
    words = safe_answer.split(" ")
    step = 5
    for i in range(0, len(words), step):
        piece = " ".join(words[i:i + step])
        if i + step < len(words):
            piece += " "
        yield f"data: {json.dumps(_openai_chunk(model, piece, None, cid))}\n\n"
        await asyncio.sleep(0.02)

    yield f"data: {json.dumps(_openai_chunk(model, None, 'stop', cid))}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/vapi/llm/chat/completions")
@app.post("/vapi/llm")
@app.post("/chat/completions")
@app.post("/vapi/llm/chat/completions/chat/completions")
async def chat_completions(req: Request):
    """OpenAI-compatible Custom LLM endpoint invoked by Vapi."""
    # Security: Rate Limiting
    client_ip = req.client.host if req.client else "Unknown"
    check_rate_limit(client_ip, limit=10, window_sec=60)
    
    # Security: Signature Validation (Optional for Ngrok setup)
    verify_vapi_signature(req)

    body = await req.json()
    model = body.get("model", os.getenv("GROQ_LLM_MODEL", "llama-3.1-70b-versatile"))
    messages = body.get("messages", [])
    call_id = body.get("call", {}).get("id") or str(uuid.uuid4())

    user_text = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_text = m.get("content", "")
            break

    if not user_text.strip():
        user_text = "Hello"

    return StreamingResponse(
        _stream_langgraph_response(user_text=user_text, call_id=call_id, model=model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ==========================================
# Real Estate Website API Endpoints
# ==========================================

@app.get("/api/config")
async def api_get_config():
    """Return public configuration for website frontend."""
    return {
        "vapi_public_key": os.getenv("VAPI_PUBLIC_KEY", "9496558c-f290-42ee-8c13-caafb05e4052"),
        "vapi_assistant_id": os.getenv("VAPI_ASSISTANT_ID", "31e5250a-6a50-47bf-89db-615fb6090422"),
        "backend_public_url": get_backend_public_url(),
        "website_public_key": os.getenv("WEBSITE_PUBLIC_KEY", "public_read_only_key")
    }

@app.get("/api/properties")
async def api_get_properties(
    city: Optional[str] = None, 
    type: Optional[str] = None, 
    budget: Optional[float] = None,
    bedrooms: Optional[int] = None,
    api_key: str = Depends(verify_api_key)
):
    """Secure endpoint to fetch properties for the website."""
    client_ip = "Unknown"
    check_rate_limit(client_ip, limit=60, window_sec=60) # general api limit

    engine = get_engine()
    query = "SELECT * FROM properties WHERE 1=1"
    params = {}
    
    if city:
        query += " AND LOWER(city) = LOWER(:city)"
        params["city"] = city
    if type:
        query += " AND LOWER(property_type) = LOWER(:type)"
        params["type"] = type
    if budget and budget > 0:
        query += " AND price <= :budget"
        params["budget"] = budget
    if bedrooms and bedrooms > 0:
        query += " AND bedrooms >= :bedrooms"
        params["bedrooms"] = bedrooms
        
    query += " LIMIT 20"
    
    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
        return {"success": True, "properties": [dict(r) for r in rows]}


@app.get("/api/stats")
async def api_get_stats(api_key: str = Depends(verify_api_key)):
    """Secure endpoint to fetch summary stats."""
    engine = get_engine()
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM properties")).scalar()
        cities = conn.execute(text("SELECT city, COUNT(*) as c FROM properties GROUP BY city")).mappings().all()
        types = conn.execute(text("SELECT property_type, COUNT(*) as c FROM properties GROUP BY property_type")).mappings().all()
        
    return {
        "success": True,
        "total_properties": total,
        "by_city": [dict(r) for r in cities],
        "by_type": [dict(r) for r in types]
    }


# Mount the website static files safely using absolute directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEBSITE_DIR = os.path.join(BASE_DIR, "website")
os.makedirs(WEBSITE_DIR, exist_ok=True)

@app.get("/")
async def serve_index():
    index_file = os.path.join(WEBSITE_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"message": "RealEstate Hub AI Voice Agent Server Running"})

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

app.mount("/", StaticFiles(directory=WEBSITE_DIR, html=True), name="website")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
