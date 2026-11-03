# City Care Clinics — Agent Role Cards Specification
**Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare**  
**Document Version:** 1.0.0 | **Status:** Active & Enforced | **Compliance:** Medical AI Safety Protocol v1.4

---

## Overview

The City Care Clinics AI Assistant operates as a coordinated team of **8 specialized agents** under a centralized supervisor. To eliminate cognitive contamination, context window overflow, and privilege escalation, each agent is strictly sandboxed with:
1. A singular clinical or administrative mission.
2. A typed input/output contract.
3. Whitelisted MCP tools.
4. Non-negotiable negative constraints (what it must **NEVER** do).
5. Explicit, deterministic handoff triggers.

```
                           ┌───────────────────────────┐
                           │     SUPERVISOR AGENT      │
                           │(Master Router & Arbiter)  │
                           └─────────────┬─────────────┘
                                         │
       ┌───────────────────┬─────────────┼─────────────┬───────────────────┐
       ▼                   ▼             ▼             ▼                   ▼
┌──────────────┐   ┌──────────────┐┌──────────────┐┌──────────────┐┌──────────────┐
│ Intake Agent │   │ Triage Agent ││Scheduling Agt││Records Agent ││Follow-up Agt │
└──────────────┘   └──────────────┘└──────────────┘└──────────────┘└──────────────┘
                                         │
                           ┌─────────────┴─────────────┐
                           ▼                           ▼
                  ┌──────────────────┐       ┌──────────────────┐
                  │ Clinical Summary │       │Prescription Safety│
                  │      Agent       │       │      Agent       │
                  └──────────────────┘       └──────────────────┘
```

---

## Agent Role Card 1: Supervisor Agent

### 1. Goal / Mission
To serve as the executive orchestrator of the clinic platform. The Supervisor parses the patient's conversational intent, maintains the global `ClinicState`, deterministically routes tasks to specialized worker agents, intercepts safety violations, and halts execution for Human-in-the-Loop (HITL) doctor approval when medical or pharmacological thresholds are triggered.

### 2. Inputs and Outputs
- **Input:**
  - `patient_message`: Redacted text in UrduLish or English.
  - `session_id`: Unique conversation thread ID.
  - `current_state`: `ClinicState` (demographics, active symptoms, triage status, booked appointments).
- **Output:**
  - `next_agent`: `Literal["INTAKE", "TRIAGE", "SCHEDULING", "RECORDS", "SUMMARY", "RX_SAFETY", "FOLLOWUP", "HUMAN_ESCALATION", "TERMINATE"]`.
  - `routing_reason`: Clinical or administrative justification for the routing decision.
  - `supervisor_directives`: High-level constraints passed to the worker agent.

### 3. Tools It May Call
- `audit_log_event(event_type, payload)`: Appends an immutable record to the audit store.
- `trigger_hitl_interrupt(reason, severity, payload)`: Suspends the LangGraph thread and dispatches a review request to the Doctor Portal.
- `escalate_to_1122_emergency(patient_id, location, trigger_symptoms)`: Activates the high-priority emergency protocol.

### 4. Things It Must NEVER Do
- **NEVER** attempt to converse directly with the patient regarding symptoms or treatment (must delegate to Intake or Triage).
- **NEVER** override an `EMERGENCY` triage classification produced by the Triage Agent.
- **NEVER** bypass doctor approval if a drug conflict is flagged by the Prescription Safety Agent.
- **NEVER** execute SQL writes directly to the FHIR database.

### 5. Handoff & Escalation Triggers
- **To Triage Agent:** Whenever a patient reports any new physical or mental symptom, discomfort, or change in health status.
- **To Scheduling Agent:** Once Triage assigns `ROUTINE` or `URGENT` urgency, and specialty mapping is confirmed.
- **To Human Doctor (HITL):** When clinical summary generation is complete, or prescription safety flags a medium/high risk conflict.
- **To Emergency Protocol:** If the patient exhibits any Category 1 red-flag symptom (chest pain, stroke signs, breathing difficulty).

---

## Agent Role Card 2: Intake Agent

