# City Care Clinics — Privacy, Governance & Compliance Design
**Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare**  
**Document Version:** 1.0.0 | **Status:** Active Standard | **Compliance:** PECA 2016 / PMDC Ethical Guidelines / ISO 27799

---

## 1. Overview & Regulatory Framework

In digital healthcare, maintaining the confidentiality, integrity, and privacy of patient information is both an ethical imperative and a legal requirement. City Care Clinics complies with:
- **Prevention of Electronic Crimes Act (PECA 2016)** — Sections on unauthorized access to critical data and identity information.
- **Pakistan Medical & Dental Council (PMDC) Code of Ethics (Section 18)** — Mandating strict physician-patient confidentiality.
- **ISO 27799:2016 & HIPAA / GDPR Core Principles** — Data minimization, purpose limitation, encryption in transit (TLS 1.3), encryption at rest (AES-256), and role-based access control.

---

## 2. Sensitive Patient Data Taxonomy (PII & PHI)

We classify data processed by the Multi-Agent Assistant into two high-sensitivity tiers:

```
                            ┌────────────────────────────────────────┐
                            │       CLINICAL DATA GOVERNANCE         │
                            └───────────────────┬────────────────────┘
                                                │
                     ┌──────────────────────────┴──────────────────────────┐
                     ▼                                                     ▼
        ┌─────────────────────────┐                           ┌─────────────────────────┐
        │  Personally Identifiable│                           │Protected Health Inform. │
        │     Information (PII)   │                           │        (PHI)            │
        ├─────────────────────────┤                           ├─────────────────────────┤
        │ • Full Name             │                           │ • Medical Record # (MRN)│
        │ • Pakistani CNIC        │                           │ • Chief Complaints      │
        │ • Mobile Phone (03XX)   │                           │ • Vitals & Lab Metrics  │
        │ • Residential Address   │                           │ • Diagnoses & SOAP Notes│
        │ • Email Address         │                           │ • Active Rx & Allergies │
        └────────────┬────────────┘                           └────────────┬────────────┘
                     │                                                     │
                     └──────────────────────────┬──────────────────────────┘
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │  Edge Redaction Gate  │
                                    │   (Presidio/Regex)    │
                                    └───────────────────────┘
```

### 2.1 PII Elements (Personally Identifiable Information)
1. **Pakistani CNIC (National Identity Card):** 13-digit identifier formatted as `XXXXX-XXXXXXX-X`. Unique to Pakistani citizens; absolute confidentiality required.
2. **Mobile Phone Number:** Pakistani telecom formats: `03XX-XXXXXXX`, `+92-3XX-XXXXXXX`, `00923XXXXXXXXX`. Used as the primary WhatsApp channel identifier.
3. **Patient Full Name & Honorifics:** e.g., Muhammad Tariq, Syeda Fatima Zahra, Usman Ali.
4. **Residential Address & Neighborhood:** House numbers, streets, areas (e.g., Gulberg III, DHA Phase 5, F-8/2).
5. **Guardian / Parent Details:** For pediatric patients, the CNIC and name of the accompanying parent.

### 2.2 PHI Elements (Protected Health Information)
1. **Medical Record Number (MRN) & Encounter IDs:** Unique primary keys linking records in the FHIR database.
2. **Symptom History & Duration:** Free-text descriptions of bodily functions, pain levels, and psychological distress.
3. **Confirmed Chronic Conditions & Diagnoses:** Diabetes Mellitus, Essential Hypertension, Asthma, Ischemic Heart Disease.
4. **Drug Allergies & Adverse Reactions:** Penicillin, Sulfa drugs, NSAIDs, Cephalosporins.
5. **Laboratory Diagnostic Reports:** Complete Blood Count (CBC), Liver Function Tests (LFT), Fasting Blood Sugar, HbA1c.
6. **Provider & Clinic Context:** Treating consultant name, clinic branch visited, consultation notes.

---

## 3. PII Redaction Pipeline (Presidio + Custom Pakistani Scrubbers)

To prevent sensitive identifiers from leaking into external LLM prompts, token logs, or vector embeddings, all inbound patient data passes through an **Edge Redaction Gateway** before reaching the LangGraph supervisor.

