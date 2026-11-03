# City Care Clinics — REST API Reference Guide

**Base URL:** `http://localhost:8000`  
**OpenAPI Swagger UI:** `http://localhost:8000/docs`  
**API Version:** `v1`  
**Authentication Scheme:** `Bearer <JWT_TOKEN>` (`Authorization` header)  

---

## 1. Authentication & User Management

### 1.1 Register New Patient Account
- **Endpoint:** `POST /api/v1/auth/register`
- **Access:** Public
- **Description:** Registers a new patient with credentials and links to or creates a FHIR Patient record.

#### Request Body
```json
{
  "username": "ali.khan",
  "password": "StrongPassword123!",
  "role": "PATIENT",
  "patient_id": "PAT_001",
  "email": "ali.khan@example.com",
  "full_name": "Ali Khan",
  "phone": "0300-1234567"
}
```

#### Response (`HTTP 200 OK`)
```json
{
  "status": "success",
  "user_id": "usr_78a1bc",
  "username": "ali.khan",
  "role": "PATIENT",
  "patient_id": "PAT_001"
}
```

---

### 1.2 User Login & Token Issuance
- **Endpoint:** `POST /api/v1/auth/login`
- **Access:** Public
- **Description:** Verifies credentials using bcrypt and issues a signed JWT token valid for 480 minutes.

#### Request Body
```json
{
  "username": "doctor.tariq",
  "password": "DoctorSecure2026!"
}
```

