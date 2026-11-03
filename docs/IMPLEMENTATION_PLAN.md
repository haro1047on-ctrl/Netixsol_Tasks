# City Care Clinics — Master Implementation Plan

**Target System:** City Care Clinics Multi-Agent Healthcare AI Assistant  
**Execution Paradigm:** Non-Destructive, Incremental, Test-Driven Repair and Extension  
**Date:** October 12, 2026  
**Status:** **100% Complete — All 16 Phases Implemented & Verified (14/14 Pytest Green)**  

---

## 1. Roadmap Overview

```mermaid
gantt
    title City Care Clinics Implementation Roadmap
    dateFormat  YYYY-MM-DD
    section Phase 1: Foundation & Audit
    Audit & Defect Discovery                  :done, p1, 2026-10-09, 1d
    section Phase 2: Configuration & Startup
    Config System, Requirements & Health Checks:done, p2, 2026-10-10, 1d
    section Phase 3: Database & Records
    Expanded FHIR Models, DB Migrations & Auth :done, p3, 2026-10-11, 2d
    section Phase 4: Persistent Memory
    Thread DB Storage, LangGraph Checkpointing :done, p4, 2026-10-13, 1d
    section Phase 5: Multi-Agent Orchestration
    Supervisor Repair, Parallel Branching, HITL:done, p5, 2026-10-14, 2d
    section Phase 6: Appointment Engine
    Concurrency Locks, Reschedule Bugfix, Slot Engine:done, p6, 2026-10-16, 2d
    section Phase 7: Real Email & Reminders
    SMTP Provider, Persistent Reminder Worker  :done, p7, 2026-10-18, 2d
    section Phase 8: Frontend & Security
    REST Streamlit Decoupling, JWT RBAC        :done, p8, 2026-10-20, 2d
    section Phase 9: QA & Documentation
    Pytest Suite (A-L), Docker & Final Docs    :done, p9, 2026-10-22, 2d
```

---

## 2. Phase-by-Phase Technical Specifications

