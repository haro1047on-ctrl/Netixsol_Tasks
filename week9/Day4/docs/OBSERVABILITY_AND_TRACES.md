# City Care Clinics — Observability & Patient Journey Traces

**Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare**  
**Document:** Day 4 Task 5 — Telemetry, Latency Tracking & Annotated Patient Journeys  
**Status:** Validated & Benchmarked  

---

## 1. Executive Summary

The **Observability Framework** tracks, audits, and quantifies every turn, agent node execution, and tool invocation across the clinic multi-agent network.

Key capabilities:
1. **Full Trace Visibility:** Captures parent `trace_id` per encounter thread with nested child spans for each specialist agent.
2. **Tool Execution Auditing:** Logs tool inputs, execution duration in milliseconds, and returned payloads.
3. **Token Usage & Financial Accounting:** Calculates prompt and completion token counts and estimates operational API costs based on standard pricing models ($0.0001 / 1k prompt, $0.0002 / 1k completion).
4. **Latency Analysis:** Records execution duration per agent node.
5. **Safety & Governance Metrics:** Quantifies emergency red-flag escalation frequency and doctor override rates.

---

## 2. Global Observability Telemetry Metrics

Summary telemetry across benchmarked operational encounters:

| Metric | Measured Value | Standard Target | Assessment |
|---|:---:|:---:|:---:|
| **Mean Conversation Latency** | **620.23 ms** | < 1,500 ms | **Optimal (Sub-second)** |
| **Mean Cost per Conversation** | **$0.000124 USD** | < $0.005000 USD | **Ultra-Low Cost** |
| **Mean Processed Tokens per Turn** | **920 tokens** | < 2,500 tokens | **Concise Context** |
| **Emergency Escalation Rate** | **33.3%** | Clinical Need | **Zero Missed Emergencies** |
| **HITL Doctor Oversight Rate** | **33.3%** | Clinical Need | **Strict Safety Gate** |

---

## 3. Annotated Walkthrough of Three Complete Patient Journeys

---

### Journey 1: Acute Pediatric Fever & Earache (Paediatric Outpatient Flow)
- **Patient:** Ahmed Raza (Age: 4 years, Child) | **ID:** `PT_0002` | **Channel:** WhatsApp
- **Presenting Complaint:** *"Mere 4 saal ke betay ko bukhar 102 hai aur kaan mein dard hai."*
- **Trace ID:** `tr_f571f0d40bb4` | **Pipeline Latency:** 622.6 ms | **Tokens:** 690 | **Cost:** $0.000093 USD

```mermaid
sequenceDiagram
    autonumber
    actor Patient as Parent (WhatsApp)
    participant Sup as Supervisor Router
    participant Intake as Intake Agent
    participant Rec as Records Agent
    participant Tri as Triage Agent
    participant Sum as Clinical Summary
    participant Sch as Scheduling Agent
    participant Dis as WhatsApp Dispatcher

    Patient->>Sup: "Mere 4 saal ke betay ko bukhar 102 hai aur kaan mein dard hai"
    Sup->>Intake: Process Intake Turn
    Intake->>Sup: Form Complete (Chief Complaint: Bukhar + Kaan dard, Identity: CHILD)
    par Parallel Evaluation
        Sup->>Rec: Fetch Longitudinal EHR Chart
        Sup->>Tri: Evaluate Pediatric Symptoms
    end
    Rec-->>Sum: Loaded Past Pediatric Otitis History
    Tri-->>Sum: Urgency: URGENT | Specialty: Paediatrics
    Sum->>Sch: Pre-Visit SOAP Brief Synthesized
    Sch->>Sch: Filter DHA Branch + Paediatricians -> Dr. Bilal Aslam
    Sch->>Sup: Reserved Slot: 2026-10-15 17:30 (Token #2)
    Sup->>Dis: Dispatch WhatsApp Confirmation
    Dis-->>Patient: "Aapki appointment Dr. Bilal Aslam (Paediatrics) ke saath confirm ho chuki hai..."
```