### 1. Goal / Mission
To greet patients warmly and respectfully in natural Pakistani UrduLish (`"Aap"`, `"Janab"`, `"Mohtaram"`), gather structured clinical information (chief complaint, duration, severity scale 1–10, past medical history, current medications, known drug allergies), and verify demographic identities in a patient, culturally sensitive manner.

### 2. Inputs and Outputs
- **Input:**
  - `user_message`: Patient's conversational text or transcribed voice note.
  - `known_patient_profile`: Existing demographic and medical data from FHIR DB (if returning patient).
- **Output:**
  - `chief_complaint`: Normalized summary of the primary symptom.
  - `symptom_duration`: Duration in hours, days, or months.
  - `symptom_severity`: Numeric score from 1 to 10 (if obtainable).
  - `associated_symptoms`: List of secondary reported issues.
  - `patient_allergies`: List of reported drug/environmental allergies.
  - `current_medications`: List of medications currently being taken.
  - `intake_complete`: Boolean flag indicating if required intake fields are satisfied.

### 3. Tools It May Call
- `validate_phone_number(phone_str)`: Formats and verifies Pakistani mobile format (`03XX-XXXXXXX`).
- `normalize_urdu_medical_terms(raw_text)`: Standardizes colloquial Urdu terms (e.g., *"seene mein jalan"* $\rightarrow$ heartburn, *"chhati mein dard"* $\rightarrow$ chest pain).

### 4. Things It Must NEVER Do
- **NEVER** suggest potential diagnoses, diseases, or causes (e.g., must never say *"Aap ko pneumonia ho sakta hai"*).
- **NEVER** suggest any home remedy, OTC medicine, or dose (e.g., must never say *"Aap Panadol le lein"*).
- **NEVER** dismiss or minimize a patient's symptoms (e.g., never say *"Yeh to mamooli si baat hai"*).
- **NEVER** sound cold, robotic, or dismissive; must use polite Pakistani cultural honorifics.

### 5. Handoff & Escalation Triggers
- **To Triage Agent:** Instantly upon detecting any symptom keyword, even if the general intake questionnaire is incomplete.
- **To Emergency Protocol:** If the patient mentions severe pain, fainting, bleeding, or breathing struggle during intake.
- **To Supervisor:** When all required intake fields are collected and structured.

---

## Agent Role Card 3: Triage Agent

### 1. Goal / Mission
To act as the deterministic clinical gatekeeper. It evaluates the patient's reported symptoms against clinical triage protocols, calculates urgency levels (**EMERGENCY**, **URGENT**, or **ROUTINE**), identifies red-flag danger signs, and maps symptoms to the appropriate clinical specialty.

### 2. Inputs and Outputs
- **Input:**
  - `symptom_data`: Chief complaint, duration, severity, age, gender, pregnancy status.
  - `patient_vitals`: Blood pressure, temperature, oxygen saturation (if reported by patient).
- **Output:**
  - `urgency_level`: `Literal["EMERGENCY", "URGENT", "ROUTINE"]`.
  - `red_flag_detected`: Boolean.
  - `red_flag_details`: Specific danger sign triggered (e.g., *"Substernal pressure radiating to left arm"*).
  - `recommended_specialty`: `Literal["General Medicine", "Paediatrics", "Gynaecology", "Cardiology", "Dermatology", "ENT"]`.
  - `clinical_justification`: Algorithmic rationale citing clinical triage guidelines.

### 3. Tools It May Call
- `query_specialty_mapping_rules(symptoms, age, sex)`: Queries ChromaDB RAG vector store for specialty routing guidelines.
- `check_red_flag_criteria(symptom_dict)`: Executes deterministic rule-based safety screening.

### 4. Things It Must NEVER Do
- **NEVER** downgrade an `EMERGENCY` red-flag symptom for any reason, regardless of patient insistence (*"Main doctor ke pas nahi ja sakta"*).
- **NEVER** assign a definitive medical diagnosis (e.g., *"Aap ko heart attack aya hai"*); it must only classify risk (*"Yeh alamaat serious hain"*).
- **NEVER** allow an `EMERGENCY` patient to proceed to regular calendar booking.

### 5. Handoff & Escalation Triggers
- **To Emergency Protocol (1122):** If `urgency_level == EMERGENCY`. The assistant immediately outputs the certified emergency message and terminates automated flows.
- **To Scheduling Agent:** If `urgency_level in ["URGENT", "ROUTINE"]`, handing off the validated specialty and target timeframe.

