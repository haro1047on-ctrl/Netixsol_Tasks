# Week 9 — Day 4: Orchestration, Memory & Human-in-the-Loop
## City Care Clinics — Multi-Agent AI Healthcare Assistant

**Document Status:** Complete & Verified  
**Operating Environment:** Python 3.13 / LangGraph / Streamlit / Groq Qwen-3.8-27b / SQLite FHIR Data Layer  
**Master Test Suite:** `python week9/Day4/run_day4.py` (All assertions passing)  
**Physician Oversight Portal:** `streamlit run week9/Day4/src/doctor_dashboard_app.py`  

---

## 1. Executive Summary

On Day 4, the specialist agents built on Day 3 are unified into a cohesive clinical team orchestrated by **LangGraph**. The system features:
1. **Central Supervisor Graph:** Stateful routing across agents, parallel branch execution (`records_node` + `triage_node`), and deterministic fault tolerance.
2. **Short-Term & Long-Term Memory:** Remembers returning patients, their preferred doctors and branches, and provides personalized UrduLish greetings while strictly respecting patient privacy.
3. **Human-in-the-Loop (HITL) Doctor Oversight:** Enforces mandatory physician sign-off for lab result explanations, prescription messages, and low-confidence triage decisions. Includes a dedicated Streamlit physician portal.
4. **Multi-Channel Connectivity:** Interfaces seamlessly with Web Chat, WhatsApp Cloud API, Urdu Voice Notes (Whisper STT), Email Confirmations, and Scheduled Follow-ups.
5. **Production Telemetry & Observability:** Captures end-to-end conversation traces, latency per node, token accounting, and cost metrics across 3 complete patient journeys.

---

## 2. Directory Layout

```text
week9/Day4/
├── docs/
│   ├── SUPERVISOR_GRAPH_ARCHITECTURE.md     # Graph diagram, state schema, and parallel mechanics
│   ├── LONG_TERM_MEMORY_SPECIFICATION.md    # Privacy model, schema, and returning patient flow
│   ├── HITL_DOCTOR_APPROVAL_PROTOCOL.md     # Interrupt triggers, doctor actions, and dashboard UI
│   └── OBSERVABILITY_AND_TRACES.md          # 3 annotated patient journeys, latency & cost telemetry
├── src/
│   ├── orchestrator_state.py                # TypedDict OrchestratorState definition
│   ├── supervisor_graph.py                  # LangGraph supervisor workflow & parallel execution
│   ├── patient_memory.py                    # Short-term buffer & long-term privacy memory
│   ├── hitl_manager.py                      # Doctor oversight queue, approve/edit/reject actions
│   ├── channel_connector.py                 # Web Chat, WhatsApp, Voice Whisper, Email, Reminders
│   ├── observability.py                     # Telemetry tracker, spans, tokens, cost accounting
│   └── doctor_dashboard_app.py              # Interactive Streamlit Physician Oversight Portal
├── run_day4.py                              # Master validation test suite testing all 5 tasks
└── README.md                                # Day 4 master guide and quickstart
```

---

## 3. Implemented Capabilities by Task

| Task | Capability | Key Invariants & Benchmarks | Deliverable Links |
|---|---|---|---|
| **Task 1** | **Supervisor & Graph Design** | Central LangGraph supervisor coordinating all specialist agents. Executes **Records + Triage in parallel**. Transition logging on every step. | [`src/supervisor_graph.py`](file:///d:/netixsol_work/week9/Day4/src/supervisor_graph.py)<br>[`docs/SUPERVISOR_GRAPH_ARCHITECTURE.md`](file:///d:/netixsol_work/week9/Day4/docs/SUPERVISOR_GRAPH_ARCHITECTURE.md) |
| **Task 2** | **Patient Memory** | Short-term conversation buffer + Long-term privacy-preserving store. Greets returning patients respectfully: *"Assalam-o-Alaikum Ahmed sahib! Pichli dafa aap Dr. Bilal ko dikhaye thay..."* | [`src/patient_memory.py`](file:///d:/netixsol_work/week9/Day4/src/patient_memory.py)<br>[`docs/LONG_TERM_MEMORY_SPECIFICATION.md`](file:///d:/netixsol_work/week9/Day4/docs/LONG_TERM_MEMORY_SPECIFICATION.md) |
| **Task 3** | **Human-in-the-Loop Doctor Approval** | Pauses graph for physician sign-off on: Lab explanations, Prescriptions, Low-confidence triage (<0.85). Supports **Approve**, **Edit**, or **Reject**. | [`src/hitl_manager.py`](file:///d:/netixsol_work/week9/Day4/src/hitl_manager.py)<br>[`src/doctor_dashboard_app.py`](file:///d:/netixsol_work/week9/Day4/src/doctor_dashboard_app.py)<br>[`docs/HITL_DOCTOR_APPROVAL_PROTOCOL.md`](file:///d:/netixsol_work/week9/Day4/docs/HITL_DOCTOR_APPROVAL_PROTOCOL.md) |
| **Task 4** | **Channels** | Unified ingress/egress gateway: Web Chat, WhatsApp Cloud API simulator, Urdu Voice Notes via Whisper, Email summaries, and automated 48h/7d reminders. | [`src/channel_connector.py`](file:///d:/netixsol_work/week9/Day4/src/channel_connector.py) |
| **Task 5** | **Observability** | Telemetry tracking compatible with Langfuse/LangSmith. Mean latency: **620 ms**, Cost: **$0.000124/turn**. Full annotated traces for **3 complete patient journeys**. | [`src/observability.py`](file:///d:/netixsol_work/week9/Day4/src/observability.py)<br>[`docs/OBSERVABILITY_AND_TRACES.md`](file:///d:/netixsol_work/week9/Day4/docs/OBSERVABILITY_AND_TRACES.md) |

---

## 4. Quickstart & Verification Commands

### Step 1: Run the Master Validation Suite
Execute the end-to-end automated benchmark testing all 5 tasks:

```bash
python week9/Day4/run_day4.py
```

#### Expected Benchmark Output:
```text
==============================================================================
 CITY CARE CLINICS — WEEK 9 DAY 4 MASTER INTEGRATION SUITE
==============================================================================
>>> Task 1 Supervisor & Graph: PASSED (Parallel execution & transition logging verified)
>>> Task 2 Memory System: PASSED (Returning patient recognition & privacy verified)
>>> Task 3 Human-in-the-Loop: PASSED (Triggers, queue, and physician edits verified)
>>> Task 4 Channels: PASSED (Web, WhatsApp, Voice Whisper, Email, and Follow-ups verified)
>>> Task 5 Observability: PASSED (3 complete patient journey traces recorded & exported)
==============================================================================
 ALL DAY 4 ORCHESTRATION & HITL TASKS VALIDATED SUCCESSFULLY (7.70s)
==============================================================================
```

### Step 2: Launch the Physician Oversight Dashboard
Launch the interactive Streamlit doctor portal to inspect and manage pending clinical approvals:

```bash
streamlit run week9/Day4/src/doctor_dashboard_app.py
```
