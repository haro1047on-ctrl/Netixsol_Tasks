# """Task 5: Production FastAPI Server for RealEstate Hub AI Voice Agent.
# 
# Features:
# - High performance ASGI framework with Uvicorn
# - Request ID Correlation Middleware & Access Timing
# - Security Headers & CORS Protection
# - Full Health Check Probes (/health, /health/liveness, /health/readiness)
# - Prometheus Telemetry Exposition (/metrics)
# - REST Chat API (/api/v1/chat)
# - Vapi Custom LLM OpenAI-Compatible Streaming Endpoint (/vapi/llm/chat/completions)
# - On-demand Automated Evaluation Trigger (/api/v1/evaluate)
# - Telemetry & Voice QoS Status (/api/v1/monitoring/status)
# """
# from __future__ import annotations
# 
# import asyncio
# import json
# import sys
# import time
# import uuid
# from dataclasses import asdict
# from pathlib import Path
# from typing import Any, Dict, List, Optional
# 
# from fastapi import FastAPI, Request, Response, status
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import JSONResponse, PlainTextResponse, StreamingResponse
# from pydantic import BaseModel
# 
# # Ensure sibling directories resolve cleanly in all run configurations
# _CURRENT_DIR = Path(__file__).resolve().parent
# _DAY6_DIR = _CURRENT_DIR.parent
# _WORKSPACE_DIR = _DAY6_DIR.parent
# _DAY5_DIR = _WORKSPACE_DIR / "day5-langgraph-agent"
# 
# for _p in (str(_DAY6_DIR), str(_DAY5_DIR), str(_WORKSPACE_DIR), str(_CURRENT_DIR)):
#     if _p not in sys.path:
#         sys.path.insert(0, _p)
# 
# from day6_config import CHROMA_DIR, SQLITE_PATH
# from env_validator import app_settings
# from prod_logger import prod_logger, setup_production_logging
# from graph import run_agent_turn
# from monitoring.alerting import alert_manager
# from monitoring.metrics_collector import metrics_collector
# from monitoring.voice_quality_monitor import voice_quality_monitor
# from performance.benchmark_engine import BenchmarkEngine
# from security.security_guardrails import security_guardrail_engine
# from state import create_initial_state
# 
# # Initialize logging
# setup_production_logging(app_settings.LOG_LEVEL)
# 
# app = FastAPI(
#     title="RealEstate Hub AI Voice Agent (Production)",
#     version="1.0.0",
#     description="Enterprise-grade LangGraph Orchestrated Real Estate AI Voice Agent",
#     docs_url="/docs",
#     redoc_url="/redoc",
# )
# 
# # ---------------------------------------------------------------------------
# # Middleware: CORS & Security Headers & Request Tracing
# # ---------------------------------------------------------------------------
# app.add_middleware(
#     CORSMiddleware,
#     allow_origin_regex=".*",
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
# 
# CALL_SESSIONS: Dict[str, Dict[str, Any]] = {}
# 
# 
# @app.middleware("http")
# async def security_and_tracing_middleware(request: Request, call_next):
#     """Add correlation ID, measure latency, and inject enterprise security headers."""
#     request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
#     request.state.request_id = request_id
#     start_time = time.perf_counter()
# 
#     response: Response = await call_next(request)
# 
#     duration_ms = (time.perf_counter() - start_time) * 1000.0
# 
#     # Inject Security Headers
#     response.headers["X-Request-ID"] = request_id
#     response.headers["X-Content-Type-Options"] = "nosniff"
#     response.headers["X-Frame-Options"] = "DENY"
#     response.headers["X-XSS-Protection"] = "1; mode=block"
#     response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
#     response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
# 
#     # Log structured access
#     prod_logger.info(
#         f"{request.method} {request.url.path} status={response.status_code} duration={duration_ms:.2f}ms",
#         extra={"request_id": request_id, "latency_ms": duration_ms},
#     )
#     return response
# 
# 
# # ---------------------------------------------------------------------------
# # Pydantic Request / Response Models
# # ---------------------------------------------------------------------------
# class ChatMessage(BaseModel):
#     role: str
#     content: str
# 
# 
# class ChatRequest(BaseModel):
#     message: str
#     session_id: Optional[str] = None
#     user_phone: Optional[str] = None
# 
# 
# class ChatResponse(BaseModel):
#     session_id: str
#     reply: str
#     intent: str
#     clarification_needed: bool
#     appointment_status: str
#     latency_ms: float
#     security_action: str
# 
# 
# class VapiChatCompletionRequest(BaseModel):
#     model: Optional[str] = "realestate-langgraph-agent"
#     messages: List[ChatMessage]
#     call: Optional[Dict[str, Any]] = None
#     stream: Optional[bool] = True
# 
# 
# # ---------------------------------------------------------------------------
# # Health & Diagnostic Endpoints (Task 5)
# # ---------------------------------------------------------------------------
# @app.get("/")
# async def root_info():
#     return {
#         "service": "RealEstate Hub AI Agent",
#         "version": "1.0.0",
#         "status": "online",
#         "framework": "LangGraph + FastAPI",
#         "voice_engine": "Vapi + Deepgram Nova-3",
#     }
# 
# 
# @app.get("/health", status_code=status.HTTP_200_OK)
# async def health_check():
#     """High-level service status probe."""
#     return {
#         "status": "healthy",
#         "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
#         "uptime_seconds": round(time.time() - metrics_collector.start_time, 2),
#     }
# 
# 
# @app.get("/health/liveness", status_code=status.HTTP_200_OK)
# async def liveness_probe():
#     """Kubernetes Liveness Probe - verifies process is running."""
#     return {"status": "alive"}
# 
# 
# @app.get("/health/readiness", status_code=status.HTTP_200_OK)
# async def readiness_probe():
#     """Kubernetes Readiness Probe - verifies all dependencies (DB, Chroma, Keys)."""
#     checks = {}
#     is_ready = True
# 
#     # 1. Database Check
#     sqlite_p = Path(SQLITE_PATH)
#     db_exists = sqlite_p.exists()
#     checks["sqlite_db"] = "ok" if db_exists else "missing"
#     if not db_exists:
#         is_ready = False
# 
#     # 2. ChromaDB / Knowledge Base Check
#     chroma_p = Path(CHROMA_DIR)
#     chroma_exists = chroma_p.exists() and any(chroma_p.iterdir())
#     checks["chroma_vector_db"] = "ok" if chroma_exists else "fallback_sqlite_kb"
# 
#     # 3. Google API Key Check
#     key_configured = bool(app_settings.GOOGLE_API_KEY and "your_google_api_key" not in app_settings.GOOGLE_API_KEY)
#     checks["google_api_key"] = "configured" if key_configured else "missing"
# 
#     if not is_ready:
#         return JSONResponse(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             content={"status": "not_ready", "checks": checks},
#         )
# 
#     return {"status": "ready", "checks": checks}
# 
# 
# @app.get("/metrics", response_class=PlainTextResponse)
# async def prometheus_metrics():
#     """Prometheus metrics text exposition endpoint (Task 4)."""
#     return metrics_collector.generate_prometheus_metrics()
# 
# 
# # ---------------------------------------------------------------------------
# # Business API Endpoints
# # ---------------------------------------------------------------------------
# @app.post("/api/v1/chat", response_model=ChatResponse)
# async def standard_chat_endpoint(payload: ChatRequest):
#     """Standard REST Chat endpoint for Mobile & Web Applications."""
#     session_id = payload.session_id or f"web_{uuid.uuid4().hex[:8]}"
#     start_time = time.perf_counter()
# 
#     # 1. Security scan
#     scan = security_guardrail_engine.scan_input(payload.message)
#     if not scan.is_safe or scan.action in ("BLOCK", "DEFLECT", "ESCALATE"):
#         duration_ms = (time.perf_counter() - start_time) * 1000.0
#         metrics_collector.record_turn(duration_ms, intent=scan.threat_category or "security")
#         if not scan.is_safe:
#             metrics_collector.record_security_block(scan.threat_category or "threat")
# 
#         return ChatResponse(
#             session_id=session_id,
#             reply=scan.override_response or "",
#             intent=scan.threat_category or "security_block",
#             clarification_needed=True,
#             appointment_status="none",
#             latency_ms=round(duration_ms, 2),
#             security_action=scan.action,
#         )
# 
#     # 2. Get/Initialize session state
#     curr_state = CALL_SESSIONS.get(session_id)
#     if curr_state is None:
#         curr_state = create_initial_state(session_id=session_id)
# 
#     # 3. Run Agent Turn
#     new_state = run_agent_turn(
#         user_message=scan.sanitized_input,
#         current_state=curr_state,
#         session_id=session_id,
#     )
#     CALL_SESSIONS[session_id] = new_state
# 
#     # 4. Extract reply cleanly
#     raw_reply = ""
#     if new_state.get("clarification_prompt"):
#         raw_reply = new_state["clarification_prompt"]
#     elif new_state.get("final_response"):
#         raw_reply = new_state["final_response"]
#     elif new_state.get("agent_response"):
#         raw_reply = new_state["agent_response"]
#     elif new_state.get("conversation_history"):
#         last_m = new_state["conversation_history"][-1]
#         raw_reply = last_m.content if hasattr(last_m, "content") else str(last_m)
# 
#     clean_reply, _ = security_guardrail_engine.scan_output(raw_reply)
# 
#     duration_ms = (time.perf_counter() - start_time) * 1000.0
#     intent = new_state.get("intent", "recommendation")
#     metrics_collector.record_turn(duration_ms, intent=intent)
# 
#     appt_stat = new_state.get("appointment_status", {}).get("status", "none")
#     if appt_stat in ("scheduled", "rescheduled"):
#         metrics_collector.record_booking_attempt(success=True)
# 
#     return ChatResponse(
#         session_id=session_id,
#         reply=clean_reply,
#         intent=intent,
#         clarification_needed=new_state.get("clarification_needed", False),
#         appointment_status=appt_stat,
#         latency_ms=round(duration_ms, 2),
#         security_action="ALLOW",
#     )
# 
# 
# @app.post("/vapi/llm/chat/completions")
# async def vapi_custom_llm_endpoint(request: Request):
#     """OpenAI-Compatible Custom LLM Endpoint for Vapi Live Voice Calls."""
#     body = await request.json()
#     messages = body.get("messages", [])
#     call_meta = body.get("call", {})
#     call_id = call_meta.get("id", f"call_{uuid.uuid4().hex[:8]}")
# 
#     last_user_msg = ""
#     for m in reversed(messages):
#         if m.get("role") == "user":
#             last_user_msg = m.get("content", "")
#             break
# 
#     start_time = time.perf_counter()
# 
#     # Track Voice QoS telemetry
#     voice_quality_monitor.evaluate_voice_turn(
#         call_id=call_id,
#         turn_index=len(messages),
#         transcription_confidence=0.96,
#     )
# 
#     # Security scan
#     scan = security_guardrail_engine.scan_input(last_user_msg)
#     if not scan.is_safe or scan.action in ("BLOCK", "DEFLECT", "ESCALATE"):
#         reply_text = scan.override_response or ""
#         duration_ms = (time.perf_counter() - start_time) * 1000.0
#         metrics_collector.record_turn(duration_ms, intent="security")
#         metrics_collector.record_security_block(scan.threat_category or "security")
#     else:
#         # Agent execution
#         curr_state = CALL_SESSIONS.get(call_id, create_initial_state(session_id=call_id))
#         new_state = run_agent_turn(
#             user_message=scan.sanitized_input,
#             current_state=curr_state,
#             session_id=call_id,
#         )
#         CALL_SESSIONS[call_id] = new_state
# 
#         raw_reply = ""
#         if new_state.get("clarification_prompt"):
#             raw_reply = new_state["clarification_prompt"]
#         elif new_state.get("final_response"):
#             raw_reply = new_state["final_response"]
#         elif new_state.get("agent_response"):
#             raw_reply = new_state["agent_response"]
#         elif new_state.get("conversation_history"):
#             last_m = new_state["conversation_history"][-1]
#             raw_reply = last_m.content if hasattr(last_m, "content") else str(last_m)
# 
#         reply_text, _ = security_guardrail_engine.scan_output(raw_reply)
#         duration_ms = (time.perf_counter() - start_time) * 1000.0
#         metrics_collector.record_turn(duration_ms, intent=new_state.get("intent", "general"))
# 
#     # Return OpenAI SSE Streaming Response format for Vapi
#     async def sse_generator():
#         chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
#         created_ts = int(time.time())
# 
#         # Stream words in SSE chunks
#         words = reply_text.split(" ")
#         for i, word in enumerate(words):
#             content_chunk = word + (" " if i < len(words) - 1 else "")
#             chunk_data = {
#                 "id": chunk_id,
#                 "object": "chat.completion.chunk",
#                 "created": created_ts,
#                 "model": "realestate-langgraph-agent",
#                 "choices": [
#                     {
#                         "index": 0,
#                         "delta": {"content": content_chunk},
#                         "finish_reason": None,
#                     }
#                 ],
#             }
#             yield f"data: {json.dumps(chunk_data)}\n\n"
#             await asyncio.sleep(0.015)
# 
#         # Final chunk
#         final_chunk = {
#             "id": chunk_id,
#             "object": "chat.completion.chunk",
#             "created": created_ts,
#             "model": "realestate-langgraph-agent",
#             "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
#         }
#         yield f"data: {json.dumps(final_chunk)}\n\n"
#         yield "data: [DONE]\n\n"
# 
#     return StreamingResponse(sse_generator(), media_type="text/event-stream")
# 
# 
# @app.post("/api/v1/evaluate")
# async def run_evaluation_endpoint():
#     """Trigger automated benchmark & evaluation suite via API (Task 1 & 3)."""
#     engine = BenchmarkEngine()
#     report, _ = engine.run_benchmark()
#     return asdict(report)
# 
# 
# @app.get("/api/v1/monitoring/status")
# async def monitoring_status():
#     """Live telemetry, active alerts, and SLA compliance metrics."""
#     alerts = alert_manager.check_slos()
#     snapshot = metrics_collector.get_snapshot()
#     return {
#         "telemetry_snapshot": snapshot,
#         "active_alerts": alerts,
#         "total_alerts_count": len(alerts),
#     }
# 
# 
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host=app_settings.HOST, port=app_settings.PORT)