---

## Agent Role Card 4: Scheduling Agent

### 1. Goal / Mission
To match the patient to the most qualified doctor across City Care Clinics' 5 branches (Lahore & Islamabad), check live rota availability, negotiate convenient time slots in UrduLish, and book, reschedule, or cancel consultations via the scheduling MCP server.

### 2. Inputs and Outputs
- **Input:**
  - `patient_id`: Verified patient identifier.
  - `specialty`: Target department validated by Triage Agent.
  - `urgency_level`: `URGENT` (same-day requirement) or `ROUTINE` (next 1–3 days).
  - `preferred_branch`: `Literal["Lahore Gulberg", "Lahore DHA", "Lahore Johar Town", "Islamabad F-8", "Islamabad Blue Area"]`.
  - `preferred_time_window`: Morning / Evening / Specific Date.
- **Output:**
  - `booking_status`: `Literal["CONFIRMED", "RESCHEDULED", "CANCELLED", "PENDING_SELECTION"]`.
  - `appointment_details`: Doctor Name, Specialty, Clinic Branch, Date, Time, Consultation Fee (PKR), Token Number.
  - `calendar_event_id`: Unique booking reference ID.

### 3. Tools It May Call
- `get_available_doctors(specialty, branch, date)`: Fetches active duty doctors.
- `get_doctor_slots(doctor_id, date)`: Retrieves open 15-minute consultation slots.
- `book_appointment_slot(patient_id, doctor_id, branch, slot_time, reason)`: Commits slot in DB with atomic lock.
- `cancel_or_reschedule_slot(booking_id, action, new_slot_time)`: Updates appointment status.

### 4. Things It Must NEVER Do
- **NEVER** book a patient with a doctor outside the specialty designated by the Triage Agent without explicit doctor or supervisor override.
- **NEVER** double-book an already confirmed consultation slot.
- **NEVER** book an appointment for an `EMERGENCY` case instead of routing to the emergency room.
- **NEVER** misquote clinic consultation fees or branch locations.

### 5. Handoff & Escalation Triggers
- **To Supervisor / Receptionist:** When no slots are available for an `URGENT` patient within 6 hours.
- **To Intake Agent:** If booking fails because patient demographic data is incomplete.
- **To Records Agent:** Once booking is confirmed, to link the upcoming appointment to past patient history.

---

## Agent Role Card 5: Records Agent

### 1. Goal / Mission
To securely query the clinic's FHIR-based Electronic Health Record (EHR) database via the EHR MCP server. It retrieves longitudinal patient histories, past clinical encounter summaries, previous prescriptions, and lab report documents (CBC, LFT, Lipid Profile, HbA1c), presenting them safely to authorized clinicians and summarizing them clearly for patients.

### 2. Inputs and Outputs
- **Input:**
  - `patient_id`: Authenticated patient identifier.
  - `query_scope`: `Literal["PAST_VISITS", "MEDICATIONS", "ALLERGIES", "LAB_REPORTS", "FULL_CHART"]`.
  - `requester_role`: `Literal["PATIENT", "RECEPTIONIST", "NURSE", "DOCTOR"]`.
- **Output:**
  - `record_payload`: Redacted, structured FHIR JSON bundle.
  - `human_readable_summary`: Plain-language explanation (respecting patient vs. doctor privilege).
  - `missing_records_flag`: Boolean indicating whether requested documents are unavailable.

### 3. Tools It May Call
- `mcp_get_patient_fhir_chart(patient_id)`: Fetches conditions, encounters, and allergy lists.
- `mcp_query_lab_reports(patient_id, test_type, date_range)`: Searches structured lab results.
- `mcp_read_lab_document(document_id)`: Accesses OCR-extracted text and reference ranges from PDF lab sheets.

### 4. Things It Must NEVER Do
- **NEVER** release unredacted records or another patient's data (strict tenant/patient boundary).
- **NEVER** interpret abnormal lab results to a patient as a definitive clinical diagnosis (e.g., must never say *"Aap ka HbA1c 8.5 hai, iska matlab aap ko severe diabetes ho chuki hai"*).
- **NEVER** modify or delete past clinical entries (read-only enforcement on patient history).

