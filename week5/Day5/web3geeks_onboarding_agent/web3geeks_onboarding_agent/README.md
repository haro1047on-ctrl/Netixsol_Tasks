# Web3Geeks Client-Onboarding Agent

A production-shaped LangGraph agent that triages a prospective client's project inquiry,
converts their budget to USD via a real FX API, matches it against a services catalog,
drafts a scoped proposal, self-corrects via a critique loop, and pauses for human
approval before "sending" the proposal -- wrapped behind a FastAPI service.

Built for Week 5 Capstone. See `EXECUTIVE_REPORT.pdf` for the full write-up (business
goal, architecture, framework rationale, evaluation results, limitations, next steps) and
`evaluation_results_template.xlsx` for the scoring sheet.

## Setup

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your free Gemini key (no credit card required,
get one at https://aistudio.google.com/apikey):

```
GEMINI_API_KEY=your_key_here
```

## Files

| File | Purpose |
|---|---|
| `agent_graph.py` | The LangGraph state, tools, nodes, and compiled graph. Import `graph` and `new_initial_state` from here. |
| `services_catalog.json` | Local data source: Web3Geeks service types, price ranges, and timelines. |
| `api.py` | FastAPI wrapper. Run with `uvicorn api:app --reload`. |
| `evaluation.py` | Runs the agent on 10 test cases (8 normal/varied + 2 adversarial) and prints an automatable-metrics table. |
| `evaluation_results_template.xlsx` | Scoring sheet: all 10 test cases pre-filled, columns for the 6 evaluation criteria left for you to fill in after reading each run's output. |

## Running the API

```bash
uvicorn api:app --reload
```

Start an onboarding run:
```bash
curl -X POST http://127.0.0.1:8000/onboard/start \
  -H "Content-Type: application/json" \
  -d '{
        "client_name": "Alice Chen",
        "project_description": "We want a full NFT marketplace where users can mint and trade art.",
        "budget_amount": 8000,
        "budget_currency": "USD"
      }'
```

This returns a `thread_id` and the drafted proposal (`status: "awaiting_approval"`).
Review the draft, then approve or reject it:
```bash
curl -X POST http://127.0.0.1:8000/onboard/<thread_id>/approve \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

Check a run's status at any time:
```bash
curl http://127.0.0.1:8000/onboard/<thread_id>/status
```

Interactive API docs (Swagger UI) are auto-generated at `http://127.0.0.1:8000/docs`
once the server is running.

## Running the evaluation harness

```bash
python evaluation.py
```

Prints a run-by-run log plus a summary table of automatable metrics (latency, whether
each run reached a successful send, revision count, errors logged). Auto-approves at the
human checkpoint for evaluation purposes only -- the real API always waits for an actual
human decision. Qualitative criteria (factual accuracy, tone, safety) need a human to
read each output and score in `evaluation_results_template.xlsx`.

## Known failure-handling built in

- **Bad input**: `validate_input` rejects missing/invalid fields (empty name, budget <= 0,
  gibberish description) before any LLM or external call happens.
- **Tool timeout/error**: currency conversion calls a real public FX API
  (`open.er-api.com`) with a 5-second timeout; on any failure it degrades gracefully
  (treats the raw amount as USD and logs the failure) instead of crashing the run.
- **Model refusal/generation failure**: every LLM call goes through `safe_llm_invoke`,
  which catches exceptions and flags short refusal-shaped responses; a failure here
  routes to a dedicated `generation_failed_end` node rather than propagating an
  unhandled exception.

## Notes on the Gemini free tier

This project defaults to `gemini-3.1-flash-lite` for cost/rate-limit headroom. If you hit
`429` errors, wait ~60 seconds and retry, or check current free-tier limits at
https://ai.google.dev/gemini-api/docs/pricing.