### Phase 1: Codebase Audit & Foundation Assessment
- **Status:** Complete. Documented in [docs/CODEBASE_AUDIT.md](file:///d:/netixsol_work/docs/CODEBASE_AUDIT.md).
- **Deliverables:** Architectural inventory, audit matrix, and defect identification.
- **Rule:** Executed strictly in AUDIT-ONLY MODE with zero modifications to existing source code.

---

### Phase 2: Configuration, Environment & Application Startup
- **Objectives:**
  1. Create a root `requirements.txt` with pinned, tested dependencies matching Python 3.13 on Windows.
  2. Implement a robust configuration system in `src/config.py` using `pydantic-settings`.
  3. Support all required variables:
     - `APP_ENV` (`development`, `staging`, `production`)
     - `DATABASE_URL` (defaulting to SQLite `clinic_fhir.db`, supporting PostgreSQL)
     - `LLM_PROVIDER` (`groq`, fallback offline)
     - `GROQ_API_KEY`
     - `EMAIL_PROVIDER` (`smtp`, `sendgrid`, `test_mode`)
     - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`
     - `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
     - `ALLOWED_ORIGINS`
     - `CLINIC_TIMEZONE` (default `Asia/Karachi`)
     - `LOG_LEVEL`
  4. Create a clean `.env.example` in root with non-sensitive placeholders.
  5. Fix SQLAlchemy 2.0 query in `/health` endpoint (`text("SELECT 1")`) in `api_server.py`.
  6. Return comprehensive component status in `/health` (Database, LLM Provider, Vector DB, SMTP status).
- **Verification Gate:**
  - Execute `GET /health` and verify HTTP 200 with `"database": "HEALTHY"`.
  - Validate that missing required environment variables fail early with helpful error messages.

---

### Phase 3: Database Models & Patient Records
- **Objectives:**
  1. Inspect existing models in `week9/Day2/src/db_models.py` and extend them in-place:
     - `DoctorScheduleModel`: Shift timings, break intervals, day of week, active leaves.
     - `VisitModel`: Formal clinical encounters linking appointment, diagnosis, and vitals.
     - `ConversationThreadModel` & `ConversationMessageModel`: Persistent conversation transcripts.
     - `PatientPreferenceModel`: Preferred doctor, branch, language, and communication channel.
     - `DoctorApprovalRequestModel`: Persistent HITL requests with clinical context, doctor notes, and actions.
     - `NotificationModel`: Outbound emails, SMS, and WhatsApp messages with status (`PENDING`, `PROCESSING`, `SENT`, `FAILED`), retry count, and delivery receipt.
     - `AuditEventModel`: Cryptographic chained audit logs (`SHA-256`) stored directly in SQLite/PostgreSQL.
     - `UserModel`: Authentication credentials with bcrypt hashed passwords and roles (`PATIENT`, `DOCTOR`, `ADMIN`).
  2. Add database unique constraint: `UNIQUE(practitioner_id, slot_datetime, status)` to prevent double booking.
  3. Ensure database initialization is non-destructive (do not wipe existing `clinic_fhir.db` tables).
  4. Implement patient registration service, secure profile retrieval, and patient preference management.
- **Verification Gate:**
  - Verify tables are created without errors on SQLite and PostgreSQL.
  - Test synthetic patient registration and verified profile retrieval.

---

### Phase 4: Real Short-Term and Long-Term Memory
- **Objectives:**
  1. **Short-Term Memory:**
     - Replace volatile `MemorySaver()` with durable thread storage in `conversation_threads` and `conversation_messages` tables.
     - Enable full session restoration across server restarts.
     - Guarantee isolation between different user threads.
  2. **Long-Term Memory:**
     - Migrate `data/patient_long_term_memory.json` into `patient_preferences` and `visits` database tables.
     - Store provenance and timestamps for preferences (e.g., preferred doctor, branch, language).
     - Returning patient flow: When an authenticated patient returns ("I want to book an appointment again"), retrieve prior doctor, branch, and conditions without asking repetitive questions.
  3. Ensure sensitive clinical data is never leaked in greeting messages.
- **Verification Gate:**
  - Session restart test: Start a chat session, record 3 turns, restart the backend process, resume the thread, and verify full context preservation.

---

### Phase 5: Supervisor & Multi-Agent Orchestration
- **Objectives:**
  1. Repair `ClinicSupervisorOrchestrator` in `week9/Day4/src/supervisor_graph.py`:
     - Maintain validated shared state (`OrchestratorState`).
     - True parallel branching: Execute `records_node` and `triage_node` concurrently before joining at `clinical_summary_node`.
     - Deterministic emergency routing: Emergency red-flags bypass normal scheduling and immediately invoke `outbound_dispatch_node` with 1122 escalation instructions.
  2. Implement bounded retries and timeouts on LLM calls with safe fallback to offline/verified responses.
  3. Log all graph node transitions with timestamps, agent IDs, and execution latency.
- **Verification Gate:**
  - Verify state transitions through emergency, urgent, and routine clinical paths.
  - Confirm parallel execution timing and state synthesis.

---

### Phase 6: Real Doctor Appointment Management & Concurrency
- **Objectives:**
  1. Repair `SchedulingAgent` in `week9/Day3/src/scheduling_agent.py`:
     - Calculate availability strictly against `DoctorScheduleModel` and existing active appointments.
     - Prevent booking in the past relative to clinic timezone (`Asia/Karachi`).
     - Fix the rescheduling bug: Ensure rescheduled slots remain marked as `"booked"` while old slots are cleanly released.
  2. **Concurrency & Anti-Double-Booking Protection:**
     - Wrap slot validation and insertion in a transactional block.
     - Catch database unique constraint violations and return `SLOT_CONFLICT` cleanly.
  3. Provide full appointment lifecycle routes in FastAPI:
     - `GET /api/v1/schedule/slots` (Check availability)
     - `POST /api/v1/schedule/book` (Book new appointment)
     - `POST /api/v1/schedule/reschedule` (Move appointment to new slot)
     - `POST /api/v1/schedule/cancel` (Cancel appointment)
     - `GET /api/v1/schedule/appointments` (List user's appointments)
- **Verification Gate:**
  - Concurrent booking test: Two simultaneous requests for the exact same doctor and slot; verify exactly 1 succeeds and 1 receives `SLOT_CONFLICT`.
  - Reschedule test: Reschedule an appointment, verify the old slot becomes available, and verify the new slot is reserved.

---

### Phase 7: Real Email Delivery
- **Objectives:**
  1. Replace simulated email logic in `notifications_server.py` with a real SMTP service (`src/services/email_service.py`):
     - Connect to configured SMTP server (Gmail, SendGrid, Amazon SES, or local test server).
     - Support HTML and plain-text templates for:
       - Appointment Confirmation (Doctor, specialty, branch, date/time, token number).
       - Appointment Rescheduling (Old date, new date, instructions).
       - Appointment Cancellation (Confirmation of cancellation).
       - Upcoming Appointment Reminders.
       - Doctor-approved Clinical Summaries.
  2. Track all outbound emails in `NotificationModel` with states: `PENDING`, `SENT`, `FAILED`.
  3. Record provider errors, timeouts, and delivery receipts.
  4. Ensure appointment booking persists even if email dispatch fails (separate failure reporting).
  5. Implement development test recipient mode (`TEST_EMAIL_RECIPIENT`).
- **Verification Gate:**
  - Send real test email via configured SMTP (or local SMTP debug server) and verify receipt and database status.
  - Simulate SMTP failure (invalid credentials/timeout) and verify appointment remains booked with email marked as `FAILED`.

---

### Phase 8: Persistent Appointment Reminders
- **Objectives:**
  1. Replace in-memory `ScheduledReminderQueue` with database-backed reminder worker (`src/services/reminder_service.py`):
     - Schedule 48-hour post-visit adherence check and 7-day lab follow-up reminders.
     - Persist reminder jobs in `NotificationModel` with `scheduled_for` timestamp.
  2. Background Worker:
     - Periodically check for due reminders.
     - Validate appointment status before sending (skip if appointment was cancelled).
     - Update status to `SENT` or `FAILED`.
     - Prevent duplicate message dispatch.
  3. Survives process restarts: On backend startup, resume pending due reminders.
- **Verification Gate:**
  - Queue a reminder, restart the server, run the worker, and verify the reminder is dispatched.
  - Cancel an appointment and verify the scheduled reminder is safely invalidated.

---

### Phase 9: Medical Safety & Deterministic Emergency Escalation
- **Objectives:**
  1. Preserve and solidify `TriageEngine` in `week9/Day1/src/triage_engine.py`:
     - 100% deterministic red-flag detection running prior to any LLM execution.
     - Comprehensive UrduLish and English keywords for:
       - Acute chest pain / Myocardial Infarction
       - Severe respiratory distress
       - Acute stroke (FAST positive)
       - Severe hemorrhage and head trauma
       - Pediatric danger signs & neonatal fever (< 3 months, >= 100.4°F)
       - Suicidal ideation & self-harm
       - Toxic ingestion / overdose
  2. Invariant: LLM output or confidence score can NEVER override or suppress an emergency trigger.
  3. Enforce non-diagnostic boundary: The assistant collects information and guides routing, but never declares medical diagnoses or prescribes drugs autonomously.
- **Verification Gate:**
  - Run 50 emergency benchmark scenarios in UrduLish and English; verify 100% emergency recall rate.

---

### Phase 10: Human-in-the-Loop (HITL) Doctor Approval Workflow
- **Objectives:**
  1. Fix HITL gate in `supervisor_graph.py`:
     - When an interrupt condition is met (lab interpretation, prescription instruction, low-confidence triage < 0.85), **halt execution and do not dispatch the draft to the patient**.
     - Save pending request in `DoctorApprovalRequestModel`.
  2. Doctor Dashboard Actions:
     - `APPROVE`: Dispatches the original draft.
     - `EDIT & APPROVE`: Updates draft with physician's text and dispatches.
     - `REJECT`: Blocks message and provides clinical referral instructions.
  3. Persist review items across application restarts.
- **Verification Gate:**
  - Trigger a lab interpretation draft; verify patient does not receive the unapproved message.
  - Execute doctor edit and approval; verify the edited text is dispatched to the patient.

---

### Phase 11: Prescription Safety Engine
- **Objectives:**
  1. Preserve and extend `PrescriptionSafetyEngine` in `week9/Day2/src/prescription_safety_engine.py`:
     - Rule-based checks for:
       - Patient allergy conflicts (e.g., Penicillin vs. Augmentin, Sulfa drugs)
       - Known drug-drug interactions (e.g., Warfarin + Aspirin)
       - Duplicate therapies (same therapeutic class)
       - Maximum 24-hour daily dose ceilings (e.g., Panadol > 4000mg/day)
       - Pediatric & pregnancy contraindications
  2. If drug data is unavailable, return `"unable to verify"` rather than claiming safety.
  3. Route all warnings to clinician review; never automatically modify a prescription.
- **Verification Gate:**
  - Evaluate against benchmark cases (Allergy clash, lethal DDI, overdose, pregnancy alert) and assert 100% detection.

---

### Phase 12: RAG Pipeline & MCP Server Integration
- **Objectives:**
  1. ChromaDB Knowledge RAG (`week9/Day2/src/rag_pipeline.py`):
     - Maintain strict source citations for all clinic FAQ and medical leaflet queries.
     - Return "certified information unavailable" when evidence is insufficient (zero hallucination policy).
  2. MCP Servers (`mcp_servers/`):
     - Connect FastMCP tools to shared underlying database services rather than separate ad-hoc logic.
     - Enforce authorization checks on patient records tool.
- **Verification Gate:**
  - Execute 25-question RAG benchmark and verify >= 85% grounding rate.
  - Run MCP test suite and verify all 4 servers pass.

---

### Phase 13: Frontend & User Experience
- **Objectives:**
  1. Patient Portal (`week9/Day5/src/patient_web_app.py`):
     - Remove hardcoded patient selection radio buttons.
     - Add registration and login interface.
     - Connect to FastAPI backend via HTTP REST endpoints (`/api/v1/chat`, `/api/v1/schedule/book`).
     - Display active doctor token, branch, and booking status.
     - Support bilingual Roman Urdu (UrduLish) and English.
  2. Doctor Dashboard (`week9/Day4/src/doctor_dashboard_app.py`):
     - Connect to FastAPI backend endpoints (`/api/v1/hitl/queue`, `/api/v1/hitl/action`).
     - Display pending approvals, clinical SOAP summaries, and prescription warnings.
- **Verification Gate:**
  - Test registration, chat conversation, booking confirmation, and physician approval workflow directly in the browser.

---

### Phase 14: Security, Authentication & Role-Based Authorization
- **Objectives:**
  1. Implement JWT authentication (`src/services/auth_service.py`):
     - Password hashing with `bcrypt` / `passlib`.
     - Role-based tokens: `PATIENT`, `DOCTOR`, `ADMIN`.
  2. Enforce endpoint authorization:
     - Patients can only retrieve and modify their own records and appointments.
     - Cross-patient record snooping is rejected with HTTP 403 Forbidden.
  3. Restrict CORS origins via `ALLOWED_ORIGINS` environment variable.
  4. Ensure sensitive credentials and patient PII are not logged in plain text.
- **Verification Gate:**
  - Security test: Authenticate as Patient A; attempt to read Patient B's chart; verify HTTP 403 Forbidden.

---

### Phase 15: Comprehensive Automated Testing Suite
- **Objectives:**
  1. Create a complete `pytest` test suite under `tests/` covering Tests A through L:
     - **Test A:** New patient registration, doctor discovery, slot selection, confirmed booking, and notification.
     - **Test B:** Returning patient memory (preferences, past visits retrieved without re-asking).
     - **Test C:** Cross-patient isolation (Patient A cannot view Patient B's data).
     - **Test D:** Concurrency and double booking (simultaneous bookings for same slot; exactly 1 succeeds).
     - **Test E:** Rescheduling (slot moved, old slot freed, no collision).
     - **Test F:** Cancellation (slot freed, reminder invalidated).
     - **Test G:** Emergency escalation (100% deterministic recall in English and UrduLish).
     - **Test H:** Email provider failure handling (appointment preserved, failure logged).
     - **Test I:** Doctor approval workflow (unapproved message blocked, edited message sent).
     - **Test J:** Application restart recovery (database records, memory, approvals persist).
     - **Test K:** Provider unavailability (Groq down; safe offline fallback, emergency rules intact).
     - **Test L:** Reminder reliability (rescheduled/cancelled appointments do not trigger wrong reminders).
  2. Generate `docs/TEST_REPORT.md` documenting actual executed test results.
- **Verification Gate:**
  - Run `pytest -v tests/` and verify all tests pass without errors.

---

### Phase 16: Development Setup, Documentation & Docker
- **Objectives:**
  1. Create idempotent seed script (`src/scripts/seed_data.py`) for synthetic patients, doctors, schedules, and branches.
  2. Create or update documentation:
     - `README.md`: Prerequisites, installation, environment setup, startup commands (PowerShell), troubleshooting.
     - `docs/ARCHITECTURE.md`: LangGraph state machine, data models, and agent roles.
     - `docs/API.md`: Complete OpenAPI route documentation.
     - `docs/SECURITY.md`: Authentication, RBAC, PII redaction, and HIPAA/data policy.
     - `docs/MEDICAL_SAFETY.md`: Triage red-flags, emergency scripts, and non-diagnostic bounds.
     - `docs/MEMORY_DESIGN.md`: Short-term and long-term memory architecture.
     - `docs/EMAIL_AND_REMINDERS.md`: SMTP configuration, reminder worker, and delivery tracking.
     - `docs/TROUBLESHOOTING.md`: Common errors, port conflicts, and DB recovery.
  3. Verify Docker setup (`Dockerfile.api`, `Dockerfile.dashboard`, `docker-compose.yml`).
- **Verification Gate:**
  - Verify complete local startup and seed run from a clean terminal.

---

## 3. Implementation Order & Dependencies

```
[Phase 2: Config & Startup]
       │
       ▼
[Phase 3: Database & Patient Records]
       │
       ▼
[Phase 4: Persistent Memory]
       │
       ▼
[Phase 5: Supervisor & Multi-Agent Orchestration]
       │
       ▼
[Phase 6: Appointment Engine & Concurrency]
       │
       ▼
[Phase 7: Real Email Delivery] ──► [Phase 8: Persistent Reminders]
       │                                  │
       ▼                                  ▼
[Phase 9: Medical Safety] & [Phase 10: HITL Doctor Approvals]
       │
       ▼
[Phase 11: Prescription Safety] & [Phase 12: RAG & MCP]
       │
       ▼
[Phase 14: Security & RBAC] ──► [Phase 13: Frontend REST Integration]
       │
       ▼
[Phase 15: Automated Pytest Suite (Tests A - L)]
       │
       ▼
[Phase 16: Seed Data, Docs & Final Handover Report]
```

---

## 4. Implementation & Verification Status

**All 16 Phases are 100% Implemented, Integrated, and Verified:**
- **Automated Pytest Suite:** 14 passed / 0 failed in 11.43s ([docs/TEST_REPORT.md](file:///d:/netixsol_work/docs/TEST_REPORT.md)).
- **System Architecture & Data Models:** Fully documented in [docs/ARCHITECTURE.md](file:///d:/netixsol_work/docs/ARCHITECTURE.md).
- **REST API Reference:** Comprehensive OpenAPI endpoints in [docs/API.md](file:///d:/netixsol_work/docs/API.md).
- **Security & RBAC:** Auth, bcrypt, isolation, and audit trail in [docs/SECURITY.md](file:///d:/netixsol_work/docs/SECURITY.md).
- **Medical Safety & Triage:** 100% emergency recall and HITL policies in [docs/MEDICAL_SAFETY.md](file:///d:/netixsol_work/docs/MEDICAL_SAFETY.md).
- **Patient Memory:** Thread persistence and EHR longitudinal profiles in [docs/MEMORY_DESIGN.md](file:///d:/netixsol_work/docs/MEMORY_DESIGN.md).
- **Email & Reminders:** SMTP dispatches and invalidation guards in [docs/EMAIL_AND_REMINDERS.md](file:///d:/netixsol_work/docs/EMAIL_AND_REMINDERS.md).
- **Operations & Troubleshooting:** Diagnostic runbook in [docs/TROUBLESHOOTING.md](file:///d:/netixsol_work/docs/TROUBLESHOOTING.md).
- **Idempotent Seed Script:** Verified working with 5 branches, 30 doctors, 180 shifts, 507 patients, and 10 user accounts (`python week9/src/scripts/seed_data.py`).

