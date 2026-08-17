"""
FastAPI wrapper for the Web3Geeks client-onboarding agent.

Two-call pattern for the human-in-the-loop step, since a single HTTP request/response
can't sit open across a real human's approval decision:

  1. POST /onboard/start          -> runs the graph up to the publish_gate interrupt,
                                      returns a thread_id and the draft proposal to review.
  2. POST /onboard/{id}/approve   -> resumes the paused run with the human's decision.
  3. GET  /onboard/{id}/status    -> inspect a run's current state at any time.

Run locally with:
    uvicorn api:app --reload
"""

import logging
import time
import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agent_graph import graph, new_initial_state

logger = logging.getLogger("onboarding_api")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

app = FastAPI(title="Web3Geeks Client-Onboarding Agent", version="1.0.0")


# ---------------------------------------------------------------------------
# Request/response models
# ---------------------------------------------------------------------------
class OnboardRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=200)
    project_description: str = Field(..., min_length=1, max_length=4000)
    budget_amount: float = Field(..., gt=0)
    budget_currency: str = Field(default="USD", min_length=3, max_length=3)


class ApprovalRequest(BaseModel):
    approved: bool


class OnboardResponse(BaseModel):
    thread_id: str
    status: str  # "awaiting_approval" | "completed" | "rejected_invalid_input" | "generation_failed"
    draft_proposal: Optional[str] = None
    quality_score: Optional[float] = None
    revision_count: Optional[int] = None
    final_output: Optional[str] = None
    errors: list[str] = []


# ---------------------------------------------------------------------------
# Logging middleware -- request-level latency + basic structured logging
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request, call_next):
    start = time.perf_counter()
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] -> {request.method} {request.url.path}")
    try:
        response = await call_next(request)
    except Exception:
        latency = time.perf_counter() - start
        logger.exception(f"[{request_id}] <- unhandled error after {latency:.2f}s")
        raise
    latency = time.perf_counter() - start
    logger.info(f"[{request_id}] <- {response.status_code} in {latency:.2f}s")
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Latency-Seconds"] = f"{latency:.3f}"
    return response


# ---------------------------------------------------------------------------
# Error handling -- graceful responses for the failure scenarios from Task 2
# ---------------------------------------------------------------------------
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.exception(f"Unhandled exception on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "Something went wrong processing this request."},
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/onboard/start", response_model=OnboardResponse)
def start_onboarding(req: OnboardRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = new_initial_state(
        client_name=req.client_name,
        project_description=req.project_description,
        budget_amount=req.budget_amount,
        budget_currency=req.budget_currency,
    )

    try:
        for _ in graph.stream(initial_state, config=config):
            pass  # each yielded step is already logged inside the node functions
    except Exception as e:
        logger.exception(f"Graph execution failed for thread {thread_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Agent execution failed: {e}")

    snapshot = graph.get_state(config)
    values = snapshot.values

    if values.get("input_errors"):
        return OnboardResponse(
            thread_id=thread_id, status="rejected_invalid_input",
            final_output=values.get("final_output"), errors=values["input_errors"],
        )
    if values.get("generation_failed"):
        return OnboardResponse(
            thread_id=thread_id, status="generation_failed",
            final_output=values.get("final_output"), errors=values.get("error_log", []),
        )
    if snapshot.next == ("publish_gate",):
        return OnboardResponse(
            thread_id=thread_id, status="awaiting_approval",
            draft_proposal=values.get("draft_proposal"),
            quality_score=values.get("quality_score"),
            revision_count=values.get("revision_count"),
            errors=values.get("error_log", []),
        )

    # Shouldn't normally happen (graph paused somewhere unexpected) -- surface it
    # rather than silently returning an incomplete response.
    raise HTTPException(status_code=500, detail=f"Unexpected graph state: next={snapshot.next}")


@app.post("/onboard/{thread_id}/approve", response_model=OnboardResponse)
def approve_onboarding(thread_id: str, req: ApprovalRequest):
    config = {"configurable": {"thread_id": thread_id}}

    existing = graph.get_state(config)
    if not existing.values:
        raise HTTPException(status_code=404, detail="Unknown thread_id.")
    if existing.next != ("publish_gate",):
        raise HTTPException(status_code=409, detail="This run is not awaiting approval.")

    graph.update_state(config, {"approved": req.approved})
    try:
        for _ in graph.stream(None, config=config):
            pass
    except Exception as e:
        logger.exception(f"Resume failed for thread {thread_id}: {e}")
        raise HTTPException(status_code=502, detail=f"Agent execution failed on resume: {e}")

    values = graph.get_state(config).values
    status = "completed" if req.approved else "rejected"
    return OnboardResponse(
        thread_id=thread_id, status=status,
        final_output=values.get("final_output"), errors=values.get("error_log", []),
    )


@app.get("/onboard/{thread_id}/status", response_model=OnboardResponse)
def get_status(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if not snapshot.values:
        raise HTTPException(status_code=404, detail="Unknown thread_id.")

    values = snapshot.values
    if snapshot.next == ("publish_gate",):
        status = "awaiting_approval"
    elif values.get("final_output"):
        status = "completed" if values.get("approved") else "ended"
    else:
        status = "in_progress"

    return OnboardResponse(
        thread_id=thread_id, status=status,
        draft_proposal=values.get("draft_proposal"),
        quality_score=values.get("quality_score"),
        revision_count=values.get("revision_count"),
        final_output=values.get("final_output"),
        errors=values.get("error_log", []),
    )
