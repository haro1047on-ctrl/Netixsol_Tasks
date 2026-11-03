# City Care Clinics — Codebase Audit & System Inventory

**Author:** Senior AI Agent Architect & Healthcare Software Engineer  
**Date:** October 9, 2026  
**Status:** Audit Completed (Pending Client Approval for Implementation)  
**Target System:** City Care Clinics Multi-Agent Healthcare AI Assistant  

---

## 1. Executive Summary

This audit assesses the state of the **City Care Clinics Multi-Agent Healthcare AI Assistant** repository (`week9/Day1` through `week9/Day5`).

The project contains a well-structured domain foundation:
1. **Clinical Triage & Red-Flag Engine** (`Day1`): Deterministic regex patterns covering cardiovascular, respiratory, neurological (FAST), pediatric, and obstetric red flags in both UrduLish and English.
2. **FHIR Relational Database Baseline** (`Day2`): SQLAlchemy models for `Patient`, `Practitioner`, `Appointment`, `Observation`, `MedicationRequest`, `Condition`, `AllergyIntolerance`, and `ClinicBranchInfo`.
3. **Medical Knowledge RAG** (`Day2`): ChromaDB vector store over clinic FAQs, fees, timings, test preparations, and bilingual patient leaflets.
4. **Prescription Safety Rules** (`Day2`): Deterministic pharmacological verification of allergy conflicts (e.g., Penicillin/Augmentin), drug interactions (e.g., Warfarin/Aspirin), daily dose ceilings (e.g., Panadol > 4000mg/day), and contraindications.
5. **Specialist Agents** (`Day3`): 7 specialized clinical agents (Intake, Triage, Scheduling, Records, Clinical Summary, Prescription Safety, Follow-up).
6. **LangGraph Supervisor Orchestrator** (`Day4`): `StateGraph` state machine coordinating multi-agent routing, parallel node execution, and telemetry.
7. **FastAPI & Streamlit Portals** (`Day5`): REST API endpoints and dual Streamlit interfaces for patients and attending physicians.

### Key Finding: Simulation vs. Production Reality
While the baseline demonstration scripts (`run_day1.py` through `run_day5.py`) execute successfully in demo mode, a rigorous architectural inspection reveals **critical gaps, simulated behaviors, and safety hazards** that prevent this system from operating as a secure, persistent, and verifiable clinic assistant:
- **Simulated Notifications:** MCP notifications and channel dispatchers log messages to in-memory Python lists (`NOTIFICATION_LOGS.append(...)`). No real SMTP or email delivery provider is connected.
- **In-Memory Reminders:** Follow-up reminders are queued in an in-memory list (`ScheduledReminderQueue.queue`). All reminder jobs are lost on process restart.
- **Volatile Conversation & Approval State:** LangGraph uses in-memory `MemorySaver()`, conversation threads are not saved to the database, HITL approvals and longitudinal memories are stored in unindexed local JSON files (`data/hitl_pending_approvals.json`, `data/patient_long_term_memory.json`), and the HITL gate in `supervisor_graph.py` fails to pause execution on pending approvals (falling through to dispatch).
- **Security & Authorization Absence:** API routes accept unauthenticated requests with arbitrary `patient_id` parameters (defaulting to `"PT_0001"`). CORS is configured to `*`. Any user can query any patient's records or trigger appointments.
- **Concurrency & Rescheduling Race Conditions:** The scheduling agent lacks database row-level locking or unique constraints, allowing double-booking under concurrent requests. Furthermore, rescheduling an appointment sets `appt.status = "rescheduled"` while keeping the slot time updated, which causes availability queries to treat the new slot as free.
- **Database Degradation in Health Check:** In `api_server.py`, `session.execute("SELECT 1")` fails under SQLAlchemy 2.0 (requiring `text("SELECT 1")`), causing the health check endpoint to report the database status as `"DEGRADED"`.
- **Missing Root Dependencies & Formal Pytest Suite:** The repository lacks a pinned root `requirements.txt` (causing GitHub Actions CI to fail), and the project lacks an automated `pytest` test suite verifying specific clinical failure and recovery modes (Tests A through L).

