# City Care Clinics — FHIR-Inspired Relational Database & ER Specification
**Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare**  
**Document Version:** 1.0.0 | **Standard:** HL7 FHIR v4 Aligned Relational Architecture  
**Database Engines Supported:** PostgreSQL (Production) / SQLite (Local Embedded)

---

## 1. Executive Summary & Clinical Data Modeling

In healthcare AI architectures, persisting clinical facts in unstructured key-value stores or free-text chats leads to data fragmentation, un-audited state, and catastrophic clinical mismatch. City Care Clinics implements an **HL7 FHIR v4 (Fast Healthcare Interoperability Resources)** inspired relational data layer.

### Core FHIR Entities Represented:
1. **`Patient`**: Master patient identity, demographics, Pakistani telecom identifiers, CNIC, and proxy relationships.
2. **`Practitioner`**: Licensed clinicians, specialties, clinic branch affiliations, PMDC registration numbers, and consulting schedules.
3. **`ClinicBranch`**: Physical healthcare facilities in Lahore and Islamabad, emergency tertiary referral hospital links.
4. **`Appointment`**: Outpatient booking lifecycle (`booked`, `arrived`, `fulfilled`, `cancelled`, `rescheduled`), triage urgency tiers, and token sequencing.
5. **`Observation`**: Quantitative and qualitative diagnostic findings (HbA1c, CBC, LFT, Lipid, RFT), reference intervals, and interpretation flags (`NORMAL`, `HIGH`, `LOW`, `CRITICAL`).
6. **`MedicationRequest`**: Active and historical pharmacological orders, dose regimens, and prescribing physician links.
7. **`Condition`**: Active problem lists, chronic medical illnesses, and ICD-10 diagnostic classifications.
8. **`AllergyIntolerance`**: Critical drug and environmental sensitivities with manifestation notes and risk severity markers.

---

## 2. Entity-Relationship (ER) Diagram

The complete relational topology is illustrated in the Mermaid diagram below:

```mermaid
erDiagram
    CLINIC_BRANCH ||--o{ PRACTITIONER : "employs"
    CLINIC_BRANCH ||--o{ APPOINTMENT : "hosts"
    
    PATIENT ||--o{ ALLERGY_INTOLERANCE : "records"
    PATIENT ||--o{ CONDITION : "diagnosed_with"
    PATIENT ||--o{ MEDICATION_REQUEST : "prescribed"
    PATIENT ||--o{ APPOINTMENT : "schedules"
    PATIENT ||--o{ OBSERVATION : "undergoes"
    
    PRACTITIONER ||--o{ APPOINTMENT : "attends"
    PRACTITIONER ||--o{ MEDICATION_REQUEST : "authors"

    CLINIC_BRANCH {
        string id PK
        string name
        string city
        string address
        string phone
        string emergency_hospital_nearby
    }

    PRACTITIONER {
        string id PK
        string name
        string specialty
        string branch_id FK
        string pmdc_number
        string qualification
        int experience_years
        int consultation_fee_pkr
        string languages_spoken
        string available_days
        string shift_hours
    }

    PATIENT {
        string id PK
        string full_name
        string gender
        string birth_date
        int age
        boolean is_pediatric
        string phone
        string cnic
        string address
        string city
        string emergency_contact
        datetime created_at
    }

    ALLERGY_INTOLERANCE {
        string id PK
        string patient_id FK
        string substance
        string clinical_status
        string verification_status
        string category
        string criticality
        string manifestation
        string recorded_date
    }

    CONDITION {
        string id PK
        string patient_id FK
        string code
        string display_name
        string clinical_status
        string category
        string severity
        string onset_date
    }

    MEDICATION_REQUEST {
        string id PK
        string patient_id FK
        string practitioner_id FK
        string medication_name
        string generic_name
        float dose_mg
        string frequency
        string route
        string status
        string authored_on
    }

    APPOINTMENT {
        string id PK
        string patient_id FK
        string practitioner_id FK
        string branch_id FK
        string specialty
        string slot_datetime
        string status
        int token_number
        string urgency_tier
        text chief_complaint
        datetime created_at
    }

    OBSERVATION {
        string id PK
        string patient_id FK
        string test_category
        string code
        string display_name
        float value_numeric
        string value_string
        string unit
        float reference_low
        float reference_high
        string interpretation
        string effective_datetime
    }
```

---

## 3. Relational Table Specifications & Data Dictionary

