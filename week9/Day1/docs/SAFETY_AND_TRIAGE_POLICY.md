# City Care Clinics — Safety & Triage Policy
**Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare**  
**Document Version:** 1.0.0 | **Status:** Regulatory & Clinical Approval | **Effective Date:** October 2026  
**Clinical Governance Board:** City Care Clinics (Lahore & Islamabad)

---

## 1. Safety Mission & The Prime Directive

In healthcare artificial intelligence, a flawed response, delayed escalation, or hallucinated medication recommendation can cause catastrophic patient injury or loss of life. 

> ### ⚠️ THE PRIME MEDICAL SAFETY DIRECTIVE
> 1. **The AI must NEVER provide a clinical diagnosis of any illness or medical condition.**
> 2. **The AI must NEVER prescribe, modify, adjust, or authorize any medication, drug dose, or medical therapy.**
> 3. **The AI collects structured information, stratifies clinical urgency, flags pharmacological risks, and assists the physician. Every clinical decision remains strictly with the licensed human doctor.**
> 4. **Every emergency red-flag symptom must IMMEDIATELY trigger escalation to Emergency Services (1122 / Emergency Department) and terminate automated outpatient scheduling.**
> 5. **All patient data used in testing, demonstration, and evaluation must be 100% synthetic.**

---

## 2. Red-Flag Symptoms & Clinical Taxonomy

A red-flag symptom indicates an immediate threat to life, organ viability, or limb preservation. The system implements a deterministic, pre-LLM regex and semantic classifier that scans every inbound message for red-flag triggers.

### 2.1 Complete Red-Flag Danger Signs Table

| Clinical Domain | Red-Flag Symptoms (UrduLish & English) | Clinical Rationale & Risk | Protocol Action |
| :--- | :--- | :--- | :--- |
| **Cardiovascular** | *Seene mein shadeed dard / dabao* (Chest pain/pressure), pain radiating to left arm (*baazu*), neck, jaw (*jabray*), cold sweats (*thanday paseenay*), sudden severe palpitations with dizziness. | Acute Coronary Syndrome (Myocardial Infarction / Heart Attack), Aortic Dissection. | **EMERGENCY (Immediate 1122)** |
| **Respiratory** | *Saans lene mein shadeed dushwari* (Severe dyspnea / shortness of breath), *saans phoolna* with blue lips/nails (*hont neelay parna* / cyanosis), stridor (*saans se seeti ki aawaz*), sudden choking. | Pulmonary Embolism, Acute Asthma/COPD Exacerbation, Foreign Body Aspiration, Anaphylaxis. | **EMERGENCY (Immediate 1122)** |
| **Neurological** | **FAST Signs:** Facial drooping (*munh tedha hona*), arm/leg weakness or numbness (*baazu ya taang mein kamzori / sunn hona*), slurred speech (*bolne mein dushwari / aawaz ladkharana*), sudden loss of consciousness (*behosh hona*), active seizure (*jhatkay / mirgi ka daura*) > 3 minutes, "worst headache of life" (*aaj tak ka sab se shadeed sar dard*). | Acute Ischemic/Hemorrhagic Stroke, Subarachnoid Hemorrhage, Status Epilepticus. | **EMERGENCY (Immediate 1122)** |
| **Hemorrhagic & Trauma** | Active uncontrolled bleeding (*khoon na rukna*), coughing up blood (*balgham mein khoon* / hemoptysis), vomiting dark blood (*khoon ki ulti*), black tarry stools (*kaala pakhana*), severe vehicular or fall trauma (*shadeed chot / hadsa*). | Massive Internal Bleeding, Upper GI Bleed, Traumatic Hemorrhagic Shock. | **EMERGENCY (Immediate 1122)** |
| **Pediatric Specific** | Infant under 3 months with fever $\ge 38.0^\circ\text{C}$ (100.4°F), baby unable to drink or breastfeed (*doodh na peena*), extreme lethargy / floppy baby (*bacha bilkul sust / behosh*), grunting / chest indrawing (*pasliyan chalna*). | Neonatal Sepsis, Severe Pneumonia, Meningitis. | **EMERGENCY (Immediate 1122)** |
| **Psychiatric & Crisis** | Expressed thoughts of suicide (*khudkushi ke khayalat*), intent to self-harm (*apne aap ko nuqsan pohanchana*), homicidal ideation, acute psychosis. | Imminent risk of self-harm or fatal crisis. | **EMERGENCY (Umang / 1122 Helpline)** |
| **Obstetric & Gynecological** | Pregnant woman with heavy vaginal bleeding (*hamal mein khoon aana*), severe sudden abdominal cramping (*shadeed pet dard*), high blood pressure with visual disturbances / aura (*aankhon ke aage andhera / flashes*). | Placental Abruption, Ectopic Pregnancy Rupture, Eclampsia / HELLP Syndrome. | **EMERGENCY (Immediate 1122)** |