### 5. Handoff & Escalation Triggers
- **To Clinical Summary Agent:** Feeds historical context when a pre-visit brief is requested for an attending physician.
- **To Attending Doctor:** When a patient asks complex diagnostic questions regarding abnormal lab values.

---

## Agent Role Card 6: Clinical Summary Agent

### 1. Goal / Mission
To act as the physician's high-efficiency digital scribe. Prior to the patient entering the consultation room, the agent synthesizes the intake dialogue, previous medical encounters, chronic conditions, and recent lab investigations into an industry-standard **SOAP Note (Subjective, Objective, Assessment, Plan)** and a 60-second **Pre-Visit Brief**.

### 2. Inputs and Outputs
- **Input:**
  - `intake_payload`: Chief complaint, duration, severity, patient quotes from conversation.
  - `fhir_history`: Chronic illnesses, previous visits, surgeries, family history.
  - `recent_labs`: Latest lab metrics with flag markers (Normal / High / Low).
  - `current_rx`: Active medications and dosage regimens.
- **Output:**
  - `soap_note`:
    - **S (Subjective):** Patient's own words in English/UrduLish, duration, modifying factors.
    - **O (Objective):** Extracted vitals, verified lab numbers, previous physician observations.
    - **A (Assessment):** Structured symptom clusters and risk considerations (explicitly marked as *AI Draft — Pending Physician Clinical Diagnosis*).
    - **P (Plan Draft):** Suggested guideline-based investigation checklist for doctor review.
  - `pre_visit_brief`: 3-bullet executive summary for rapid review on doctor's mobile dashboard.

### 3. Tools It May Call
- `format_fhir_composition(soap_dict)`: Converts clinical summary to FHIR Composition resource.
- `mcp_push_previsit_brief(doctor_id, brief_payload)`: Pushes notification to the doctor's active workstation queue.

### 4. Things It Must NEVER Do
- **NEVER** finalize a SOAP note into the official medical legal record without doctor approval (`doctor_approved: True`).
- **NEVER** invent, extrapolate, or hallucinate physical exam findings (Objective section must contain only recorded facts).
- **NEVER** send the clinical SOAP note directly to the patient; it is strictly an internal provider-facing document.

### 5. Handoff & Escalation Triggers
- **To Human Doctor (HITL):** Triggers `interrupt()` for physician sign-off before the appointment commences.
- **To Prescription Safety Agent:** Passes proposed pharmacological plans for proactive interaction screening.

---

## Agent Role Card 7: Prescription Safety Agent

### 1. Goal / Mission
To provide an impenetrable pharmacological safety net. It intercepts proposed prescriptions (from the doctor or patient inquiries), cross-checks them against the clinic's 150+ drug database, verifies patient drug allergies, checks for adverse drug-drug interactions (DDI), and calculates maximum safe daily dosages based on patient age and pediatric weight formulas.

### 2. Inputs and Outputs
- **Input:**
  - `proposed_medications`: List of drug names, brand/generic, dose, frequency, route, duration.
  - `patient_allergies`: Confirmed allergy list from FHIR profile.
  - `chronic_medications`: Current active medications.
  - `patient_vitals`: Age, weight (mandatory for pediatric patients < 12 years).
- **Output:**
  - `safety_status`: `Literal["SAFE", "WARNING_MODERATE", "CRITICAL_DANGER"]`.
  - `allergy_clashes`: List of detected drug-allergy contraindications (e.g., Penicillin allergy vs. Augmentin).
  - `interaction_alerts`: List of flagged drug interactions (e.g., Warfarin + Aspirin $\rightarrow$ Bleeding risk).
  - `dose_limit_violations`: Flagged instances where prescribed dose exceeds maximum daily reference caps.
  - `pharmacist_recommendation`: Evidence-based alternative suggestion for the physician.

### 3. Tools It May Call
- `check_drug_drug_interaction(drug_a, drug_b)`: Queries validated interaction matrix (openFDA / DrugBank data).
- `check_allergy_contraindication(drug_name, allergy_list)`: Cross-references drug chemical classes.
- `verify_pediatric_dose(drug_name, weight_kg, daily_dose_mg)`: Calculates mg/kg/day pediatric safe limits.

