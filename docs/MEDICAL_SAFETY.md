# City Care Clinics — Clinical Safety Guardrails & Emergency Escalation

**Classification:** Medical Governance, Emergency Protocols & Risk Management  
**Benchmark Target:** 100% Recall on Life-Threatening Red Flags  
**Implementation Modules:** `week9/Day1/src/triage_engine.py`, `week9/Day4/src/supervisor_graph.py`, `week9/Day2/src/prescription_safety_engine.py`  

---

## 1. Core Clinical Safety Principles

The AI Clinic Assistant is engineered as a **clinical administrative and triage support tool**, NOT an autonomous diagnostic physician. Four inviolable principles govern its clinical operation:

1. **Deterministic Red-Flag Priority:** Rule-based emergency keyword and pattern scanners execute on turn 1 before any LLM inference occurs. No LLM confidence score can suppress an emergency escalation.
2. **Zero Autonomous Diagnosis:** The assistant never issues formal diagnostic declarations (e.g., "You have appendicitis"). It identifies symptom clusters and routes patients to the appropriate clinical specialist.
3. **Zero Autonomous Prescribing:** The assistant never recommends specific pharmacological prescription dosages directly to a patient without licensed physician sign-off.
4. **Physician Final Authority (HITL):** All communications interpreting abnormal diagnostic tests or discussing prescription changes must be approved by a clinic doctor.

---

## 2. Deterministic Emergency Red-Flag Protocol

### 2.1 Monitored Clinical Syndromes

The system actively screens for 7 acute clinical emergencies across English and Roman Urdu (UrduLish):

| Clinical Syndrome | Key Indicator Terms (English & UrduLish) | Deterministic Action |
| :--- | :--- | :--- |
| **Acute Coronary Syndrome (MI)** | Chest pain, seene mein shadeed dard, left arm pain, jaw pain, sweating, ghhabrahat, chakkar | Immediate Red Flag (1122 Escalation) |
| **Acute Stroke (FAST Protocol)** | Facial drooping, munh terha, arm weakness, baazu sun, speech slurred, bolnay mein dikkat | Immediate Red Flag (1122 Escalation) |
| **Severe Respiratory Distress** | Cannot breathe, saans lene mein shaded takleef, cyanosis, blue lips, wheezing at rest | Immediate Red Flag (1122 Escalation) |
| **Severe Hemorrhage / Trauma** | Uncontrolled bleeding, khoon behna, head injury, behosh ho gaya, loss of consciousness | Immediate Red Flag (1122 Escalation) |
| **Pediatric Critical Danger Signs** | Neonatal fever (< 3 months $\ge 100.4^\circ\text{F}$), bachay ko jhatkay (convulsions), lethargy | Immediate Red Flag (1122 Escalation) |
| **Acute Toxic Ingestion / Poison** | Swallowed chemical, poison, keera mar dawai, phenoil, overdose | Immediate Red Flag (1122 Escalation) |
| **Suicidal Ideation / Crisis** | Khudkushi, want to end my life, self-harm, jaan khatam | Immediate Crisis Helpline + 1122 |

### 2.2 Short-Circuit Architecture
When any red-flag pattern matches:
1. `intake_node` immediately mutates state: `triage_level = "EMERGENCY"`.
2. Graph execution short-circuits directly to `outbound_dispatch_node` in under 1 millisecond.
3. The patient is provided with urgent lifesaving instructions:
   - Call Rescue **1122** immediately.
   - Do not attempt to drive alone.
   - Nearest emergency departments with addresses across Lahore and Islamabad.

```
[Incoming User Message]
          │
          ▼
┌───────────────────────────────────────────────┐
│  Deterministic Red-Flag Screening (Regex/Dict)│
└───────────────────────────────────────────────┘
          │
          ├───► [Match Found] ──► Immediate Short-Circuit ──► Rescue 1122 Message
          │
          └───► [No Red Flag] ──► Continue Conversational Intake & LLM Workup
```

---

## 3. Bilingual Emergency Response Scripts

### English Emergency Script
> ⚠️ **CRITICAL MEDICAL EMERGENCY DETECTED**  
> Based on your symptoms, you require immediate emergency medical care.  
> 1. **Call Rescue 1122 immediately** or have someone drive you to the nearest hospital emergency room.  
> 2. Sit in a comfortable position and do not exert yourself.  
> 3. Nearest Emergency Facility: **Services Hospital Emergency / National Hospital DHA (Lahore)** or **PIMS Hospital (Islamabad)**.  
> *Do not wait for an online clinic appointment.*

### UrduLish (Roman Urdu) Emergency Script
> ⚠️ **FORI EMERGENCY ITTILA**  
> Aap ki alamaat shadeed hain aur in ke liye fori emergency medical treatment ki zaroorat hai.  
> 1. **Foran Rescue 1122 par call karein** ya qareebi hospital ke emergency ward tashreef le jayein.  
> 2. Khushi ya ghabrahat se bachein aur aaram se baith jayein.  
> 3. Qareebi Emergency: **Services Hospital / National Hospital (Lahore)** ya **PIMS Hospital (Islamabad)**.  
> *Online appointment ka intezar hargiz mat karein.*

---

## 4. Prescription Safety Engine

The `PrescriptionSafetyEngine` (`week9/Day2/src/prescription_safety_engine.py`) protects patients from dangerous medication events:

### 4.1 Allergy Cross-Reactivity
- Scans patient's recorded `AllergyIntoleranceModel` against prescribed drug and its pharmacological drug class.
- Recognizes beta-lactam cross-reactivity (e.g. Penicillin allergy triggers alert on Augmentin, Amoxicillin, Ampicillin).

### 4.2 Drug-Drug Interactions (DDI)
- Rule-based detection of dangerous co-prescriptions:
  - `Warfarin` + `Aspirin` / `NSAIDs` $\rightarrow$ Severe bleeding risk.
  - `ACE Inhibitors` + `Potassium-Sparing Diuretics` $\rightarrow$ Hyperkalemia risk.
  - `Metformin` + `Iodinated Radiocontrast` $\rightarrow$ Lactic acidosis risk.

### 4.3 Daily Maximum Dose Ceilings
- Enforces strict limits:
  - Paracetamol / Panadol: Max $4000\text{ mg}$ per 24 hours.
  - Ibuprofen: Max $2400\text{ mg}$ per 24 hours.

### 4.4 Special Populations
- Pregnancy contraindications: ACE inhibitors, statins, and retinoids flagged as strictly contraindicated.
- Pediatric weight-based dosing flags for patients under 12 years of age.

---

## 5. Doctor Human-in-the-Loop (HITL) Workflow

Communications involving high clinical risk trigger an approval requirement:
- **Condition 1:** Abnormal lab report findings (e.g., HbA1c $> 8.0\%$, Troponin elevation, severe anemia).
- **Condition 2:** Medication changes, dosage inquiries, or prescription safety warnings.
- **Condition 3:** Triage classification confidence score below $0.85$.

### Clinical Action Workflow
1. The AI synthesizes a draft clinical note.
2. The draft is stored in `DoctorApprovalRequestModel` with status `PENDING`.
3. Outbound dispatch to the patient is blocked.
4. The physician reviews the request in the Doctor Oversight Dashboard:
   - **`APPROVE`**: Dispatches the draft as composed.
   - **`EDIT_AND_APPROVE`**: Doctor customizes the text before dispatching.
   - **`REJECT`**: Suppresses the message and replaces it with clinic booking instructions.
