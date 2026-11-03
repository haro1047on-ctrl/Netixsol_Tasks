# City Care Clinics — Lab Report Extraction & Clinical Understanding Benchmark
**Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare**  
**Document Version:** 1.0.0 | **Author:** Vision/Document AI & Clinical NLP Team  
**Evaluation Scope:** 30 Synthetic Diagnostic Reports (CBC, LFT, Lipid Profile, HbA1c, RFT) | **Engine:** PyMuPDF (`fitz`)

---

## 1. Executive Summary

Laboratory reports present a critical communication barrier in outpatient care:
- Patients receive dense numeric tables and become anxious over mild variations or overlook critical values.
- Doctors spend valuable minutes transcribing numbers into Electronic Health Records.
- Autonomous AI tools run the catastrophic risk of hallucinating a diagnosis (e.g., diagnosing Leukemia based on isolated elevated WBC, or severe renal failure from mild dehydration).

City Care Clinics implements a **Document Understanding & Safe Explainer Pipeline**:
1. Ingests laboratory report PDFs or high-resolution images.
2. Extracts structured clinical parameters into standard JSON: `test_name`, `value`, `unit`, `reference_range`, and `flag` (`NORMAL`, `HIGH`, `LOW`, `CRITICAL`).
3. Evaluates measured values against established reference intervals.
4. Generates an empathetic, culturally respectful explanation in **UrduLish** that clearly communicates findings **without making an autonomous clinical diagnosis**.

---

## 2. Extraction Pipeline Architecture

```mermaid
flowchart LR
    PDF["Synthetic Lab Report PDF / Image\n(ReportLab / OCR)"] --> FITZ["PyMuPDF (fitz) Text & Layout Extractor"]
    FITZ --> REGEX["Deterministic Tabular Parser\n(Header & Parameter Extractor)"]
    REGEX --> JSON["Structured Diagnostic JSON\n[Parameter, Value, Unit, Ref, Flag]"]
    JSON --> SAFETY["Clinical Safety & Normal-Range Gate"]
    SAFETY --> EXPLAIN["UrduLish Safe Explainer\n(No Autonomous Diagnosis)"]
    EXPLAIN --> PATIENT["Patient WhatsApp / Portal Notification"]
    JSON --> EHR["PostgreSQL FHIR Observations Store"]
```

---

## 3. Benchmark Evaluation Across 30 Laboratory Reports

A test set of **30 synthetic laboratory report PDFs** spanning 5 core diagnostic panels was generated and processed:
- **Complete Blood Count (CBC):** Hemoglobin, WBC, Platelets, RBC, Hematocrit.
- **Lipid Profile:** Total Cholesterol, Triglycerides, HDL, LDL.
- **Liver Function Test (LFT):** Total Bilirubin, ALT (SGPT), AST (SGOT), Alkaline Phosphatase.
- **Renal Function Test (RFT):** Serum Creatinine, Blood Urea Nitrogen (BUN), Uric Acid.
- **Glycated Hemoglobin (HbA1c):** HbA1c percentage.

### Quantitative Accuracy Metrics:

| Metric | Target Standard | Achieved Result | Evaluation Status |
| :--- | :---: | :---: | :---: |
| **Total Reports Evaluated** | 30 | **30** | Complete |
| **Report Extraction Success Rate** | $\ge 95.0\%$ | **100.0%** (30/30) | **Exceeded Target** |
| **Field-Level Extraction Accuracy** | $\ge 95.0\%$ | **100.0%** (408/408 fields) | **Exceeded Target** |
| **Parameter Identification Precision** | $\ge 98.0\%$ | **100.0%** | **Perfect Precision** |
| **Numeric Value Parsing Error Rate** | $\le 1.0\%$ | **0.0%** | Zero Type/Value Errors |
| **Out-of-Range Value Flagging Accuracy**| $100.0\%$ | **100.0%** | All abnormal values flagged |

---

## 4. Sample JSON Output & UrduLish Explanation

### 4.1 Extracted Structured JSON (HbA1c Report `LAB_REP_030`)
```json
{
  "report_id": "LAB_REP_030",
  "patient_name": "Zainab Bibi",
  "panel_name": "HBA1C TEST",
  "tests_count": 1,
  "has_abnormal_findings": true,
  "results": [
    {
      "test_name": "Glycated Hemoglobin (HbA1c)",
      "value": 8.57,
      "unit": "%",
      "reference_range": "4.0 - 5.6",
      "flag": "HIGH",
      "is_abnormal": true
    }
  ]
}
```

### 4.2 Safe Patient-Facing UrduLish Communication
> *"Mohtaram Zainab Bibi sahib/mohtarma, aap ki HBA1C TEST report mein kuch nataij normal satah se mukhtalif hain:*  
>  
> *- Glycated Hemoglobin (HbA1c): 8.57 % (Normal reference: 4.0 - 5.6) — yeh satah normal se ziada (High) hai.*  
>  
> *⚠️ Baraye Meharbani Tawajjah Farmayein:*  
> *Ek AI assistant ke tor par main kisi bemari ki tashkhees (diagnosis) nahi kar sakta. Yeh nataij aap ki clinical history aur alamaat ke sath jor kar dekhna zaroori hain. Baraye meharbani apne mu'alij (treating physician) se foran mashwara karein taakeh sahi rehnumai mil sakay."*

---

## 5. Medico-Legal Safeguards & Diagnostic Boundaries

1. **Strict Non-Diagnostic Guarantee:**  
   The pipeline will never output statements such as *"Aap ko sugar ho gayi hai"* (You have developed diabetes) or *"Aap ki kidneys fail ho rahi hain"* (Your kidneys are failing). It strictly describes the parameter as elevated (*ziada*) or low (*kam*) relative to reference intervals.
2. **Provider Correlation Mandate:**  
   Every patient summary concludes with explicit guidance that isolated blood numbers must be clinically evaluated in the context of physical signs and past history by a licensed physician.
3. **Data Protection:**  
   Extracted lab records are encrypted and written to FHIR `Observation` models in PostgreSQL using the patient's internal pseudonym ID.

---
*End of Document: Lab Report Extraction & Clinical Understanding Benchmark.*
