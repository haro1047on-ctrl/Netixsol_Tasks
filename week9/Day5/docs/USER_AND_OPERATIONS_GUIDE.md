# City Care Clinics — User & Operations Manual
**Document ID:** CCC-OPS-USERGUIDE-2026  
**Audience:** Patients • Clinic Receptionists • Consulting Physicians • System Administrators  
**Deployment:** 5 Branches (Gulberg, DHA, Johar Town, Blue Area, F-8 Markaz)  
**Version:** v1.0.0 Production  

---

## 1. Patient User Guide (Patient Chat Portal & WhatsApp)

### 1.1. Accessing the Assistant
* **Web Portal:** Navigate to `http://localhost:8502` (or clinic web portal).
* **WhatsApp:** Message City Care Clinics verified business number (`+92-300-CITYCARE`).

### 1.2. How to Book an Appointment
1. **Start the Conversation:** Type in everyday Roman Urdu or English:
   - *"Assalam-o-Alaikum, mujhe bukhar aur galay mein dard hai."*
   - *"Need to see a paediatrician for my 2-year-old child."*
2. **Answer Clarifying Questions:** The assistant asks one brief question at a time:
   - How many days you have had the fever (`Duration`).
   - How severe the discomfort feels on a 1–10 scale (`Severity`).
   - Any other symptoms (cough, runny nose, body ache).
3. **Receive Instant Confirmation:**  
   Once completed, the system automatically matches the most qualified doctor, reserves the slot, and outputs:
   - Doctor Name and Specialty (e.g. Dr. Ayesha Malik, Paediatrics).
   - Confirmed Date and Time (e.g. October 15, 2026 at 17:30).
   - Clinic Branch and Queue Token Number (e.g. Token #4).
   - Consultation Fee in PKR.

### 1.3. What Happens in an Emergency?
If you report red-flag symptoms such as sudden chest pressure, facial drooping, slurred speech, heavy bleeding, or severe difficulty breathing:
* **The system will NOT keep you waiting for an appointment.**
* It immediately outputs red emergency instructions in UrduLish:
  - Calls **Rescue 1122** immediately.
  - Directs you to the nearest 24/7 hospital emergency room (e.g. Services Hospital or PIMS Emergency).
  - Reminds you that City Care Clinics is an outpatient facility without ICU equipment.

---

## 2. Receptionist & Front-Desk Guide

### 2.1. Handling Inbound Patients
1. **Verifying Appointment Tokens:**  
   When a patient arrives at the front desk, ask for their **Queue Token Number** or phone number.
2. **Checking Status in Database:**  
   The patient record will already display in the clinic management dashboard with status `BOOKED`.
3. **Marking Arrival:**  
   Click **Check-In / Arrived**. The system automatically notifies the doctor's room that the patient is in the waiting lounge.

### 2.2. Handling Walk-In Patients
* If an unbooked patient walks in, receptionists can open the web interface and enter their symptoms. The triage agent will instantly recommend the correct specialty and open slot, avoiding receptionist guesswork.

### 2.3. Rescheduling & Cancellations
* Patients can reschedule via WhatsApp up to 2 hours prior to the slot. The freed slot is immediately released back into the available pool for other waiting patients.

---

## 3. Consulting Physician Guide (Doctor Dashboard)

### 3.1. Logging into Doctor Dashboard
* Open `http://localhost:8501` on the clinic workstation.
* Select your Doctor ID (e.g. `DOC_0001 — Dr. Tariq Mahmood, General Medicine`).

### 3.2. Pre-Visit SOAP Brief Review
Before the patient enters the consultation room, review the automated **Pre-Visit Brief**:
* **Subjective:** Chief complaint, duration, severity, and associated symptoms collected by Intake Agent.
* **Objective (EHR Pre-Fetch):** Longitudinal lab results (HbA1c, CBC, Creatinine), recent vitals, and chronic conditions.
* **Assessment & Risk Flags:** Flagged allergies (e.g. Penicillin) and documented drug contraindications.
* **Plan:** Proposed medication regimen draft for physician verification.

### 3.3. Human-in-the-Loop (HITL) Queue Management
When an agent prepares a complex explanation (e.g. explaining abnormal lipid lab results to a patient):
1. The message appears under **Pending Reviews** on your dashboard.
2. Review the AI draft:
   - Click **Approve** to dispatch the message as-is.
   - Click **Edit** to modify the text before sending.
   - Click **Reject** if the patient must be called into the clinic for an in-person discussion.

---

## 4. System Maintenance & Administrator Guide

### 4.1. Starting the Services
To start all services locally or in a staging environment:
```powershell
# 1. Start FastAPI Gateway & MCP microservices
uvicorn week9.Day5.src.api_server:app --host 0.0.0.0 --port 8000 --reload

# 2. Start Doctor Dashboard
streamlit run week9/Day4/src/doctor_dashboard_app.py --server.port 8501

# 3. Start Patient Web Chat Portal
streamlit run week9/Day5/src/patient_web_app.py --server.port 8502
```

### 4.2. Running with Docker Compose
```bash
docker compose -f week9/Day5/docker/docker-compose.yml up -d --build
```

### 4.3. Automated Health Checks & Monitoring
* **Liveness Probe:** `GET /health` (Status 200 required).
* **Database Verification:** `python -c "import sqlite3; c = sqlite3.connect('week9/Day2/clinic_fhir.db'); print(c.execute('SELECT COUNT(*) FROM patients').fetchone())"`
* **Telemetry Logs:** Inspect `week9/Day4/src/data/telemetry_traces.json` for per-node execution times and error traces.

### 4.4. Routine Maintenance Schedule
1. **Daily:** Review telemetry traces for any unhandled node exceptions or slow tool executions.
2. **Weekly:** Backup `clinic_fhir.db` (or PostgreSQL dump) to secure, encrypted cold storage.
3. **Monthly:** Run the full 65-scenario evaluation suite (`python week9/Day5/run_day5.py`) to verify that no model drift or prompt degradation has occurred.