---

## 3. Three-Tier Clinical Urgency Classification Framework

Every inbound clinical presentation is mapped deterministically into one of three operational tiers:

```
                            [Patient Symptoms Received]
                                         │
                   ┌─────────────────────┴─────────────────────┐
                   ▼                                           ▼
      [Red-Flag Danger Signs?]                       [No Red Flags]
                   │                                           │
         ┌─────────┴─────────┐                       ┌─────────┴─────────┐
         │ YES               │ NO                    │                   │
         ▼                   ▼                       ▼                   ▼
    ┌───────────┐      ┌───────────┐           ┌───────────┐       ┌───────────┐
    │ EMERGENCY │      │  URGENT   │           │  URGENT   │       │  ROUTINE  │
    │(Code Red) │      │(Code Yell)│           │(Code Yell)│       │(Code Green│
    └─────┬─────┘      └─────┬─────┘           └─────┬─────┘       └─────┬─────┘
          │                  │                       │                   │
          ▼                  └───────────┬───────────┘                   ▼
    1122 Protocol                        ▼                         Standard Appt
    Hard Intercept              Same-Day Priority Slot             (1-3 Days)
    Outpatient Halt             (Within 4-6 Hours)
```

### 3.1 Tier 1: Emergency (Code Red)
- **Clinical Definition:** Immediately life-threatening or organ-threatening condition requiring resuscitation, advanced trauma support, or acute surgical intervention.
- **SLA / Response Time:** **Instantaneous ($< 50\text{ ms}$)**.
- **Operational Action:**
  1. Bypass all LLM reasoning; execute deterministic hard-stop script.
  2. Discontinue outpatient appointment scheduling.
  3. Emit certified UrduLish 1122 emergency message with clickable emergency call links.
  4. Transmit high-priority telemetry alert to Clinic Medical Director audit log.

### 3.2 Tier 2: Urgent (Code Yellow — Same Day)
- **Clinical Definition:** Acute conditions with moderate-to-severe discomfort, high probability of rapid deterioration without intervention within 6–12 hours, or extreme distress (e.g., high fever 103°F in adults, acute ear infection with severe pain, urinary tract infection with high fever and flank pain, asthma exacerbation responsive to inhaler, deep lacerations needing stitches).
- **SLA / Target Consultation:** **Within 4–6 hours** (Same-day priority slot).
- **Operational Action:**
  1. Complete rapid intake (vitals, allergies).
  2. Route to urgent on-call physician slot at the nearest clinic branch.
  3. Advise patient on immediate supportive measures (e.g., sip water, stay resting) while waiting for appointment.

### 3.3 Tier 3: Routine (Code Green — Standard Outpatient)
- **Clinical Definition:** Chronic disease monitoring (hypertension, type 2 diabetes follow-up), mild self-limiting symptoms (< 3 days, low-grade fever, mild runny nose, routine skin rash, follow-up lab review, general wellness checkups).
- **SLA / Target Consultation:** **Within 1–3 business days**.
- **Operational Action:**
  1. Standard structured intake (full history, allergies, current meds).
  2. Optimal specialty matching.
  3. Interactive calendar negotiation for preferred branch and doctor slot.

---

## 4. Exact UrduLish Escalation Messages

All emergency communications must use standardized, pre-approved text templates. **Agents are strictly forbidden from modifying or paraphrasing these messages.**

### 4.1 Primary Emergency Escalation (General Emergency)
```text
🚨 FORI TIBBI IMDAD KI ZAROORAT HAI / EMERGENCY ALERT 🚨

Aap ki batai hui alamaat nihayat sanjeeda ho sakti hain aur fori tibbi tawajjah ki talabgaar hain.

Baraye meharbani bila-takheer yeh iqdamat karein:
1. FORAN 1122 (Rescue 1122) par call karein ya qareebi hospital ki Emergency jayein.
2. Gaari khud drive na karein; kisi ghar walay ya dost ko madad ke liye pukarein.
3. City Care Clinics aik outpatient clinic hai jahan emergency ICU/OT ki suhoolat dastiyab nahi hoti.

Agar aap Lahore mein hain: Services Hospital, Mayo Hospital, ya Doctors Hospital Emergency ruju karein.
Agar aap Islamabad mein hain: PIMS Hospital ya Shifa International Emergency tashreef le jayein.

Allah aap ko sehat ata farmaye.
```