---

## 2. Comprehensive Audit Matrix

| Severity | Component / File | Identified Issue | Real-World Impact | Proposed Fix |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `Day2/src/mcp_servers/notifications_server.py`, `Day4/src/channel_connector.py` | **Simulated Email & Message Delivery:** `send_email_summary` appends to in-memory `NOTIFICATION_LOGS` without calling an SMTP or email API provider. | No actual emails are ever sent. Appointment confirmations, cancellations, and doctor communications fail silently while reporting success. | Implement genuine SMTP email provider with configurable credentials, secure TLS, delivery status tracking, and error reporting. |
| **CRITICAL** | `Day4/src/channel_connector.py` | **In-Memory Scheduled Reminders:** `ScheduledReminderQueue` stores pending follow-ups in an in-memory list `self.queue = []`. | Server restart or crash completely wipes all pending 48-hour and 7-day medication and appointment reminders. | Implement persistent database-backed reminder queue with status tracking (`QUEUED`, `PROCESSING`, `SENT`, `FAILED`). |
| **CRITICAL** | `Day4/src/supervisor_graph.py` | **HITL Gate Fallthrough:** When `hitl_gate_node` flags an interrupt (`hitl_required=True`, `hitl_status="PENDING"`), `doctor_review_node` does not pause graph execution. It proceeds directly to `prescription_and_followup_node` and dispatches unapproved medical text to the patient. | AI sends unapproved lab interpretations and prescription instructions directly to patients, violating clinic medical safety policy. | Refactor graph with LangGraph interrupts / durable state pause so outbound dispatch is blocked until an explicit physician review action is recorded. |
| **CRITICAL** | `Day5/src/api_server.py`, `Day2/src/mcp_servers/patient_records_server.py` | **Zero Authentication & Authorization:** `ChatRequest` defaults to `patient_id="PT_0001"`. Any user can query or modify any patient's chart, appointments, and medical history simply by passing their ID. | Complete violation of patient privacy (HIPAA/GDPR/Pakistani health data principles). Unauthorized access to sensitive medical records. | Implement JWT-based patient and doctor authentication, session tokens, and strict role-based access control (RBAC) ensuring patients access only their own records. |
| **CRITICAL** | `Day3/src/scheduling_agent.py` | **Reschedule Slot Collision & Status Bug:** When an appointment is rescheduled, `appt.status` is set to `"rescheduled"`. Availability queries only check `status.in_(["booked", "arrived"])`, meaning the newly rescheduled slot is seen as empty by subsequent searches. | Double bookings on rescheduled slots. Broken audit trail of original vs. new appointment dates. | Keep confirmed appointments as `"booked"`, maintain previous slot history, and use transactional atomic updates. |
| **HIGH** | `Day3/src/scheduling_agent.py` | **Missing Concurrency Protection:** Booking checks check availability with a plain `SELECT` query followed later by `session.add(new_appt)`. No database unique constraint exists on `(practitioner_id, slot_datetime)` for active bookings. | Concurrent booking requests for the same doctor and slot both succeed, causing double booking. | Add database unique constraint on `(practitioner_id, slot_datetime, status)` and wrap slot reservation in an atomic transaction with immediate re-validation. |
| **HIGH** | `Day4/src/supervisor_graph.py` | **Volatile Conversation Checkpoints:** `ClinicSupervisorOrchestrator` uses `MemorySaver()`, which resides entirely in RAM. | Application restarts or worker recycling destroy all multi-turn conversation states and session history. | Implement persistent database checkpointing or durable session thread storage in SQLite/PostgreSQL. |
| **HIGH** | `Day4/src/hitl_manager.py`, `Day4/src/patient_memory.py` | **JSON File Storage for Critical State:** HITL pending approvals and patient longitudinal memory are serialized to flat JSON files (`data/hitl_pending_approvals.json`, `data/patient_long_term_memory.json`). | Risk of file corruption under concurrent writes, unindexed queries, lack of transactional integrity, and disconnection from main database. | Migrate HITL approval requests and patient preferences/memories into relational database tables with proper foreign keys and timestamps. |
| **HIGH** | `Day5/src/api_server.py` | **Database Health Check Failure:** `session.execute("SELECT 1")` raises an exception in SQLAlchemy 2.0 without `text()`, causing health checks to always return `"database": "DEGRADED"`. | False negative on database health; monitoring systems report database degradation even when SQLite/PostgreSQL is healthy. | Wrap raw SQL in `sqlalchemy.text("SELECT 1")` and handle engine health checks cleanly. |
| **HIGH** | `Day2/src/db_models.py` | **Missing Core Healthcare Entities:** Missing models for `DoctorSchedule` (working hours/leaves), `Visit`, `ConversationThread`, `ConversationMessage`, `PatientPreference`, `DoctorApprovalRequest`, `Notification`, and `AuditEvent`. | Forces application modules to use ad-hoc JSON or in-memory arrays for critical clinical processes. | Expand SQLAlchemy models to include all required relational tables with proper foreign keys, indexes, and constraints. |
| **HIGH** | `Day5/src/patient_web_app.py` | **Hardcoded Demo Patient Identities in UI:** Streamlit radio buttons force selection of `"Ahmed Raza - PT_0002"`, `"Shoaib Bhatti - PT_0005"`, or `"Ali Khan - PT_0001"`. | Real users cannot authenticate, register, or use the clinic assistant under their own identity. | Add proper registration/login form and dynamic session management in Streamlit. |
| **HIGH** | Root Repository | **Missing Dependency Manifest:** No `requirements.txt` exists in root. CI pipeline (`.github/workflows/ci.yml`) specifies `pip install -r requirements.txt`, which will fail on fresh checkout. | CI/CD build fails; local setup is not reproducible without hunting across files. | Create a comprehensive, pinned `requirements.txt` in root. |
| **MEDIUM** | `Day4/src/supervisor_graph.py` | **Pseudo-Parallel LangGraph Branching:** Comments describe parallel execution of `records_node` and `triage_node`, but edges are actually sequential: `records_node -> triage_node -> clinical_summary_node`. | Unnecessary latency on independent operations (EHR chart fetching and symptom triage). | Use LangGraph fan-out / fan-in branching or async parallel tasks to run both nodes concurrently before joining into the summary node. |
| **MEDIUM** | `Day5/src/api_server.py` | **Permissive CORS Configuration:** `allow_origins=["*"]` allows any web origin to interact with the API. | Potential cross-site request forgery or unauthorized cross-origin embedding. | Restrict CORS origins via environment variable (`ALLOWED_ORIGINS`). |
| **MEDIUM** | `Day3/src/llm_client.py` | **Fixed Fallback Model String:** Client defaults to `qwen/qwen3.8-27b` without configurable environment overrides for model name or provider. | Hardcoded model string may break if Groq deprecates or renames the endpoint. | Read LLM model name and provider settings from environment variables (`LLM_MODEL`, `LLM_PROVIDER`). |
| **MEDIUM** | `Day5/src/patient_web_app.py`, `Day4/src/doctor_dashboard_app.py` | **In-Process Backend Coupling:** Streamlit apps instantiate backend classes (`ClinicSupervisorOrchestrator()`, `HITLManager()`) in-process rather than calling the FastAPI REST endpoints. | Bypasses API authentication, rate limiting, and centralized middleware; cannot be deployed as decoupled microservices. | Wire Streamlit clients to communicate with the FastAPI backend via HTTP REST / WebSocket endpoints. |
| **LOW** | Repository Root | **Lack of Unified Pytest Suite:** The only tests are custom runner scripts (`run_day1.py` through `run_day5.py`); no standard `pytest` suite tests edge cases A through L. | Difficult to run automated regression testing in standard Python CI/CD environments. | Create a structured `tests/` directory with comprehensive `pytest` test cases covering Tests A through L. |

