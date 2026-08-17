"""
Web3Geeks Client-Onboarding Agent
==================================

A LangGraph workflow that takes a prospective client's project inquiry, validates it,
converts their budget to USD (a real external API call), matches it to a services
catalog entry, drafts a scoped proposal, critiques and self-corrects the draft, pauses
for human approval before "sending" it (the one consequential, external-facing action),
and terminates gracefully on three distinct failure paths: bad input, a tool
timeout/error, and model generation failure/refusal.

Framework choice: LangGraph. This workflow is control-heavy and stateful -- it has a
fixed pipeline of named stages, a genuine self-correction loop (critique -> revise),
and a human-in-the-loop pause before a consequential action -- exactly the shape
LangGraph is built for (see Day 3). A CrewAI-style role-based crew would be a worse fit
here: there's no need for multiple collaborating personas with distinct expertise,
just one well-defined pipeline that needs precise control flow, explicit state, and an
interrupt point. A raw hand-rolled loop (Day 1 style) could technically do this too, but
would mean re-implementing conditional routing, an interrupt/resume mechanism, and
checkpointed persistence by hand -- exactly the boilerplate LangGraph removes.
"""

import os
import json
import time
import logging
from typing import TypedDict, Optional, List

import requests
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

load_dotenv()

logger = logging.getLogger("onboarding_agent")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.environ.get("ONBOARDING_MODEL", "gemini-3.1-flash-lite")

llm = ChatGoogleGenerativeAI(model=MODEL, google_api_key=GEMINI_API_KEY, temperature=0)

CATALOG_PATH = os.path.join(os.path.dirname(__file__), "services_catalog.json")
QUALITY_THRESHOLD = 0.7
DEFAULT_MAX_REVISIONS = 2


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
class OnboardingState(TypedDict):
    client_name: str
    project_description: str
    budget_amount: float
    budget_currency: str
    budget_usd: Optional[float]
    input_errors: List[str]
    service_match: str
    service_data: str
    draft_proposal: str
    critique: str
    quality_score: float
    revision_count: int
    max_revisions: int
    approved: Optional[bool]
    generation_failed: bool
    final_output: str
    error_log: List[str]
    token_usage: List[dict]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
def read_catalog() -> dict:
    """Reads the full services catalog from the local JSON data source."""
    with open(CATALOG_PATH) as f:
        return json.load(f)