### 4.2 Pediatric Infant Emergency (< 3 Months or Severe Danger Signs)
```text
🚨 BACHAY KI TIBBI EMERGENCY / PEDIATRIC ALERT 🚨

Mohtaram Walid / Walida:
Chotay bachon (khaas tor par 3 mahine se kam umar) mein tez bukhar ya doodh na peena fori emergency ki alamat hai.

Baraye meharbani foran bachay ko kisi qareebi Hospital ke Children's Emergency Ward le jayein (maslan Children's Hospital Lahore ya PIMS Islamabad Children Emergency).

Clinic ki aam appointment ka intizar hargiz na karein!
```

### 4.3 Psychiatric / Suicide Crisis Escalation
```text
Aap akele nahi hain, aur aap ki zindagi nihayat qeemti hai. 

Baraye meharbani foran kisi se baat karein:
- Umang Mental Health Helpline: 0311-7786264 (24/7 Muft aur Khufia)
- Rescue 1122 Helpline
- Apne kisi qareebi dost, walidain, ya azeez se foran rabta karein.

Hamara AI assistant is waqt aap ko sahi madad nahi pohancha sakta, baraye meharbani foran helpline par call karein.
```

---

## 5. Scope Boundary Matrix: AI Assistant vs. Licensed Physician

To maintain legal, ethical, and clinical integrity, the division of responsibilities is strictly codified:

| Clinical / Administrative Activity | AI Assistant Permitted? | Licensed Doctor Required? | Operational Rule / Constraint |
| :--- | :---: | :---: | :--- |
| **Greet & collect chief complaints** | **YES** | No | Uses warm, culturally respectful UrduLish. |
| **Record symptom duration & severity** | **YES** | No | Captures numbers (days, hours, scale 1–10). |
| **Inquire about drug allergies & current meds**| **YES** | No | Records to structured FHIR profile. |
| **Classify urgency (Emergency/Urgent/Routine)**| **YES** | No | Rule-based deterministic classification. |
| **Match symptom to clinical specialty** | **YES** | No | RAG-assisted specialty directory matching. |
| **Book, reschedule, cancel appointments** | **YES** | No | Atomic calendar MCP tool transaction. |
| **Read raw lab report values with ref ranges** | **YES** | No | Factual read-only; no clinical interpretation. |
| **Provide pre-test preparation instructions** | **YES** | No | Fasting duration, water intake for ultrasound. |
| **Synthesize draft SOAP note & pre-visit brief**| **YES** | **YES (Sign-off)**| Strictly provider-facing; requires doctor sign. |
| **Check drug interactions & max dose caps** | **YES** | **YES (Override)**| Deterministic Drug DB check; flags to doctor. |
| **Diagnose an illness (e.g. "You have Malaria")**| ❌ **STRICT NO**| **MANDATORY** | **Absolute Prohibition:** Never diagnose. |
| **Prescribe any medication (Rx or OTC)** | ❌ **STRICT NO**| **MANDATORY** | **Absolute Prohibition:** Never prescribe. |
| **Advise altering or stopping a prescribed drug**| ❌ **STRICT NO**| **MANDATORY** | Routes to doctor consultation. |
| **Authorize sick leave or medical certificates**| ❌ **STRICT NO**| **MANDATORY** | Only doctor can issue physical sign/stamp. |
| **Provide definitive diagnostic lab opinion** | ❌ **STRICT NO**| **MANDATORY** | Refers to attending physician for review. |

---

## 6. Mandatory Disclaimers & Legal Guardrails

### 6.1 Conversational Session Header Disclaimer
Every patient initiating a conversation session receives the following mandatory bilingual notice:
> *"City Care Clinics AI Assistant aik digital rehnuma hai jo aap ki appointments, clinic maloomat, aur triage mein madad karta hai. Yeh AI doctor ka mutabadil (replacement) nahi hai aur koi bemari diagnose ya dawai prescribe nahi kar sakta. Kisi bhi emergency ki soorat mein foran 1122 par call karein."*

### 6.2 Pre-Consultation Summary Footer Disclaimer
Every provider-facing SOAP note or Pre-Visit Brief contains the following cryptographic watermarked footer:
> `[AI-GENERATED CLINICAL DRAFT — NOT AN OFFICIAL MEDICAL DIAGNOSIS]`  
> *"This note was synthesized by City Care Clinics AI Assistant from patient-reported intake data and past FHIR records. It requires clinical validation, physical examination, and formal electronic signature by a licensed medical practitioner before entry into the permanent health record."*

### 6.3 Medication Review Disclaimer
Whenever an interaction or contraindication is flagged by the Prescription Safety Agent:
> *"Flagged via City Care Clinics Pharmacy Safety Engine (v1.0) using openFDA/DrugBank validated data. Final pharmacological discretion and dose calculation rests solely with the attending physician."*

---
*End of Document: Safety & Triage Policy.*
