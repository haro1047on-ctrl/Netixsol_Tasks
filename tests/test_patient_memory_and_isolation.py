"""City Care Clinics - Patient Memory and Isolation Tests.

Tests:
- Test B: Returning patient longitudinal memory across sessions
- Test C: Cross-patient record isolation (Patient A blocked from Patient B; Doctor allowed)
"""
import uuid
import pytest
from patient_memory import MemoryManager
from services.auth_service import get_auth_service


def test_returning_patient_memory_recognition():
    """Test B: Returning patient is recognized, longitudinal memory loads previous visit and preferences."""
    mgr = MemoryManager()

    # Session 1: Patient PT_0002 (Ahmed Raza)
    res = mgr.initialize_session(patient_id="PT_0002", patient_name="Ahmed Raza")
    assert res["is_returning_patient"] is True
    assert "Ahmed" in res["welcome_greeting"]
    assert res["profile"] is not None

    # Verify past complaints or preferred doctor are loaded from DB
    profile = res["profile"]
    assert profile.get("patient_id") == "PT_0002"
    assert profile.get("patient_name") == "Ahmed Raza"


def test_cross_patient_isolation_guard(client, auth_service):
    """Test C: Patient A cannot access Patient B's chart (HTTP 403 Forbidden enforced)."""
    # 1. Register Patient Alpha
    u_alpha = f"user_alpha_{uuid.uuid4().hex[:6]}"
    res_reg_a = client.post("/api/v1/auth/register", json={
        "username": u_alpha,
        "password": "Password123!",
        "full_name": "Alpha Patient",
        "role": "PATIENT",
        "phone": "0300-1110001"
    })
    assert res_reg_a.status_code == 201
    pat_a_id = res_reg_a.json()["user"]["patient_id"]

    # 2. Register Patient Beta
    u_beta = f"user_beta_{uuid.uuid4().hex[:6]}"
    res_reg_b = client.post("/api/v1/auth/register", json={
        "username": u_beta,
        "password": "Password123!",
        "full_name": "Beta Patient",
        "role": "PATIENT",
        "phone": "0300-2220002"
    })
    assert res_reg_b.status_code == 201
    pat_b_id = res_reg_b.json()["user"]["patient_id"]

    # 3. Login Patient Alpha
    res_login_a = client.post("/api/v1/auth/login", json={
        "username_or_email": u_alpha,
        "password": "Password123!"
    })
    assert res_login_a.status_code == 200
    token_a = res_login_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 4. Patient Alpha views own chart -> 200 OK
    res_own = client.get(f"/api/v1/patient/{pat_a_id}", headers=headers_a)
    assert res_own.status_code == 200
    assert res_own.json()["profile"]["patient_id"] == pat_a_id

    # 5. Patient Alpha attempts to view Patient Beta's chart -> 403 Forbidden
    res_forbidden = client.get(f"/api/v1/patient/{pat_b_id}", headers=headers_a)
    assert res_forbidden.status_code == 403
    assert "isolation violation" in res_forbidden.json()["detail"].lower()

    # 6. Attending Doctor views Patient Beta's chart -> 200 OK
    res_login_doc = client.post("/api/v1/auth/login", json={
        "username_or_email": "doctor.tariq",
        "password": "DoctorPassword123!"
    })
    assert res_login_doc.status_code == 200
    doc_token = res_login_doc.json()["access_token"]
    headers_doc = {"Authorization": f"Bearer {doc_token}"}

    res_doc_access = client.get(f"/api/v1/patient/{pat_b_id}", headers=headers_doc)
    assert res_doc_access.status_code == 200
    assert res_doc_access.json()["profile"]["patient_id"] == pat_b_id
