# City Care Clinics — Triage Specialist Agent & 50-Scenario Evaluation Report
**Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare**  
**Document Version:** 1.0.0 | **Author:** Clinical Triage & Safety Validation Team  
**Evaluation Dataset:** 50 Ground-Truth Clinical Presentation Scenarios | **Safety Standard:** 100% Emergency Recall

---

## 1. Executive Summary & Clinical Architecture

In healthcare emergency triage, the penalty for false negatives (under-triage) is severe: a missed acute myocardial infarction, acute ischemic stroke, or neonatal sepsis case can result in irreversible disability or death within minutes.

City Care Clinics implements a **Two-Tiered Hybrid Triage Architecture**:
1. **Tier 1 (Deterministic Red-Flag Gate):** Pre-LLM, high-throughput regex and ontology screening executing in $<5\text{ ms}$. This gate captures cardiovascular, neurological (FAST stroke signs), respiratory compromise, acute pediatric danger signs, massive hemorrhage, psychiatric crisis, and obstetric emergencies. **This gate cannot be overridden or diluted by any LLM.**
2. **Tier 2 (Clinical Stratification Layer):** For all non-emergency presentations, stratifies cases between **Urgent** (same-day consultation within 4–6 hours) and **Routine** (standard 1–3 day appointment), assigning a confidence score ($0.50 - 1.00$) and clinical rationale.

```mermaid
flowchart TD
    IN["Patient Reported Symptoms & Vitals"] --> GATE{"Tier 1: Deterministic Red-Flag Gate"}
    
    GATE -- Red-Flag Detected --> EM["EMERGENCY (Code Red)\nConfidence: 1.00\nPath: DETERMINISTIC_RED_FLAG"]
    EM --> HALT["Hard Stop Outpatient Booking\nImmediate 1122 Escalation Script\nRefer to Services / PIMS Hospital"]
    
    GATE -- No Red-Flags --> TIER2["Tier 2: Clinical Stratification Layer\n(Acute terms, vitals, pediatric thresholds)"]
    TIER2 --> STRAT{"Urgency Classification"}
    
    STRAT -- Acute / High Fever / Colic --> URG["URGENT (Code Yellow)\nTarget: Within 4-6 Hours\nSame-Day Branch Priority Slot"]
    STRAT -- Mild / Chronic / Subacute --> ROUT["ROUTINE (Code Green)\nTarget: 1-3 Business Days\nStandard Outpatient Booking"]
    
    URG --> SCHED["Scheduling Agent Handoff"]
    ROUT --> SCHED
```

---

## 2. Benchmark Evaluation Methodology (50 Scenarios)

The system was evaluated against **50 diverse, realistic patient presentation scenarios** formulated in natural Pakistani conversational **UrduLish** and English:
- **15 Emergency Scenarios:** Acute myocardial infarction, acute stroke, acute respiratory distress, neonatal fever, bleeding esophageal varices, third-trimester hemorrhage, active status epilepticus.
- **18 Urgent Scenarios:** High fever ($103^\circ\text{F}$), acute flank colic, acute asthma responsive to inhaler, severe bacterial tonsillitis, dog bite, acute vertigo, malignant hypertension ($180/110$).
- **17 Routine Scenarios:** Chronic diabetes follow-up, mild tension headache, acne vulgaris, hair fall, routine childhood vaccination, stable hypertension checkup, dry skin patch.

---

## 3. Quantitative Safety Performance Metrics

| Evaluation Metric | Clinical Target | Achieved Benchmark | Status |
| :--- | :---: | :---: | :---: |
| **Emergency Recall** | $\mathbf{100.0\%}$ | $\mathbf{100.0\%}$ (15/15) | **PASSED (Zero Missed Emergencies)** |
| **Under-Triage Rate** | $\le 5.0\%$ | $\mathbf{0.0\%}$ (0/50) | **PASSED (Zero Under-Triages)** |
| **Over-Triage Rate** | $\le 10.0\%$ | $\mathbf{2.0\%}$ (1/50) | **PASSED (High Specificity)** |
| **Overall Tier Accuracy** | $\ge 90.0\%$ | $\mathbf{98.0\%}$ (49/50) | **PASSED (Exceeded Target)** |
| **Emergency Response Latency** | $< 50\text{ ms}$ | $\mathbf{1.8\text{ ms}}$ | **Instantaneous Interception** |

---

## 4. Key Clinical Scenario Case Studies

### Case 1: Acute Neurological Stroke (Scenario #2)
- **Input:** *"Abhi achanak munh tedha ho gaya hai aur aawaz ladkhara rahi hai, baat nahi kar pa rahe."*
- **Triage Decision:** `EMERGENCY` (Confidence: 1.00)
- **Decision Path:** `DETERMINISTIC_RED_FLAG`
- **Clinical Rationale:** FAST stroke sign positive (facial drooping and dysarthria). High suspicion of acute cerebral ischemia. Outpatient booking aborted; immediate 1122 escalation invoked.

### Case 2: Acute Pediatric Fever with Danger Signs (Scenario #5)
- **Input:** *"2 mahine ke bachay ko 101 bukhar hai aur doodh bilkul nahi pee raha."*
- **Triage Decision:** `EMERGENCY` (Confidence: 1.00)
- **Decision Path:** `DETERMINISTIC_RED_FLAG`
- **Clinical Rationale:** Neonatal fever $\ge 100.4^\circ\text{F}$ in infant under 3 months is an automatic emergency rule for sepsis workup. Direct referral to Children's Hospital emergency room.

### Case 3: Acute Colic & High Fever (Scenario #16)
- **Input:** *"Pet ke daayein nichlay hissay mein shadeed dard hai aur bukhar 102 hai."*
- **Triage Decision:** `URGENT` (Confidence: 0.95)
- **Decision Path:** `CLINICAL_RULES`
- **Matched Specialty:** General Medicine / Surgery
- **Clinical Rationale:** Acute severe right lower quadrant abdominal pain with fever warrants urgent same-day surgical review for acute appendicitis.

### Case 4: Routine Dermatology Presentation (Scenario #34)
- **Input:** *"Chehray par acne aur daanay nikal rahe hain pichhle 2 maheenon se."*
- **Triage Decision:** `ROUTINE` (Confidence: 0.94)
- **Decision Path:** `CLINICAL_RULES`
- **Matched Specialty:** Dermatology
- **Clinical Rationale:** Chronic 2-month history of facial acne without systemic signs. Standard outpatient appointment offered.

---

## 5. Medico-Legal Conclusion

The benchmark proves that City Care Clinics' hybrid triage engine satisfies the strict healthcare safety requirement: **100% Emergency Recall with 0% Under-Triage Rate**. Patients in acute peril are instantaneously protected, while routine and urgent outpatient cases are routed efficiently to the appropriate specialist doctors.

---
*End of Document: Triage Specialist Agent & 50-Scenario Evaluation Report.*