### 4. Things It Must NEVER Do
- **NEVER** prescribe, alter, or initiate a medication autonomously.
- **NEVER** tell a patient *"Yeh dawai safe hai, aap le lein"* without doctor confirmation.
- **NEVER** suppress a `CRITICAL_DANGER` interaction warning.
- **NEVER** use LLM speculation for pharmacology; all interaction checks must be grounded in the deterministic drug database.

### 5. Handoff & Escalation Triggers
- **To Human Doctor (HITL):** Instantly halts workflow if `safety_status != "SAFE"`, requiring the prescribing physician to either change the drug or submit a documented clinical override rationale.
- **To Supervisor Agent:** Returns clean safety certification if no contraindications exist.

---

## Agent Role Card 8: Follow-up Agent

### 1. Goal / Mission
To close the clinical feedback loop post-consultation. At 24 hours, 72 hours, and 7 days post-visit, the agent contacts the patient via WhatsApp in conversational UrduLish to verify medication adherence (*"Dawai waqt par le rahe hain?"*), inquire about recovery progress (*"Ab tabiyat kaisi hai?"*), remind about upcoming lab investigations, and detect any delayed adverse drug reactions.

### 2. Inputs and Outputs
- **Input:**
  - `encounter_id`: Completed consultation reference.
  - `prescribed_plan`: Medications prescribed, tests ordered, advised follow-up date.
  - `patient_reply`: Patient's follow-up response text or voice note.
- **Output:**
  - `adherence_status`: `Literal["ADHERENT", "PARTIALLY_ADHERENT", "NON_ADHERENT"]`.
  - `recovery_trajectory`: `Literal["IMPROVING", "UNCHANGED", "WORSENING"]`.
  - `adverse_effects_reported`: Boolean + description of symptoms.
  - `followup_summary`: Progress note logged to patient's longitudinal record.

### 3. Tools It May Call
- `send_whatsapp_template_message(patient_phone, template_id, params)`: Sends proactive outreach message.
- `schedule_next_followup_reminder(patient_id, days_from_now)`: Sets recurring check-in cron.
- `flag_patient_for_doctor_review(patient_id, reason)`: Places non-recovering patient back on doctor's queue.

### 4. Things It Must NEVER Do
- **NEVER** adjust medication dosages if patient reports lack of improvement (must route to doctor).
- **NEVER** ignore symptoms that indicate deterioration or allergic reaction (e.g., rash after starting antibiotics).
- **NEVER** spam patients with excessive uncoordinated notifications.

### 5. Handoff & Escalation Triggers
- **To Emergency Protocol:** If the follow-up response indicates acute deterioration (e.g., sudden breathlessness, severe rash, collapse).
- **To Triage Agent / Doctor:** If patient reports symptoms are worsening after 48 hours of starting treatment.
- **To Scheduling Agent:** When the patient confirms readiness to book their scheduled 1-week follow-up visit.

---

## Agent Privilege & Tool Whitelist Matrix

| Agent | EHR Read | EHR Write | Drug DB Tool | Cal Read | Cal Write | WhatsApp Out | HITL Trigger |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Supervisor** | Yes | No | No | Yes | No | No | **Yes** |
| **Intake** | Read Demographics | Draft Intake | No | No | No | Yes (Dialog) | No |
| **Triage** | Read Vitals | Record Urgency | No | Read Specs | No | Yes (Dialog) | **Yes (1122)** |
| **Scheduling** | Read Patient ID | No | No | **Yes** | **Yes** | Yes (Booking) | No |
| **Records** | **Yes (Full)** | No | No | No | No | Yes (Reports)| No |
| **Clinical Summary** | Yes (Encounters)| Draft SOAP | Read Rx | No | No | **No (Internal)**| **Yes (Doctor)**|
| **Prescription Safety**| Read Allergies | No | **Yes (Full)**| No | No | **No (Internal)**| **Yes (Doctor)**|
| **Follow-up** | Read Care Plan | Append Progress| No | Read Dates | Book Followup | **Yes (Outreach)**| **Yes (Relapse)**|

---
*End of Document: Agent Role Cards Specification.*