---

## 3. Component-by-Component Assessment

### 3.1 Application Entry Points & Startup Architecture
- **FastAPI Gateway (`week9/Day5/src/api_server.py`):**
  - Exposes `/health`, `/api/v1/clinic/branches`, `/api/v1/clinic/doctors`, `/api/v1/chat`, `/api/v1/triage`, `/api/v1/hitl/queue`, `/api/v1/hitl/action`, and `/api/v1/telemetry`.
  - **Strengths:** Clean Pydantic schemas, detailed routing, and functional integration with singletons.
  - **Defects:** Missing auth endpoints (register, login), missing appointment management endpoints (reschedule, cancel, slot search), permissive CORS (`["*"]`), and SQLAlchemy 2.0 syntax bug in `/health`.
- **Streamlit Patient Web App (`week9/Day5/src/patient_web_app.py`):**
  - Provides a conversational chat UI with UrduLish prompts.
  - **Defects:** Hardcoded patient identities in sidebar radio buttons; runs `ClinicSupervisorOrchestrator` in-process rather than calling FastAPI REST API.
- **Streamlit Doctor Dashboard (`week9/Day4/src/doctor_dashboard_app.py`):**
  - Provides pending approval queue, decision audit trail, and longitudinal memory viewer.
  - **Defects:** Directly reads/writes flat JSON files via `HITLManager` and `MemoryStore` instead of calling backend REST endpoints.