#### Response (`HTTP 200 OK`)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "DOCTOR",
  "patient_id": null,
  "practitioner_id": "DOC_001",
  "expires_in_minutes": 480
}
```

---

### 1.3 Get Current Authenticated Profile
- **Endpoint:** `GET /api/v1/auth/me`
- **Access:** Authenticated (`Bearer <token>`)
- **Description:** Returns the active token claims and profile details.

#### Response (`HTTP 200 OK`)
```json
{
  "username": "doctor.tariq",
  "role": "DOCTOR",
  "patient_id": null,
  "email": "dr.tariq@citycare.com"
}
```

---

## 2. Health & Telemetry

### 2.1 System Pre-Flight Health Check
- **Endpoint:** `GET /health`
- **Access:** Public
- **Description:** Evaluates database connectivity via `SELECT 1`, LLM provider status, ChromaDB vector store, and SMTP configuration.

#### Response (`HTTP 200 OK`)
```json
{
  "status": "HEALTHY",
  "timestamp": "2026-10-12T12:00:00Z",
  "components": {
    "database": "HEALTHY",
    "llm_provider": "ONLINE",
    "vector_store": "READY",
    "smtp_service": "CONFIGURED"
  },
  "environment": "production"
}
```

---

## 3. Patient Records & Clinical Chart

### 3.1 Get Authenticated Patient Profile
- **Endpoint:** `GET /api/v1/patient/me`
- **Access:** Patient Role
- **Description:** Retrieves the caller's complete FHIR demographic profile, allergies, and conditions.

---

### 3.2 Get Patient Chart by ID
- **Endpoint:** `GET /api/v1/patient/{id}`
- **Access:** Patient (Self only) / Doctor / Admin
- **Description:** Returns full clinical record for patient `{id}`. Enforces strict multi-tenant isolation.
- **Security Guard:** If a patient attempts to request another patient's ID, returns `HTTP 403 Forbidden` with `"detail": "Cross-patient access forbidden"`.

#### Response (`HTTP 200 OK`)
```json
{
  "id": "PAT_001",
  "mrn": "MRN-2026-0001",
  "name": "Muhammad Usman",
  "phone": "0300-8451234",
  "email": "usman.m@example.com",
  "dob": "1984-05-12",
  "gender": "male",
  "allergies": [
    {
      "substance": "Penicillin",
      "reaction": "Anaphylaxis / Urticaria",
      "severity": "high"
    }
  ],
  "conditions": [
    {
      "code": "I10",
      "display": "Essential (primary) hypertension",
      "clinical_status": "active"
    }
  ]
}
```

---

## 4. Scheduling & Appointment Lifecycle

### 4.1 Search Available Slots
- **Endpoint:** `GET /api/v1/schedule/slots`
- **Access:** Public / Authenticated
- **Query Parameters:**
  - `practitioner_id` (optional, e.g. `DOC_001`)
  - `specialty` (optional, e.g. `General Medicine`)
  - `branch_id` (optional, e.g. `BR_LHR_GULBERG`)
  - `target_date` (optional, format `YYYY-MM-DD`)

#### Response (`HTTP 200 OK`)
```json
{
  "total_slots": 8,
  "slots": [
    {
      "practitioner_id": "DOC_001",
      "doctor_name": "Dr. Tariq Mahmood",
      "specialty": "General Medicine",
      "branch_id": "BR_LHR_GULBERG",
      "slot_datetime": "2026-10-13T10:00:00",
      "status": "available",
      "consultation_fee": 2500
    }
  ]
}
```

---

### 4.2 Book Appointment
- **Endpoint:** `POST /api/v1/schedule/book`
- **Access:** Authenticated (Patient or Staff)
- **Description:** Books an available slot with transactional anti-double-booking locks and automatically enqueues confirmation email and reminders.

#### Request Body
```json
{
  "patient_id": "PAT_001",
  "practitioner_id": "DOC_001",
  "slot_datetime": "2026-10-13T10:00:00",
  "reason": "Routine hypertension review"
}
```

#### Response (`HTTP 200 OK`)
```json
{
  "status": "success",
  "appointment_id": "APT_98231",
  "token_number": "TOKEN-001",
  "doctor_name": "Dr. Tariq Mahmood",
  "branch": "City Care Clinics — Gulberg Branch",
  "slot_datetime": "2026-10-13T10:00:00",
  "notification_status": "QUEUED"
}
```

#### Collision Response (`HTTP 409 Conflict`)
```json
{
  "status": "error",
  "error_code": "SLOT_CONFLICT",
  "message": "The requested appointment slot is already booked by another patient."
}
```

---

### 4.3 Reschedule Appointment
- **Endpoint:** `POST /api/v1/schedule/reschedule`
- **Access:** Authenticated (Patient or Staff)
- **Description:** Moves an existing booking to a new available slot, frees the old slot, and notifies the patient.

#### Request Body
```json
{
  "appointment_id": "APT_98231",
  "new_slot_datetime": "2026-10-14T11:00:00"
}
```

#### Response (`HTTP 200 OK`)
```json
{
  "status": "success",
  "appointment_id": "APT_98231",
  "old_slot": "2026-10-13T10:00:00",
  "new_slot": "2026-10-14T11:00:00",
  "message": "Appointment rescheduled successfully. Prior slot has been freed."
}
```

---

### 4.4 Cancel Appointment
- **Endpoint:** `POST /api/v1/schedule/cancel`
- **Access:** Authenticated (Patient or Staff)
- **Description:** Cancels an appointment, returns slot to available status, and invalidates pending reminders.

#### Request Body
```json
{
  "appointment_id": "APT_98231",
  "cancellation_reason": "Patient travelling"
}
```

#### Response (`HTTP 200 OK`)
```json
{
  "status": "success",
  "appointment_id": "APT_98231",
  "status": "cancelled",
  "reminders_invalidated": 2
}
```

---

## 5. Conversational Multi-Agent Interaction

### 5.1 Chat with Multi-Agent Orchestrator
- **Endpoint:** `POST /api/v1/chat`
- **Access:** Authenticated or Guest Session
- **Description:** Executes a turn in the LangGraph state machine. Red-flags trigger immediate emergency short-circuit.

#### Request Body
```json
{
  "message": "Doctor sahab, 2 din se sar mein shaded dard hai aur ulti bhi aa rahi hai.",
  "patient_id": "PAT_001",
  "thread_id": "thread_custom_102"
}
```

#### Response (`HTTP 200 OK`)
```json
{
  "thread_id": "thread_custom_102",
  "triage_level": "URGENT",
  "response": "Aap ko severe headache aur vomiting hai. Yeh signs doctor se fori checkup require karte hain. Hum aap ko Gulberg branch mein General Physician ke saath book kar saktay hain.",
  "suggested_actions": ["Book Urgent Appointment", "Clinic Directions"],
  "requires_doctor_approval": false
}
```

---

## 6. Doctor Oversight & HITL Approvals

### 6.1 Get Pending Approval Queue
- **Endpoint:** `GET /api/v1/hitl/queue`
- **Access:** Doctor / Admin Role
- **Description:** Retrieves pending approval drafts requiring clinical sign-off.

#### Response (`HTTP 200 OK`)
```json
{
  "pending_count": 1,
  "queue": [
    {
      "id": "HITL_REQ_001",
      "patient_id": "PAT_001",
      "draft_text": "HbA1c level is 8.2% which indicates sub-optimal glycemic control.",
      "clinical_context": "Lab Report Analysis - Diabetic review",
      "status": "PENDING",
      "created_at": "2026-10-12T11:45:00Z"
    }
  ]
}
```

---

### 6.2 Process Doctor Action
- **Endpoint:** `POST /api/v1/hitl/action`
- **Access:** Doctor / Admin Role
- **Description:** Performs doctor sign-off: `APPROVE`, `EDIT_AND_APPROVE`, or `REJECT`.

#### Request Body
```json
{
  "request_id": "HITL_REQ_001",
  "action": "EDIT_AND_APPROVE",
  "doctor_notes": "Added advice for fasting glucose test before next visit",
  "updated_text": "HbA1c level is 8.2% which indicates sub-optimal control. Please schedule a fasting blood glucose test before your visit with Dr. Tariq."
}
```

#### Response (`HTTP 200 OK`)
```json
{
  "status": "success",
  "request_id": "HITL_REQ_001",
  "action_performed": "EDIT_AND_APPROVE",
  "dispatched_to_patient": true
}
```

---

## 7. Notifications & Background Reminders

### 7.1 Trigger Persistent Reminder Worker
- **Endpoint:** `POST /api/v1/notifications/reminders/process`
- **Access:** Admin / Scheduled Cron
- **Description:** Processes all pending reminders due for dispatch. Automatically skips cancelled appointments.

#### Response (`HTTP 200 OK`)
```json
{
  "status": "success",
  "processed": 5,
  "dispatched": 4,
  "skipped_cancelled": 1,
  "errors": 0
}
```

---

## 8. Lab Report Analysis

### 8.1 Analyze Lab Report Document
- **Endpoint:** `POST /api/v1/lab/analyze`
- **Access:** Doctor / Staff
- **Description:** Extracts structured FHIR observations, flags out-of-range biomarkers, and creates a draft requiring doctor approval.

#### Request Body
```json
{
  "patient_id": "PAT_001",
  "report_text": "CBC Test: Hemoglobin 9.2 g/dL (Reference 13.0-17.0), WBC 11,500 /uL"
}
```

#### Response (`HTTP 200 OK`)
```json
{
  "patient_id": "PAT_001",
  "abnormal_findings_count": 2,
  "abnormal_observations": [
    {
      "test_name": "Hemoglobin",
      "value": 9.2,
      "unit": "g/dL",
      "reference_range": "13.0 - 17.0",
      "flag": "LOW"
    }
  ],
  "hitl_status": "ENQUEUED_FOR_DOCTOR_APPROVAL"
}
```