### 3.1 `patients` Table
- **`id`** (`VARCHAR(50)`, PK): Unique pseudonymized patient identifier (e.g. `PT_0042`).
- **`full_name`** (`VARCHAR(100)`, Not Null): Patient full name formatted in Pakistani naming conventions.
- **`gender`** (`VARCHAR(20)`, Not Null): `MALE` / `FEMALE` / `OTHER`.
- **`birth_date`** (`VARCHAR(20)`): ISO format date `YYYY-MM-DD`.
- **`age`** (`INTEGER`, Not Null): Derived age in years (0 to 120).
- **`is_pediatric`** (`BOOLEAN`): True if age < 14 years.
- **`phone`** (`VARCHAR(30)`, Indexed): Pakistani mobile format (`03XX-XXXXXXX`).
- **`cnic`** (`VARCHAR(30)`, Indexed, Nullable): National ID card format `XXXXX-XXXXXXX-X`.
- **`address`** (`VARCHAR(255)`): Residential street, sector/phase, and city.
- **`city`** (`VARCHAR(50)`): Clinic catchment area (Lahore, Islamabad, Rawalpindi).
- **`emergency_contact`** (`VARCHAR(50)`): Kin phone number for acute escalations.

### 3.2 `practitioners` Table
- **`id`** (`VARCHAR(50)`, PK): Doctor identifier (e.g. `DOC_001` to `DOC_030`).
- **`name`** (`VARCHAR(100)`, Not Null): Full professional title (e.g. Dr. Tariq Mahmood).
- **`specialty`** (`VARCHAR(50)`, Not Null): One of the 6 core outpatient specialties:
  1. *General Medicine*
  2. *Paediatrics*
  3. *Gynaecology*
  4. *Cardiology*
  5. *Dermatology*
  6. *ENT*
- **`branch_id`** (`VARCHAR(50)`, FK $\rightarrow$ `clinic_branches.id`): Base physical facility.
- **`pmdc_number`** (`VARCHAR(30)`, Not Null): Certified Pakistan Medical & Dental Council license.
- **`qualification`** (`VARCHAR(100)`): Post-graduate degrees (FCPS, MRCP, MRCOG, FRCS).
- **`consultation_fee_pkr`** (`INTEGER`): Clinic tariff (PKR 2,000 to 4,000).
- **`shift_hours`** (`VARCHAR(50)`): Standard consultation window (e.g. `17:00-21:00`).

### 3.3 `appointments` Table
- **`id`** (`VARCHAR(50)`, PK): Booking reference (e.g. `APT_0042_0`).
- **`patient_id`** (`VARCHAR(50)`, FK $\rightarrow$ `patients.id`, Indexed).
- **`practitioner_id`** (`VARCHAR(50)`, FK $\rightarrow$ `practitioners.id`, Indexed).
- **`branch_id`** (`VARCHAR(50)`, FK $\rightarrow$ `clinic_branches.id`).
- **`slot_datetime`** (`VARCHAR(50)`, Not Null): Target consultation timestamp.
- **`status`** (`VARCHAR(30)`): `booked`, `arrived`, `fulfilled`, `cancelled`, `rescheduled`.
- **`token_number`** (`INTEGER`): Serial queue token for clinic arrival.
- **`urgency_tier`** (`VARCHAR(30)`): `ROUTINE`, `URGENT`, `EMERGENCY`.
- **`chief_complaint`** (`TEXT`): Intake complaint summary.

### 3.4 `observations` Table
- **`id`** (`VARCHAR(50)`, PK): Diagnostic observation primary key.
- **`patient_id`** (`VARCHAR(50)`, FK $\rightarrow$ `patients.id`, Indexed).
- **`test_category`** (`VARCHAR(50)`): Diagnostic panel (`HbA1c`, `CBC`, `Lipid`, `LFT`, `RFT`).
- **`code`** (`VARCHAR(50)`): LOINC identifier (e.g. `4548-4` for HbA1c, `718-7` for Hemoglobin).
- **`display_name`** (`VARCHAR(150)`): Clinician-readable test name.
- **`value_numeric`** (`FLOAT`): Measured quantitative result.
- **`unit`** (`VARCHAR(30)`): Standard SI or clinical unit (`%`, `g/dL`, `mg/dL`, `U/L`).
- **`reference_low`** (`FLOAT`), **`reference_high`** (`FLOAT`): Valid normal physiological bounds.
- **`interpretation`** (`VARCHAR(30)`): `NORMAL`, `HIGH`, `LOW`, `CRITICAL`.

### 3.5 `allergy_intolerances`, `conditions` & `medication_requests` Tables
- Enforces relational referential integrity.
- Indexed by `patient_id` to enable sub-5-millisecond queries by the Prescription Safety Agent and Records Agent.

---

## 4. PostgreSQL vs. SQLite Production Deployment Strategy

1. **Local Development & Embedded Evaluation:**
   - Pre-configured with SQLite backend (`clinic_fhir.db`), zero configuration required.
   - Enforces thread safety with `check_same_thread=False` and atomic connection pooling.
2. **Enterprise Production Deployment (Railway, Render, AWS RDS):**
   - Provide standard `DATABASE_URL=postgresql://user:password@host:5432/dbname`.
   - SQLAlchemy automatically adopts high-concurrency connection pooling with `pool_pre_ping=True`.
   - Table schema generation is idempotent via `Base.metadata.create_all(bind=engine)`.

---
*End of Document: ER Diagram & Schema Specification.*