- **Master Runners (`run_day1.py` - `run_day5.py`):**
  - Standalone validation scripts that demonstrate end-to-end functionality. They work as intended, but need to be complemented by standard `pytest` suites.

### 3.2 Database Models & Schema Gaps
- **Current Models (`week9/Day2/src/db_models.py`):**
  - `ClinicBranchModel`, `PractitionerModel`, `PatientModel`, `AllergyIntoleranceModel`, `ConditionModel`, `MedicationRequestModel`, `AppointmentModel`, `ObservationModel`.
- **Database Engine Support:**
  - `get_db_engine()` supports SQLite (`clinic_fhir.db`) with PostgreSQL fallback via `DATABASE_URL`.
- **Missing Required Tables (per Phase 3 specification):**
  1. `DoctorScheduleModel`: Doctor shifts, working hours, break times, and approved leaves.
  2. `VisitModel`: Completed clinic visit encounter records.
  3. `ConversationThreadModel` & `ConversationMessageModel`: Persistent multi-turn chat history.
  4. `PatientPreferenceModel`: Patient preferred branch, preferred doctor, preferred language, and communication preferences.
  5. `DoctorApprovalRequestModel`: Persistent HITL review items with clinical context and doctor actions.
  6. `NotificationModel`: Outbound emails, SMS, and WhatsApp messages with delivery status, timestamps, and provider receipts.
  7. `AuditEventModel`: Persistent cryptographic SHA-256 chained audit logs.
  8. `UserModel`: Secure authentication credentials (hashed passwords, roles: `PATIENT`, `DOCTOR`, `ADMIN`).

### 3.3 Security, Authentication & Record Isolation
- **Current State:**
  - PII redaction engine (`pii_redactor.py`) correctly masks Pakistani CNICs, phone numbers, and addresses.
  - However, **API endpoints have zero authentication**.
  - A user can supply any `patient_id` (e.g., `PT_0002`, `PT_0005`) in `/api/v1/chat` or to MCP tools and immediately access another person's medical chart, allergies, conditions, and appointments.
- **Remediation Required:**
  - Implement password hashing (bcrypt) and JWT access tokens.
  - Implement middleware/dependency injection in FastAPI to extract authenticated user identity.
  - Enforce record-level authorization: Patients may only read/write their own records; doctors may access records only in clinical context.

