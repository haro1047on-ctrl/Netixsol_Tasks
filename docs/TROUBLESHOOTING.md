# City Care Clinics — Operations & Troubleshooting Runbook

**Classification:** System Administration, Troubleshooting & Incident Response  
**Target Environment:** Windows 10/11, Python 3.13, PowerShell 7+, Docker  

---

## 1. Common Operational Issues & Diagnostic Resolutions

### 1.1 Python Import & Module Path Errors

#### Symptom
```text
ModuleNotFoundError: No module named 'supervisor_graph'
ModuleNotFoundError: No module named 'services'
```

#### Root Cause
Python's `sys.path` does not include the specific day's `src/` directory when scripts are invoked from the root repository directory.

#### Resolution
All entrypoint scripts (`api_server.py`, `patient_web_app.py`, `doctor_dashboard_app.py`, and test suites) now include dynamic parent path resolution:
```python
import sys
from pathlib import Path

# Automatically inject day source roots
DAY2_SRC = Path(__file__).resolve().parents[2] / "Day2" / "src"
DAY4_SRC = Path(__file__).resolve().parents[2] / "Day4" / "src"
DAY5_SRC = Path(__file__).resolve().parents[1]

for p in [str(DAY2_SRC), str(DAY4_SRC), str(DAY5_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)
```
Ensure that when executing manual commands or scripts, you run them with the project root as current working directory or set `PYTHONPATH=.`.

---

### 1.2 Port Conflicts on Windows

#### Symptom
```text
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000): only one usage of each socket address is normally permitted
```

#### Diagnostic & Resolution (PowerShell)
Find the process ID holding the port and terminate it:
```powershell
# 1. Identify PID using port 8000
netstat -ano | findstr :8000

# 2. Terminate the process by PID
taskkill /PID <PID> /F

# Repeat for Streamlit ports if necessary
netstat -ano | findstr :8501
netstat -ano | findstr :8502
```

---

### 1.3 SQLite Database Locks (`database is locked`)

#### Symptom
```text
sqlite3.OperationalError: database is locked
```

#### Root Cause
Under heavy concurrent load (e.g. simultaneous multi-turn chat and appointment writes), SQLite file locks can time out if another transaction is writing.

#### Resolution
1. **Configured Timeout:** The SQLite engine is initialized with `timeout=30.0` and `check_same_thread=False`.
2. **Production Recommendation:** For production deployments with concurrent users, switch from SQLite to PostgreSQL by updating `DATABASE_URL` in `.env`:
   ```bash
   DATABASE_URL=postgresql://clinic_admin:CityCareSecure2026!@localhost:5432/clinic_fhir
   ```

---

### 1.4 LLM Provider Offline / Quota Exceeded

#### Symptom
```text
groq.APIConnectionError: Error communicating with Groq API
```

#### System Behavior & Safe Mode
The assistant detects network failures or missing API keys and activates **Deterministic Offline Safe Mode**:
- Rule-based red-flag triage continues with 100% reliability.
- Appointment slot searches and bookings execute uninterrupted using direct database queries.
- Patient receives verified deterministic clinic responses rather than an unhandled application crash.

---

### 1.5 SMTP Email Delivery Failures

#### Symptom
Appointments are booked successfully, but no confirmation emails arrive.

#### Diagnosis
1. Inspect the notification audit log:
   ```bash
   curl -X GET http://localhost:8000/api/v1/notifications/audit
   ```
2. Check `status` and `provider_response`. If status is `FAILED`:
   - Verify SMTP host and port in `.env` (`SMTP_HOST`, `SMTP_PORT`).
   - If using Gmail, ensure you are using an **App Password** (16 characters) with 2-Factor Authentication enabled, NOT your primary Google account password.
   - For local development and testing, set `EMAIL_PROVIDER=test_mode` or configure a mock SMTP server.

---

## 2. Health Verification Checklist

Run these commands in PowerShell to verify system integrity:

```powershell
# 1. Run all 14 automated verification tests
pytest -v tests/

# 2. Test pre-flight API health check
curl http://localhost:8000/health

# 3. Test background reminder worker
curl -X POST http://localhost:8000/api/v1/notifications/reminders/process
```
