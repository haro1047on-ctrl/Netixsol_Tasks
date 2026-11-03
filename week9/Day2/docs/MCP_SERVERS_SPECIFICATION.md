# City Care Clinics — Model Context Protocol (MCP) Servers Specification
**Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare**  
**Document Version:** 1.0.0 | **Protocol:** Model Context Protocol (FastMCP / JSON-RPC 2.0)  
**Author:** Distributed Systems & MCP Infrastructure Team

---

## 1. Overview & Architectural Role of MCP

In traditional agent systems, tools are implemented as internal Python functions with direct database credentials in memory. In healthcare, this poses severe security and regulatory risks.

The **Model Context Protocol (MCP)**, open-sourced by Anthropic, enforces a standardized boundary where data sources, clinic databases, and external notification APIs run as independent, sandboxed server processes communicating via JSON-RPC 2.0.

City Care Clinics deploys **4 specialized MCP servers**:
1. **`patient-records-server`**: Secure, authenticated read access to the longitudinal FHIR database.
2. **`clinic-scheduling-server`**: Multi-branch doctor rotas, slot availability, atomic booking, and calendar transitions.
3. **`pharmacy-safety-server`**: Deterministic pharmacology database, drug-drug interaction matrix, allergy checker, and dose calculator.
4. **`notifications-server`**: Multi-channel outbound messaging engine (WhatsApp Cloud API, Email, SMS) with tamper-evident delivery receipts.

---

## 2. Server 1: `patient-records-server`

- **Endpoint / Module:** `src/mcp_servers/patient_records_server.py`
- **Underlying Data Store:** PostgreSQL / SQLite FHIR Relational Database (`clinic_fhir.db`)
- **Exposed Tools:**

| Tool Name | Parameters | Return Schema | Purpose & Safety Constraint |
| :--- | :--- | :--- | :--- |
| `get_patient_profile` | `identifier: str` | `Dict[str, Any]` | Resolves patient demographics by ID (`PT_0001`), Phone (`0300-1234567`), or CNIC. |
| `get_patient_allergies` | `patient_id: str` | `List[Dict[str, Any]]` | Returns active substance allergies, manifestations, and criticality ratings. |
| `get_patient_conditions` | `patient_id: str` | `List[Dict[str, Any]]` | Returns active chronic problems and ICD-10 codes. |
| `get_patient_medications` | `patient_id: str` | `List[Dict[str, Any]]` | Returns active prescriptions, dose, frequency, and route. |
| `get_patient_observations` | `patient_id: str`, `category: Optional[str]` | `List[Dict[str, Any]]` | Returns quantitative diagnostic lab results and reference intervals. |
| `get_full_patient_chart` | `patient_id: str` | `Dict[str, Any]` | Aggregates full longitudinal medical record bundle for authorized clinicians. |

---

## 3. Server 2: `clinic-scheduling-server`

- **Endpoint / Module:** `src/mcp_servers/scheduling_server.py`
- **Underlying Data Store:** `practitioners`, `clinic_branches`, and `appointments` tables
- **Exposed Tools:**

| Tool Name | Parameters | Return Schema | Purpose & Safety Constraint |
| :--- | :--- | :--- | :--- |
| `find_doctors` | `specialty: str`, `city: Optional[str]`, `branch_id: Optional[str]` | `List[Dict[str, Any]]` | Searches licensed doctors by specialty, branch, fee, and shift hours. |
| `get_doctor_slots` | `doctor_id: str`, `target_date: str` | `Dict[str, Any]` | Generates 15-minute consultation slots and filters out already-reserved slots. |
| `book_appointment` | `patient_id: str`, `doctor_id: str`, `slot_datetime: str`, `chief_complaint: str`, `urgency_tier: str` | `Dict[str, Any]` | Atomically commits booking, issues unique booking ID (`APT_BK_XXXX`), and generates sequential token number. |
| `reschedule_appointment`| `appointment_id: str`, `new_slot_datetime: str` | `Dict[str, Any]` | Atomically checks collision on new slot and updates appointment time. |
| `cancel_appointment` | `appointment_id: str`, `reason: str` | `Dict[str, Any]` | Releases consultation slot back to open clinic pool and logs cancellation rationale. |

---

## 4. Server 3: `pharmacy-safety-server`

- **Endpoint / Module:** `src/mcp_servers/drug_database_server.py`
- **Underlying Data Store:** Pakistani Outpatient Formulary & OpenFDA/DrugBank Interaction Rules
- **Exposed Tools:**

| Tool Name | Parameters | Return Schema | Purpose & Safety Constraint |
| :--- | :--- | :--- | :--- |
| `lookup_drug` | `drug_name: str` | `Dict[str, Any]` | Resolves Pakistani brand names (e.g. Augmentin, Panadol, Risek) to generic compound, max daily dose, and warnings. |
| `check_drug_interaction`| `drug_a: str`, `drug_b: str` | `Dict[str, Any]` | Evaluates pair against deterministic interaction matrix; flags `CRITICAL_DANGER` or `WARNING_MODERATE`. |
| `check_allergy_conflict`| `drug_name: str`, `patient_allergies: List[str]` | `Dict[str, Any]` | Cross-references chemical class (e.g. Penicillins, NSAIDs) with patient allergy profile to prevent anaphylaxis. |
| `verify_daily_dose` | `drug_name: str`, `dose_mg_per_intake: float`, `frequency: str`, `patient_age: int`, `patient_weight_kg: float` | `Dict[str, Any]` | Calculates total 24h intake; flags adult overdoses and calculates pediatric mg/kg limits. |

---

## 5. Server 4: `notifications-server`

- **Endpoint / Module:** `src/mcp_servers/notifications_server.py`
- **Exposed Tools:**

| Tool Name | Parameters | Return Schema | Purpose & Safety Constraint |
| :--- | :--- | :--- | :--- |
| `send_whatsapp_message`| `recipient_phone: str`, `message_text: str`, `template_name: Optional[str]` | `Dict[str, Any]` | Dispatches WhatsApp Cloud API notification with unique ID (`WA_MSG_XXXX`). |
| `send_email_summary` | `recipient_email: str`, `subject: str`, `body_html: str` | `Dict[str, Any]` | Dispatches clinical pre-visit summaries and appointment receipts via Email. |
| `send_sms_alert` | `recipient_phone: str`, `sms_text: str` | `Dict[str, Any]` | Dispatches urgent SMS alerts and arrival tokens. |
| `get_notification_audit_log`| `recipient_phone: Optional[str]` | `List[Dict[str, Any]]` | Returns immutable audit history of all dispatched messages. |

---

## 6. Independent Test Client Verification Results

All 4 servers were evaluated independently via `src/mcp_servers/mcp_test_client.py`:
- **`patient-records-server`:** Verified profile lookup and comprehensive chart aggregation.
- **`clinic-scheduling-server`:** Verified doctor discovery across specialties, slot generation, atomic booking, rescheduling, and cancellation.
- **`pharmacy-safety-server`:** Verified brand normalization, Warfarin+Aspirin critical interaction detection, Penicillin allergy interception, and pediatric Aspirin contraindication.
- **`notifications-server`:** Verified WhatsApp, Email, SMS dispatch simulation and audit log persistence.
- **Overall Result:** **100% Passed (4/4 Servers Online & Certified)**.

---
*End of Document: Model Context Protocol (MCP) Servers Specification.*