### 3.4 Short-Term & Long-Term Memory
- **Short-Term Memory:**
  - Currently managed via LangGraph `MemorySaver()`, which is an in-memory dictionary. On application restart, active threads and dialogue buffers are lost.
  - **Remediation:** Store conversation threads and messages in database tables and integrate with durable LangGraph checkpointers.
- **Long-Term Patient Memory:**
  - Currently managed by `MemoryStore` in `patient_memory.py`, which saves to `data/patient_long_term_memory.json`.
  - Seeded profiles (`PT_0001`, `PT_0002`, `PT_0005`) correctly remember preferred doctor and branch.
  - **Remediation:** Migrate JSON storage to the `patient_preferences` and `visits` database tables.

### 3.5 Supervisor & Multi-Agent Orchestration
- **LangGraph Graph (`week9/Day4/src/supervisor_graph.py`):**
  - Connects `supervisor_node`, `intake_node`, `records_node`, `triage_node`, `clinical_summary_node`, `scheduling_node`, `hitl_gate_node`, `doctor_review_node`, `prescription_and_followup_node`, and `outbound_dispatch_node`.
  - **Working Features to Preserve:**
    - Clean state passing using `OrchestratorState`.
    - Telemetry tracking for transition durations and token costs.
    - Deterministic emergency short-circuit directly to `outbound_dispatch_node`.
  - **Defects to Fix:**
    - HITL gate fallthrough (pending approvals do not block outbound dispatch).
    - Sequential execution between `records_node` and `triage_node` instead of true parallel execution.

### 3.6 Doctor Appointment Management & Concurrency
- **Scheduling Agent (`week9/Day3/src/scheduling_agent.py`):**
  - **Working Features to Preserve:**
    - Symptom-to-specialty mapping.
    - Doctor filtering by gender, language, branch, fee, and experience.
    - Past-date rejection.
    - Google Calendar RFC 5545 JSON event construction.
    - Respectful UrduLish confirmation messages.
  - **Defects to Fix:**
    - Concurrency vulnerability: Lacks database row locks or unique constraints on `(practitioner_id, slot_datetime, status)`.
    - Rescheduling bug: `appt.status = "rescheduled"` marks the slot in a state that availability queries ignore, opening the slot to duplicate bookings.

### 3.7 Email Delivery & Persistent Reminders
- **Notifications Server (`week9/Day2/src/mcp_servers/notifications_server.py`):**
  - Contains simulated methods returning dummy IDs (`EML_...`, `WA_MSG_...`).
  - **Remediation:** Implement genuine SMTP email delivery with HTML templates for appointment confirmations, rescheduling, cancellations, and reminders. Add support for development test mode (mocking or directing to a test email address).
- **Scheduled Reminders (`week9/Day4/src/channel_connector.py`):**
  - Stores reminders in an in-memory list `self.queue = []`.
  - **Remediation:** Persist reminder jobs in the database with scheduled execution timestamps. Implement a background worker that checks and dispatches due reminders.

### 3.8 Medical Safety & Emergency Escalation
- **Triage Engine (`week9/Day1/src/triage_engine.py`):**
  - Pre-LLM deterministic regex matching for cardiovascular, respiratory, stroke (FAST), bleeding, pediatric danger, and suicide/self-harm.
  - Neonatal fever (< 3 months, temp >= 100.4°F) emergency trigger.
  - Standard UrduLish emergency instructions ("Rescue 1122 par call karein").
  - **Status:** **EXCELLENT & WORKING.** Must be strictly preserved.

### 3.9 Human-in-the-Loop (HITL) Doctor Approval
- **HITL Manager (`week9/Day4/src/hitl_manager.py`):**
  - Triggers review for lab result explanations, prescription messages, and low-confidence triage (< 0.85).
  - Supports Approve, Edit & Approve, and Reject.
  - **Defects to Fix:** File-based JSON persistence must be moved to database tables, and graph flow must genuinely block patient dispatch until approved.

