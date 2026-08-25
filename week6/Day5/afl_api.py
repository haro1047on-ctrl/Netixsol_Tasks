"""
================================================================================
AFL ASSISTANT — FastAPI Production API Wrapper
Day 5: Capstone Deployment
================================================================================
Exposes the LangGraph AFL app as a REST API.

Endpoints:
  POST /chat   — accepts message + conversation_id, returns response + metadata
  GET  /health — liveness check

Run with:
  uvicorn afl_api:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# ── Add Day5 current dir to path ──────────────────────────────────────────────
CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from langgraph_afl_agent import afl_app

# ── Logging setup ─────────────────────────────────────────────────────────────
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("afl_api")

STRUCTURED_LOG_FILE = os.path.join(LOGS_DIR, "afl_api_structured.jsonl")


def write_structured_log(entry: Dict[str, Any]) -> None:
    """Append a structured JSON log entry to the JSONL log file."""
    with open(STRUCTURED_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


# ── In-memory conversation state store ───────────────────────────────────────
conversation_store: Dict[str, Dict[str, Any]] = {}

BLANK_STATE = {
    "user_query": "",
    "messages": [],
    "detected_intent": "",
    "entities": {},
    "tool_results": {},
    "validation_status": "",
    "clarification_prompt": None,
    "final_response": ""
}

# ── FastAPI App ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="AFL AI Assistant API",
    description="Domain-locked AFL chat + prediction assistant powered by LangGraph.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Models ─────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    response: str
    intent: str
    validation_status: str
    tools_called: list
    latency_ms: float
    disclaimer: Optional[str] = None


# ── Rate / Abuse Tracking ─────────────────────────────────────────────────────
REQUEST_LOG: Dict[str, list] = {}   # conversation_id -> list of timestamps
MAX_OFF_TOPIC_IN_WINDOW = 5         # max off-topic queries per conversation
WINDOW_SECONDS = 120                # sliding window


def check_abuse(conversation_id: str, intent: str) -> bool:
    """Returns True if conversation appears to be abusing the system."""
    now = time.time()
    history = REQUEST_LOG.get(conversation_id, [])
    # Keep only entries within window
    history = [(ts, i) for ts, i in history if now - ts < WINDOW_SECONDS]
    off_topic_count = sum(1 for _, i in history if i == "off_topic")
    if intent == "off_topic":
        off_topic_count += 1
    history.append((now, intent))
    REQUEST_LOG[conversation_id] = history
    return off_topic_count >= MAX_OFF_TOPIC_IN_WINDOW


# ── Chat Endpoint ─────────────────────────────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    conversation_id = req.conversation_id or str(uuid.uuid4())
    message = req.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    if len(message) > 1000:
        raise HTTPException(status_code=400, detail="Message too long (max 1000 chars).")

    # Build fresh state (stateless per request — conversation history managed externally)
    state = {**BLANK_STATE, "user_query": message}

    start_time = time.perf_counter()
    try:
        result = afl_app.invoke(state)
    except Exception as e:
        logger.error(f"LangGraph invocation error: {e}")
        raise HTTPException(status_code=500, detail=f"Assistant error: {str(e)}")
    latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

    intent = result.get("detected_intent", "unknown")
    validation = result.get("validation_status", "")
    response_text = result.get("final_response", "I could not generate a response.")
    tool_results = result.get("tool_results", {})
    tools_called = list(tool_results.get("data", {}).keys()) if tool_results else []

    # Abuse detection
    if check_abuse(conversation_id, intent):
        response_text = (
            "This conversation has sent multiple off-topic requests. "
            "I am an AFL-only assistant. Please ask an AFL-related question or start a new session."
        )

    # Add disclaimer to all prediction responses
    disclaimer = None
    if intent == "prediction" and "predicted probability" not in response_text.lower():
        disclaimer = "All predictions are predicted probabilities, not certainties. Match outcomes depend on real-world factors not captured in historical data."

    # Structured logging
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "conversation_id": conversation_id,
        "query": message,
        "intent": intent,
        "validation_status": validation,
        "tools_called": tools_called,
        "latency_ms": latency_ms,
        "response_length": len(response_text),
    }
    write_structured_log(log_entry)
    logger.info(f"[{conversation_id}] intent={intent} latency={latency_ms}ms tools={tools_called}")

    return ChatResponse(
        conversation_id=conversation_id,
        response=response_text,
        intent=intent,
        validation_status=validation,
        tools_called=tools_called,
        latency_ms=latency_ms,
        disclaimer=disclaimer,
    )


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "AFL AI Assistant", "version": "1.0.0"}


# ── API Docs Meta ─────────────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "message": "AFL AI Assistant API — visit /docs for Swagger UI",
        "endpoints": {
            "POST /chat": "Send a message, get AFL response",
            "GET /health": "Health check",
            "GET /docs": "Swagger API documentation",
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("afl_api:app", host="0.0.0.0", port=8000, reload=True)