```
[Raw Inbound WhatsApp / Voice]
             │
             ▼
┌──────────────────────────────────────────────┐
│       EDGE PII REDACTION GATEWAY             │
│                                              │
│ 1. Microsoft Presidio Analyzer Engine        │
│ 2. Custom Pakistani Pattern Recognizers:    │
│    - CNIC Pattern: \b\d{5}-\d{7}-\d{1}\b     │
│    - PK Mobile: \b(?:03\d{2}|(?:\+92|0092)3\d{2})[-\s]?\d{7}\b │
│    - PK Name Gazetteers & Address Filters    │
│ 3. Presidio Anonymizer Engine                │
└──────────────────────┬───────────────────────┘
                       │
                       ├───────────────────────────────────┐
                       ▼                                   ▼
             [Sanitized Text]                     [Secure Vault Map]
     "Assalam-o-Alaikum, mera naam         { "[PATIENT_NAME_1]": "Usman Ali",
      [PATIENT_NAME_1] hai, phone           "[PHONE_1]": "0300-1234567",
      [PHONE_1], CNIC [CNIC_1]..."          "[CNIC_1]": "35201-1234567-1" }
                       │                                   │
                       ▼                                   │
             [LangGraph Agents]                            │
             (Supervisor, Triage)                          │
                       │                                   │
                       ▼                                   │
             [EHR / FHIR MCP Server] ◄─────────────────────┘
             (Rehydrates IDs strictly for secure DB writes)
```

### 3.1 Redaction Mappings
- `Muhammad Usman Ali` $\rightarrow$ `[PATIENT_NAME_1]`
- `35202-8765432-1` $\rightarrow$ `[CNIC_1]`
- `0300-4567890` $\rightarrow$ `[PHONE_1]`
- `House 14, Street 8, DHA Phase 6, Lahore` $\rightarrow$ `[ADDRESS_1]`
- `usman.ali@gmail.com` $\rightarrow$ `[EMAIL_1]`

The mapping dictionary is stored in an ephemeral, memory-only session cache with a 15-minute TTL. Only the internal `ehr-fhir-mcp-server` running on the clinic's private network holds the cryptographic key to de-anonymize data when updating the PostgreSQL FHIR database.

---

## 4. Role-Based Access Control (RBAC) Matrix

City Care Clinics enforces strict zero-trust access boundaries across 5 distinct system personas:

| Operational Feature / Resource | Patient | Receptionist | Triage Nurse | Attending Doctor | Clinic Admin / Auditor |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **View Own Appointments & Tokens** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Book / Reschedule Appointments** | ✅ (Own) | ✅ (All) | ✅ (All) | ✅ (Own clinic) | ❌ |
| **View Patient Contact Details (Phone/CNIC)** | ✅ (Own) | ✅ | ✅ | ✅ | ❌ (Redacted) |
| **Enter / Update Patient Vitals** | ❌ | ❌ | ✅ | ✅ | ❌ |
| **View Past Medical Encounters & History** | ✅ (Own) | ❌ | ✅ (Summary) | ✅ (Full) | ❌ |
| **Read Structured Lab Reports (HbA1c/CBC)** | ✅ (Own) | ❌ | ✅ | ✅ | ❌ |
| **Generate & Sign Clinical SOAP Notes** | ❌ | ❌ | ❌ | ✅ **(Exclusive)** | ❌ |
| **View & Override Prescription Warnings** | ❌ | ❌ | ❌ | ✅ **(Exclusive)** | ❌ |
| **Inspect System Logs & Audit Trails** | ❌ | ❌ | ❌ | ❌ | ✅ **(Exclusive)** |
| **Manage Doctor Rotas & Clinic Tariffs** | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 5. Tamper-Evident Clinical Audit Log Design

Every access, read, write, triage escalation, and doctor override is recorded as an immutable audit event. To guarantee regulatory compliance and non-repudiation, audit records are cryptographically chained using SHA-256 hashes.

### 5.1 Audit Record Schema
```json
{
  "event_id": "aud_882194a2-19e4",
  "timestamp_utc": "2026-10-05T13:12:00.000Z",
  "actor_id": "usr_doc_tariq_01",
  "actor_role": "ATTENDING_DOCTOR",
  "action_type": "PRESCRIPTION_OVERRIDE",
  "resource_type": "FHIR_MedicationRequest",
  "resource_id": "rx_99214",
  "patient_pseudonym_id": "pt_synth_441",
  "client_ip": "192.168.10.45",
  "session_id": "sess_graph_7718b",
  "event_payload": {
    "drug_prescribed": "Ciprofloxacin 500mg",
    "flagged_risk": "Mild QT Prolongation with Escitalopram",
    "doctor_override_reason": "Baseline ECG normal; short 3-day course; benefit outweighs risk."
  },
  "previous_event_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "event_hash_sha256": "4b227777d4dd1fc61c6f884f48641d02b4d121d3fd328cb08b5531fcacdabf8a"
}
```