def convert_to_usd(amount: float, currency: str) -> tuple[Optional[float], Optional[str]]:
    """Converts `amount` from `currency` to USD using a real, free public FX API.

    Returns (usd_amount, error_message). On any failure (timeout, bad response, unknown
    currency), usd_amount is None and error_message explains why -- callers should
    degrade gracefully (e.g. treat the original amount as an approximate USD figure)
    rather than crash the whole workflow over a currency lookup failing.
    """
    currency = currency.strip().upper()
    if currency == "USD":
        return amount, None
    try:
        resp = requests.get(f"https://open.er-api.com/v6/latest/{currency}", timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("result") != "success":
            return None, f"FX API returned non-success result for currency '{currency}'."
        rate = data["rates"].get("USD")
        if rate is None:
            return None, f"No USD rate found for currency '{currency}'."
        return round(amount * rate, 2), None
    except requests.exceptions.Timeout:
        return None, "FX API request timed out after 5 seconds."
    except requests.exceptions.RequestException as e:
        return None, f"FX API request failed: {e}"
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        return None, f"FX API returned an unexpected response: {e}"


def safe_llm_invoke(prompt: str, node_name: str) -> tuple[Optional[str], Optional[str]]:
    """Calls the LLM with basic guardrails against empty responses and refusals.

    Returns (content, error). On success, error is None. On failure -- an exception,
    an empty response, or what looks like a short refusal -- content is None and error
    describes what went wrong, so the calling node can route to a graceful failure path
    instead of crashing or silently passing along garbage.
    """
    try:
        response = llm.invoke(prompt)
        content = (response.content or "").strip()

        usage = getattr(response, "usage_metadata", None)
        if usage:
            logger.info(f"[{node_name}] token usage: {usage}")

        if not content:
            return None, "Model returned an empty response."

        refusal_markers = ("i cannot", "i can't help", "i'm unable to", "i won't")
        if len(content) < 80 and any(m in content.lower() for m in refusal_markers):
            return None, f"Model appears to have refused the request: {content[:120]}"

        return content, None
    except Exception as e:
        logger.error(f"[{node_name}] LLM call failed: {e}")
        return None, f"LLM call failed: {e}"


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------
def validate_input_node(state: OnboardingState) -> dict:
    errors = []
    if not state.get("client_name", "").strip():
        errors.append("client_name is required.")
    description = state.get("project_description", "").strip()
    if len(description) < 10:
        errors.append("project_description must be at least 10 characters.")
    elif sum(c.isalpha() for c in description) / max(len(description), 1) < 0.5:
        errors.append("project_description does not look like readable text.")
    budget = state.get("budget_amount")
    if budget is None or budget <= 0:
        errors.append("budget_amount must be a positive number.")

    logger.info(f"[validate_input] errors={errors}")
    return {"input_errors": errors}


def route_after_validate(state: OnboardingState) -> str:
    return "invalid_input_end" if state["input_errors"] else "convert_currency"


def convert_currency_node(state: OnboardingState) -> dict:
    usd, error = convert_to_usd(state["budget_amount"], state.get("budget_currency", "USD"))
    error_log = list(state.get("error_log", []))
    if error:
        error_log.append(f"[convert_currency] {error}")
        logger.warning(f"[convert_currency] falling back to raw amount as USD: {error}")
        # Graceful degradation: treat the raw amount as an approximate USD figure
        # rather than failing the whole workflow over a currency-conversion hiccup.
        usd = state["budget_amount"]
    logger.info(f"[convert_currency] budget_usd={usd}")
    return {"budget_usd": usd, "error_log": error_log}


def triage_node(state: OnboardingState) -> dict:
    catalog = read_catalog()
    content, error = safe_llm_invoke(
        f"A client described their project as: '{state['project_description']}'. "
        f"Which single service from this list best matches it: {list(catalog.keys())}? "
        f"Reply with only the exact service name from the list, nothing else.",
        "triage",
    )
    error_log = list(state.get("error_log", []))
    if error:
        error_log.append(f"[triage] {error}")
        # Fall back to the first catalog entry rather than failing outright --
        # the draft node will still produce something a human can review/correct.
        match = list(catalog.keys())[0]
    else:
        match = content.strip().lower()
        if match not in catalog:
            match = list(catalog.keys())[0]
    logger.info(f"[triage] service_match={match}")
    return {"service_match": match, "error_log": error_log}


def retrieve_node(state: OnboardingState) -> dict:
    catalog = read_catalog()
    entry = catalog.get(state["service_match"], {})
    data = json.dumps(entry)
    logger.info(f"[retrieve] service_data={data}")
    return {"service_data": data}


def draft_proposal_node(state: OnboardingState) -> dict:
    guidance = f"\n\nAddress this feedback from a previous draft: {state['critique']}" if state.get("critique") else ""
    prompt = (
        f"Write a short, professional client proposal for Web3Geeks.\n"
        f"Client: {state['client_name']}\n"
        f"Project: {state['project_description']}\n"
        f"Matched service: {state['service_match']}\n"
        f"Service details: {state['service_data']}\n"
        f"Client's budget: ${state['budget_usd']:.2f} USD\n"
        f"Include a recommended price within the service's range, a rough timeline, "
        f"and one sentence on whether the budget is realistic for this scope.{guidance}"
    )
    content, error = safe_llm_invoke(prompt, "draft_proposal")
    error_log = list(state.get("error_log", []))
    if error:
        error_log.append(f"[draft_proposal] {error}")
        return {"generation_failed": True, "error_log": error_log}
    return {
        "draft_proposal": content,
        "generation_failed": False,
        "revision_count": state.get("revision_count", 0),
        "error_log": error_log,
    }


def route_after_draft(state: OnboardingState) -> str:
    return "generation_failed_end" if state.get("generation_failed") else "critique"


def critique_node(state: OnboardingState) -> dict:
    content, error = safe_llm_invoke(
        f"Rate this client proposal from 0.0 to 1.0 for clarity, whether it names a "
        f"specific price and timeline, and whether the tone is professional. "
        f"Proposal:\n{state['draft_proposal']}\n\n"
        f"Reply in the exact format:\nSCORE: <number>\nFEEDBACK: <one sentence>",
        "critique",
    )
    revision_count = state.get("revision_count", 0)
    error_log = list(state.get("error_log", []))
    if error:
        error_log.append(f"[critique] {error}")
        # If critique itself fails, don't loop forever -- accept the current
        # draft as-is and let the human reviewer at the approval gate judge it.
        return {"quality_score": 1.0, "critique": "", "revision_count": revision_count + 1, "error_log": error_log}

    try:
        score_line = [l for l in content.splitlines() if l.upper().startswith("SCORE")][0]
        score = float(score_line.split(":", 1)[1].strip())
    except (IndexError, ValueError):
        score = 0.5
    feedback_lines = [l for l in content.splitlines() if l.upper().startswith("FEEDBACK")]
    feedback = feedback_lines[0].split(":", 1)[1].strip() if feedback_lines else ""

    logger.info(f"[critique] pass {revision_count}: score={score}, feedback={feedback!r}")
    return {"quality_score": score, "critique": feedback, "revision_count": revision_count + 1, "error_log": error_log}


def route_after_critique(state: OnboardingState) -> str:
    below_threshold = state["quality_score"] < QUALITY_THRESHOLD
    retries_left = state["revision_count"] < state["max_revisions"]
    if below_threshold and retries_left:
        return "draft_proposal"
    return "publish_gate"


def publish_gate_node(state: OnboardingState) -> dict:
    """No-op node whose only purpose is an interrupt point before sending."""
    logger.info("[publish_gate] paused for human approval")
    return {}


def route_after_gate(state: OnboardingState) -> str:
    return "send_proposal" if state.get("approved") else "rejected_end"


def send_proposal_node(state: OnboardingState) -> dict:
    final = f"[SENT TO {state['client_name']}]\n\n{state['draft_proposal']}"
    logger.info("[send_proposal] proposal sent")
    return {"final_output": final}


def rejected_end_node(state: OnboardingState) -> dict:
    logger.info("[rejected_end] human declined to send the proposal")
    return {"final_output": "Proposal was not sent (rejected by reviewer)."}


def invalid_input_end_node(state: OnboardingState) -> dict:
    logger.info(f"[invalid_input_end] {state['input_errors']}")
    return {"final_output": f"Request rejected -- invalid input: {'; '.join(state['input_errors'])}"}


def generation_failed_end_node(state: OnboardingState) -> dict:
    logger.info(f"[generation_failed_end] {state.get('error_log', [])}")
    return {"final_output": "Proposal generation failed and needs manual follow-up. See error_log."}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------
def build_graph():
    builder = StateGraph(OnboardingState)

    builder.add_node("validate_input", validate_input_node)
    builder.add_node("convert_currency", convert_currency_node)
    builder.add_node("triage", triage_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("draft_proposal", draft_proposal_node)
    builder.add_node("critique", critique_node)
    builder.add_node("publish_gate", publish_gate_node)
    builder.add_node("send_proposal", send_proposal_node)
    builder.add_node("rejected_end", rejected_end_node)
    builder.add_node("invalid_input_end", invalid_input_end_node)
    builder.add_node("generation_failed_end", generation_failed_end_node)

    builder.add_edge(START, "validate_input")
    builder.add_conditional_edges(
        "validate_input", route_after_validate,
        {"convert_currency": "convert_currency", "invalid_input_end": "invalid_input_end"},
    )
    builder.add_edge("convert_currency", "triage")
    builder.add_edge("triage", "retrieve")
    builder.add_edge("retrieve", "draft_proposal")
    builder.add_conditional_edges(
        "draft_proposal", route_after_draft,
        {"critique": "critique", "generation_failed_end": "generation_failed_end"},
    )
    builder.add_conditional_edges(
        "critique", route_after_critique,
        {"draft_proposal": "draft_proposal", "publish_gate": "publish_gate"},
    )
    builder.add_conditional_edges(
        "publish_gate", route_after_gate,
        {"send_proposal": "send_proposal", "rejected_end": "rejected_end"},
    )
    builder.add_edge("send_proposal", END)
    builder.add_edge("rejected_end", END)
    builder.add_edge("invalid_input_end", END)
    builder.add_edge("generation_failed_end", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer, interrupt_before=["publish_gate"])


graph = build_graph()


def new_initial_state(client_name: str, project_description: str, budget_amount: float,
                       budget_currency: str = "USD", max_revisions: int = DEFAULT_MAX_REVISIONS) -> OnboardingState:
    return {
        "client_name": client_name,
        "project_description": project_description,
        "budget_amount": budget_amount,
        "budget_currency": budget_currency,
        "budget_usd": None,
        "input_errors": [],
        "service_match": "",
        "service_data": "",
        "draft_proposal": "",
        "critique": "",
        "quality_score": 0.0,
        "revision_count": 0,
        "max_revisions": max_revisions,
        "approved": None,
        "generation_failed": False,
        "final_output": "",
        "error_log": [],
        "token_usage": [],
    }