**Clinical Outcome:**  
Pre-visit SOAP note prepared with otitis media differential and recommended otoscopy. 48-hour WhatsApp adherence check scheduled.

---

### Journey 2: Returning Adult Diabetic (Lab Result Query & HITL Doctor Edit)
- **Patient:** Shoaib Bhatti (Age: 54 years) | **ID:** `PT_0005` | **Channel:** Web Chat
- **Presenting Query:** *"Mera aakhri HbA1c test result kya aya tha aur kya mujhe sugar ki dawa badalni chahiye?"*
- **Trace ID:** `tr_8f6914e82492` | **Pipeline Latency:** 456.1 ms | **Tokens:** 690 | **Cost:** $0.000093 USD

```mermaid
sequenceDiagram
    autonumber
    actor Patient as Returning Patient (Web Chat)
    participant Sup as Supervisor Router
    participant Mem as Memory Manager
    participant Rec as Records Agent
    participant HITL as HITL Gate Node
    actor Doctor as Dr. Tariq Mahmood (Portal)
    participant Dis as Web Chat Dispatcher

    Patient->>Sup: "Mera aakhri HbA1c test result kya aya tha..."
    Sup->>Mem: Query Longitudinal Memory
    Mem-->>Sup: Returning Patient Confirmed: Shoaib Bhatti (Doctor: Dr. Tariq Mahmood)
    Sup->>Rec: Query Laboratory Observations
    Rec-->>Sup: HbA1c: 8.2% (HIGH, Date: 2026-08-14)
    Sup->>HITL: Flag Output: Explaining Diagnostic Lab & Medication
    Note over HITL: WORKFLOW HALTS: Queued for Physician Sign-Off
    Doctor->>HITL: Inspect Draft: "Aapka HbA1c 8.2% hai... Metformin shuru karein."
    Doctor->>HITL: EDIT MESSAGE: "Aapka HbA1c 8.2% aya hai... Barah-e-karam clinic tashreef layein."
    HITL-->>Dis: Resume Graph with Doctor-Edited Message
    Dis-->>Patient: Dispatched Doctor-Approved Clinical Guidance
```

**Clinical Outcome:**  
Prevented premature medication prescription over chat. Attending physician Dr. Tariq Mahmood intervened, edited the guidance, and scheduled a clinic consultation.

---

### Journey 3: Acute Cardiac Red-Flag (Immediate Emergency Escalation)
- **Patient:** Usman Tariq (Age: 58 years) | **ID:** `PT_0003` | **Channel:** Telephony / Voice
- **Presenting Complaint:** *"Mere seene mein achanak shadeed dard shuru hua hai jo baayein baazu mein ja raha hai aur paseenay aa rahe hain."*
- **Trace ID:** `tr_a1d3f1c81bc5` | **Pipeline Latency:** 782.0 ms | **Tokens:** 1,380 | **Cost:** $0.000186 USD

```mermaid
sequenceDiagram
    autonumber
    actor Patient as Caller (Voice Telephony)
    participant Sup as Supervisor Router
    participant Intake as Intake Agent
    participant Tri as Triage Agent (Red-Flag Engine)
    participant Dis as Voice Dispatcher

    Patient->>Sup: "Mere seene mein achanak shadeed dard shuru hua hai..."
    Sup->>Intake: Extract Complaint
    Intake->>Tri: Evaluate Clinical Presentation
    Note over Tri: RED-FLAG DETECTED: Acute Coronary Syndrome (Chest pain + Radiation)
    Tri-->>Sup: URGENCY: EMERGENCY | Bypass Routine Scheduling
    Sup->>Dis: Dispatch 1122 Ambulance Emergency Protocol
    Dis-->>Patient: 🚨 FORI TIBBI IMDAD KI ZAROORAT HAI: Foran 1122 call karein!
```

**Clinical Outcome:**  
Zero delay. Routine scheduling, SOAP synthesis, and prescription nodes were bypassed. Caller was directed to Rescue 1122 and nearest tertiary hospital emergency room.
