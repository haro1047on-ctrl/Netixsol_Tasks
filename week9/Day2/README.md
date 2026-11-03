# Week 9 — Day 2: Data Layer, Knowledge Base & MCP Servers
## Multi-Agent AI Clinic Assistant for Healthcare (City Care Clinics)

### 📌 Milestone Overview
This milestone establishes the data foundation and tool interoperability layer for City Care Clinics across 5 physical branches in Lahore and Islamabad.

All 5 core Day 2 tasks have been built, documented, and independently verified:
1. **Task 1: Synthetic Data & FHIR Database** (500+ patients, 30 doctors, 5 branches, appointments, and observations).
2. **Task 2: Medical Knowledge RAG Pipeline** (ChromaDB vector store + hybrid lexical reranker over FAQs, lab prep guidelines, patient leaflets, and specialty maps; 25-question evaluation).
3. **Task 3: Lab Report Understanding** (PyMuPDF parser, normal-range flagger, safe UrduLish explainer, 30 synthetic PDF reports, 100% field extraction accuracy).
4. **Task 4: Model Context Protocol (MCP) Servers** (4 independent FastMCP servers: `patient-records-server`, `clinic-scheduling-server`, `pharmacy-safety-server`, `notifications-server`).
5. **Task 5: Deterministic Prescription Safety Engine** (Rule-based allergy checks, drug-drug interaction matrix, 24h dose limits, duplicate therapies, and special population contraindications).

---

## 📂 Deliverables Directory Map

| Task # | Deliverable Title | Documentation / Code Link | Description |
| :---: | :--- | :--- | :--- |
| **Task 1** | **FHIR Database & ER Diagram** | [ER_DIAGRAM_AND_SCHEMA.md](file:///d:/netixsol_work/week9/Day2/docs/ER_DIAGRAM_AND_SCHEMA.md) | Mermaid ER diagram, FHIR v4 relational data dictionary, PostgreSQL/SQLite configuration. |
| **Task 1** | **FHIR Relational Models** | [db_models.py](file:///d:/netixsol_work/week9/Day2/src/db_models.py) | SQLAlchemy models for Patient, Practitioner, Appointment, Observation, MedicationRequest, Condition, AllergyIntolerance. |
| **Task 1** | **Synthetic Data Generator** | [data_generator.py](file:///d:/netixsol_work/week9/Day2/src/data_generator.py) | Populates 500+ Pakistani patients, 30 doctors across 6 specialties, appointments, and observations using Faker and clinical distributions. |
| **Task 2** | **RAG Evaluation Report** | [RAG_EVALUATION_REPORT.md](file:///d:/netixsol_work/week9/Day2/docs/RAG_EVALUATION_REPORT.md) | 4 knowledge categories, citation architecture, 25-question ground-truth evaluation, 88.0% grounding rate. |
| **Task 2** | **RAG Pipeline & Benchmark** | [rag_pipeline.py](file:///d:/netixsol_work/week9/Day2/src/rag_pipeline.py) | ChromaDB persistent store with dense + lexical reranker and mandatory source citations. |
| **Task 3** | **Lab Extraction Benchmark Report**| [LAB_REPORT_EXTRACTION_REPORT.md](file:///d:/netixsol_work/week9/Day2/docs/LAB_REPORT_EXTRACTION_REPORT.md)| Document AI pipeline analysis, 30-report accuracy benchmark, safe non-diagnostic UrduLish communication rules. |
| **Task 3** | **PDF Lab Report Generator** | [lab_report_generator.py](file:///d:/netixsol_work/week9/Day2/src/lab_report_generator.py) | Generates 30 realistic PDF diagnostic reports (CBC, LFT, Lipid, HbA1c, RFT) using ReportLab. |
| **Task 3** | **PDF Lab Report Analyzer** | [lab_report_analyzer.py](file:///d:/netixsol_work/week9/Day2/src/lab_report_analyzer.py) | PyMuPDF text/table parser, JSON extractor, normal-range flagger, safe UrduLish explainer (100% field accuracy). |
| **Task 4** | **MCP Servers Specification** | [MCP_SERVERS_SPECIFICATION.md](file:///d:/netixsol_work/week9/Day2/docs/MCP_SERVERS_SPECIFICATION.md)| Technical contract, JSON-RPC schemas, and tool specifications for all 4 MCP servers. |
| **Task 4** | **Patient Records MCP Server** | [patient_records_server.py](file:///d:/netixsol_work/week9/Day2/src/mcp_servers/patient_records_server.py) | FastMCP server exposing patient profile, allergies, conditions, meds, and longitudinal chart. |
| **Task 4** | **Clinic Scheduling MCP Server** | [scheduling_server.py](file:///d:/netixsol_work/week9/Day2/src/mcp_servers/scheduling_server.py) | FastMCP server managing doctor discovery, 15-minute slot generation, atomic bookings, rescheduling, and cancellations. |
| **Task 4** | **Drug Database MCP Server** | [drug_database_server.py](file:///d:/netixsol_work/week9/Day2/src/mcp_servers/drug_database_server.py) | FastMCP server exposing Pakistani formulary, DDI matrix, allergy clashes, and dose calculations. |
| **Task 4** | **Notifications MCP Server** | [notifications_server.py](file:///d:/netixsol_work/week9/Day2/src/mcp_servers/notifications_server.py) | FastMCP server dispatching simulated WhatsApp, Email, and SMS with immutable delivery audit logs. |
| **Task 4** | **Independent MCP Test Client** | [mcp_test_client.py](file:///d:/netixsol_work/week9/Day2/src/mcp_servers/mcp_test_client.py) | Independent inspector runner verifying tools across all 4 servers (100% pass rate). |
| **Task 5** | **Prescription Safety Specification**| [PRESCRIPTION_SAFETY_SPECIFICATION.md](file:///d:/netixsol_work/week9/Day2/docs/PRESCRIPTION_SAFETY_SPECIFICATION.md)| 5-vector audit framework, clinical justification for deterministic checks vs. LLM-only checks. |
| **Task 5** | **Prescription Safety Engine** | [prescription_safety_engine.py](file:///d:/netixsol_work/week9/Day2/src/prescription_safety_engine.py)| Rule-based engine auditing allergy clashes, DDIs, daily dose ceilings, duplicate therapies, and special populations. |
| **Runner** | **Master Day 2 Validation Suite** | [run_day2.py](file:///d:/netixsol_work/week9/Day2/run_day2.py) | Executable test suite verifying Tasks 1–5 end-to-end. |

---

## 🚀 Execution & Verification

Run the master Day 2 test suite directly:

```bash
python week9/Day2/run_day2.py
```

### Verified Benchmark Summary:
- **Task 1 (Database):** 500 Patients, 30 Doctors, 5 Branches, 1,020+ Appointments, 180+ Observations verified in `clinic_fhir.db`.
- **Task 2 (RAG):** 25/25 questions evaluated (88.0% Grounding Rate, 84.0% Top-1 Retrieval Precision, 100% source citations).
- **Task 3 (Lab PDFs):** 30 synthetic PDF lab reports parsed with 100.0% report success and 100.0% field extraction accuracy (408/408 fields).
- **Task 4 (MCP Servers):** 4/4 FastMCP servers independently certified (`patient-records`, `scheduling`, `drug-database`, `notifications`).
- **Task 5 (Rx Safety):** 100% interception of lethal DDIs (Warfarin + Aspirin), Penicillin allergy clashes, pediatric Aspirin contraindications, adult overdoses, and pregnancy Category D/X drugs.