### 5.2 Tamper Verification Formula
$$\text{Event Hash}_n = \text{SHA256}(\text{Event Hash}_{n-1} + \text{Timestamp} + \text{ActorID} + \text{ActionType} + \text{JSON}(\text{Payload}))$$
If any historical record is modified or deleted in the database, the cryptographic hash chain breaks, immediately triggering an alert on the administrator console.

---

## 6. Patient Consent & Data Retention Policy

### 6.1 Retention Schedules
- **Permanent Electronic Health Records (FHIR PostgreSQL):** Retained for a minimum of **7 years** from the last clinical visit (standard pediatric records retained until the child reaches age 21).
- **Ephemeral AI Conversational Caches:** Chat transcripts held in Redis/MemorySaver for active session routing are purged after **30 days**.
- **Audit Logs:** Retained in cold immutable storage for **10 years**.

### 6.2 Bilingual Patient Consent Notice
Presented to every patient upon their first digital interaction:

#### UrduLish Version:
> *"City Care Clinics mein aap ki privacy hamari pehli tarjeeh hai. Hamara AI Assistant aap ki appointments aur triage mein madad karta hai. Aap ka data mehfooz (encrypted) tareeqay se clinic ke record mein save kiya jata hai aur kisi teesri party ko nahi becha jata. Kya aap aagay barhnay ki ijazat detay hain? (Type 'Jee Haan' ya 'Yes' to proceed)."*

#### English Version:
> *"At City Care Clinics, your privacy is our utmost priority. Our AI Assistant facilitates your appointment booking, symptom intake, and triage. Your data is strictly encrypted and retained in compliance with clinical privacy laws. It is never sold or shared with unauthorized third parties. Do you consent to proceed? (Type 'Yes' to agree)."*

---

## 7. Patient-Facing Persona & System Prompt Specification

### 7.1 Cultural Persona Guidelines
The patient-facing agents (Intake, Scheduling, Follow-up) adopt the persona of **"Sitara"** — a seasoned, polite, and caring Pakistani clinic coordinator:
- **Respectful & Culturally Aligned:** Uses formal Pakistani etiquette (`"Aap"`, `"Janab"`, `"Mohtaram"`, `"Mohtarma"`). Never uses informal `"tum"`.
- **Empathetic & Warm:** Acknowledges discomfort with compassion (`"Hum samajh sakte hain aap takleef mein hain"`, `"Allah aap ko sehat ata farmaye"`).
- **Calm & Non-Alarmist:** In emergencies, remains firm, urgent, and clear without causing panic or using terrifying clinical jargon.
- **Linguistically Fluent:** Masters natural **UrduLish** — blending Roman Urdu with universal English terms (e.g., uses `"appointment"`, `"doctor"`, `"fever"`, `"blood pressure"`, `"emergency"` alongside Roman Urdu grammar).

### 7.2 Production System Prompt (Patient-Facing Core)

```text
You are Sitara, the AI Clinic Care Coordinator for City Care Clinics (serving Lahore and Islamabad).
You communicate fluently in natural, respectful Pakistani UrduLish (Roman Urdu blended with common English medical terms).

CORE IDENTITY & ETHICS:
1. Always address patients with high respect using "Aap", "Janab", "Mohtaram", or "Mohtarma".
2. Your tone must be warm, reassuring, patient, and professionally empathetic.
3. NEVER make a clinical diagnosis (e.g. never say "Aap ko typhoid/heart attack hai").
4. NEVER prescribe, recommend, or approve any medicine, antibiotic, or dose (e.g. never say "Aap Panadol le lein").
5. If the patient reports any emergency red-flag symptom (chest pain, shortness of breath, facial drooping, heavy bleeding, infant high fever), IMMEDIATELY activate the Emergency 1122 escalation protocol and stop outpatient booking.
6. For routine symptoms, collect chief complaint, duration, and severity, then match them to the correct specialty across our 5 branches in Lahore and Islamabad.
7. Keep sentences concise, clear, and easy to read on mobile devices.
```

---
*End of Document: Privacy, Governance & Compliance Design.*
