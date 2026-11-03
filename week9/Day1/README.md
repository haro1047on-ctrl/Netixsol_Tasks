# Week 9 — Day 1: Architecture, Safety Design & Agent Roles
## Multi-Agent AI Clinic Assistant for Healthcare (City Care Clinics)

### 📌 Milestone Overview
City Care Clinics is a premier healthcare network with 5 outpatient facilities across Lahore and Islamabad (Lahore Gulberg, Lahore DHA, Lahore Johar Town, Islamabad F-8, Islamabad Blue Area) staffed by 30 consultant physicians across 6 specialties.

This repository directory contains the complete, production-grade architectural specifications, safety policies, multi-agent role definitions, conversation flows, and privacy compliance designs for **Week 9 — Day 1**.

---

## 📂 Deliverables Directory Map

| Task # | Deliverable Title | Documentation / Code Link | Description |
| :---: | :--- | :--- | :--- |
| **Task 1** | **Multi-Agent Architecture Research** | [ARCHITECTURE.md](file:///d:/netixsol_work/week9/Day1/docs/ARCHITECTURE.md) | Supervisor vs. Swarm vs. Hierarchical analysis, single vs. multi-agent criteria, shared state vs. message passing, MCP protocol role, HITL patterns, and Mermaid system topology. |
| **Task 2** | **Agent Role Cards (All 8 Agents)** | [AGENT_ROLES.md](file:///d:/netixsol_work/week9/Day1/docs/AGENT_ROLES.md) | Comprehensive Role Cards for all 8 agents (Supervisor, Intake, Triage, Scheduling, Records, Clinical Summary, Prescription Safety, Follow-up) with inputs/outputs, MCP tools, prohibitions, and handoffs. |
| **Task 3** | **Patient Conversation Flows** | [CONVERSATION_FLOWS.md](file:///d:/netixsol_work/week9/Day1/docs/CONVERSATION_FLOWS.md) | Sequence diagrams, state mutations, and bilingual UrduLish dialog transcripts for all 7 required clinical and administrative scenarios. |
| **Task 4** | **Safety & Triage Policy** | [SAFETY_AND_TRIAGE_POLICY.md](file:///d:/netixsol_work/week9/Day1/docs/SAFETY_AND_TRIAGE_POLICY.md) | Clinical red-flag taxonomy across 7 domains, 3-tier urgency classification, exact certified UrduLish 1122 escalation scripts, AI vs. doctor boundary matrix, and legal disclaimers. |
| **Task 5** | **Privacy, Governance & Compliance** | [PRIVACY_AND_COMPLIANCE.md](file:///d:/netixsol_work/week9/Day1/docs/PRIVACY_AND_COMPLIANCE.md) | Sensitive PII/PHI taxonomy under PECA 2016 / PMDC, Presidio & Pakistani regex redaction pipeline, RBAC matrix, SHA-256 tamper-evident audit logs, retention schedules, and UrduLish system prompts. |
| **Engine**| **Clinical State & Schemas** | [clinical_state.py](file:///d:/netixsol_work/week9/Day1/src/clinical_state.py) | Pydantic v2 models and LangGraph `ClinicState` TypedDict for all 8 agents and cryptographic audit chaining. |
| **Engine**| **Triage & Red-Flag Engine** | [triage_engine.py](file:///d:/netixsol_work/week9/Day1/src/triage_engine.py) | Deterministic zero-latency pre-LLM emergency screening and urgency classifier in UrduLish and English. |
| **Engine**| **Pakistani PII Redactor** | [pii_redactor.py](file:///d:/netixsol_work/week9/Day1/src/pii_redactor.py) | Edge privacy gateway scrubbing CNIC (`XXXXX-XXXXXXX-X`), mobile numbers (`03XX-XXXXXXX`), names, and addresses with reversible token vaulting. |
| **Engine**| **Agent Registry & Prompts** | [agent_registry.py](file:///d:/netixsol_work/week9/Day1/src/agent_registry.py) | Central registry of metadata, permitted tools, negative constraints, and production prompts for all 8 agents. |
| **Engine**| **Conversation Simulator** | [conversation_simulator.py](file:///d:/netixsol_work/week9/Day1/src/conversation_simulator.py) | Programmatic test harness verifying all 7 patient journeys end-to-end. |
| **Runner**| **Master Day 1 Validation Suite** | [run_day1.py](file:///d:/netixsol_work/week9/Day1/run_day1.py) | Executable test suite asserting 100% compliance across roles, triage, PII scrubbing, audit hashing, and scenario execution. |

---

## 🚀 Execution & Verification

Run the master Day 1 validation suite directly from PowerShell or Bash:

```bash
python week9/Day1/run_day1.py
```

### Verified Test Results Summary:
- **Task 2 (Agent Roles):** 8/8 agents verified with strict tool whitelists, negative constraints, and system prompts.
- **Task 4 (Safety Triage):** 100% interception of red-flag emergencies (Cardiovascular, Respiratory, Stroke FAST, Hemorrhagic, Neonatal Fever).
- **Task 5 (Privacy Guardrail):** Reversible PII tokenization confirmed for CNIC, mobile, email, and addresses; SHA-256 block hash chaining confirmed.
- **Task 3 (Conversation Flows):** All 7 scenarios simulated and verified without error.
