# Web3Geeks Client-Onboarding Agent — Presentation Outline
### ~5-7 minutes, 7 slides

**Slide 1 — The problem (30s)**
- Every inbound project inquiry needs the same manual first pass: match it to a service, sanity-check the budget, draft a quote.
- Today that's manual and inconsistent between whoever picks it up.

**Slide 2 — What we built (45s)**
- An agent that does intake -> validation -> currency conversion -> service matching -> drafting -> self-correction -> human approval -> send.
- One architecture diagram on screen (the flowchart shown in this session).

**Slide 3 — Why LangGraph (45s)**
- Fixed pipeline + a genuine self-correction loop + a human approval pause that must persist across time.
- CrewAI fits role-based collaboration; this is one controlled pipeline, not a team of specialists.
- A raw hand-rolled loop would mean rebuilding interrupt/resume and state persistence from scratch.

**Slide 4 — Human stays in control (45s)**
- The one consequential action — actually sending a proposal to a client — always pauses for a real approval via the API.
- Show the two-call API pattern: `/onboard/start` -> review draft -> `/onboard/{id}/approve`.

**Slide 5 — How we know it works (60s)**
- 6 evaluation criteria (task success, factual grounding, latency, cost, tone, safety).
- 10 test cases: 5 normal, 3 bad-input, 2 adversarial (prompt injection + unrealistic scope).
- Point to the evaluation results sheet as the source of truth, not a claimed pass rate.

**Slide 6 — What could still go wrong (45s)**
- Static catalog can drift from real pricing; free FX API has no SLA; in-memory checkpointer doesn't survive a restart.
- Most likely failure: an ungrounded price slipping past critique — mitigation is a hard price-range validator node.

**Slide 7 — Next steps & ask (30s)**
- Persistent checkpointer, price-range validator, wider adversarial testing before public traffic.
- Keep the approval gate mandatory until the validator has a track record.
- Ask: sign-off to pilot on a small slice of real inbound inquiries with the approval gate on.