### 3.10 Prescription Safety Engine
- **Prescription Safety Engine (`week9/Day2/src/prescription_safety_engine.py`):**
  - Rule-based verification of allergy clashes, drug interactions, maximum daily doses, and population contraindications.
  - **Status:** **EXCELLENT & WORKING.** Must be strictly preserved and connected to the database models.

### 3.11 RAG Pipeline & MCP Servers
- **ChromaDB Knowledge RAG (`week9/Day2/src/rag_pipeline.py`):**
  - Working vector retrieval over clinic FAQs, lab instructions, and patient leaflets with mandatory source citations.
  - **Status:** **WORKING.** Needs safe persistence path and configuration.
- **FastMCP Servers (`week9/Day2/src/mcp_servers/`):**
  - 4 servers: `patient-records-server`, `scheduling-server`, `drug-database-server`, `notifications-server`.
  - **Defects to Fix:** In-memory notification simulation, lack of authorization checks on tool invocations.

---

## 4. Preservation vs. Modification Inventory

### A. Working Features to Preserve
- Deterministic red-flag triage rules and UrduLish emergency messaging (`Day1/triage_engine.py`).
- Pakistani PII redactor and reversible vaulting (`Day1/pii_redactor.py`).
- 8 Agent role cards and operational constraints (`Day1/agent_registry.py`).
- FHIR database schemas for patients, doctors, appointments, and observations (`Day2/db_models.py`).
- ChromaDB medical knowledge base and RAG citation pipeline (`Day2/rag_pipeline.py`).
- Deterministic prescription safety engine and Pakistani drug database (`Day2/prescription_safety_engine.py`, `drug_database_server.py`).
- Conversational intake state extraction and single-question logic (`Day3/intake_agent.py`).
- Clinical summary pre-visit SOAP generator (`Day3/clinical_summary_agent.py`).
- Google Calendar event builder (`Day3/scheduling_agent.py`).
- Core LangGraph state machine structure and node transition tracking (`Day4/supervisor_graph.py`).
- Telemetry tracker and cost/latency metrics (`Day4/observability.py`).

### B. Existing Features Needing Bug Fixes
- `Day5/api_server.py`: Fix SQLAlchemy 2.0 health check query `text("SELECT 1")`.
- `Day3/scheduling_agent.py`: Fix `reschedule_appointment` status and slot overwrite bug.
- `Day3/scheduling_agent.py`: Add database concurrency protection / unique constraint.
- `Day4/supervisor_graph.py`: Fix HITL interrupt fallthrough so unapproved messages are not sent.
- `Day4/supervisor_graph.py`: Fix LangGraph parallel branching for `records_node` and `triage_node`.
- `Day5/patient_web_app.py`: Fix hardcoded patient selection and import path issues.

### C. Missing Features Needing Implementation
- Root `requirements.txt` with pinned, compatible versions.
- Unified configuration system (`config.py`) using Pydantic Settings and `.env`.
- Real SMTP email notification service with HTML templates.
- Persistent database-backed reminder worker surviving application restarts.
- Missing database models: `DoctorSchedule`, `Visit`, `ConversationThread`, `ConversationMessage`, `PatientPreference`, `DoctorApprovalRequest`, `Notification`, `AuditEvent`, `User`.
- User authentication (JWT tokens, password hashing) and role-based record authorization.
- REST endpoints for patient registration, login, appointment rescheduling, and appointment cancellation.
- Streamlit connection to FastAPI backend via HTTP REST rather than in-process imports.
- Comprehensive `pytest` automated test suite covering Tests A through L.

### D. Required Database Migrations & Configuration Updates
- Add unique constraint on appointments table: `UNIQUE(practitioner_id, slot_datetime, status)`.
- Create new tables for `doctor_schedules`, `visits`, `conversation_threads`, `conversation_messages`, `patient_preferences`, `doctor_approvals`, `notifications`, `audit_events`, `users`.
- Add environment variables for SMTP server, clinic timezone, JWT secret, and allowed CORS origins in `.env.example`.
