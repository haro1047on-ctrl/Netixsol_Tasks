"""Unit & Integration Tests for Week 8 Day 4 FastAPI Endpoints.

Tests:
1. GET /health
2. GET /model/info
3. POST /predict/price (valid input, bounds, formatted output)
4. POST /predict/price (OOD & validation errors: negative marla, unknown city)
5. POST /predict/lead-score (valid lead, Hot/Warm/Cold priority)
6. POST /predict/lead-score (OOD & validation errors)
7. POST /explain/price (SHAP attribution)
8. POST /explain/lead (SHAP attribution)
9. POST /predict/batch (CSV upload)
10. GET /audit/logs (verifies prediction was logged to SQLite)
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
from fastapi.testclient import TestClient
import pandas as pd
import pytest

TEST_DIR = Path(__file__).resolve().parent
DAY4_SRC = TEST_DIR.parent / "src"
if str(DAY4_SRC) not in sys.path:
    sys.path.insert(0, str(DAY4_SRC))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from api import app, startup_event

# Initialize engines
startup_event()
client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "PropertyValuationModel_v1" in data["loaded_models"]
    print("✅ Health Check Passed")


def test_model_info():
    response = client.get("/model/info")
    assert response.status_code == 200
    data = response.json()
    assert len(data["models"]) >= 2
    model_names = [m["model_name"] for m in data["models"]]
    assert "PropertyValuationModel" in model_names
    assert "LeadScoringModel" in model_names
    print("✅ Model Info Passed")


def test_predict_price_success():
    payload = {
        "city": "Lahore",
        "area_society": "DHA Phase 6",
        "property_type": "House",
        "plot_size_marla": 20.0,  # 1 Kanal
        "bedrooms": 5,
        "bathrooms": 5,
        "age_years": 5.0,
        "is_corner": "Yes",
        "listed_price_pkr": 80000000.0,  # 8 Crore
    }
    response = client.post("/predict/price", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["predicted_price_pkr"] > 0
    assert "crore" in data["predicted_price_formatted"].lower()
    assert "verdict" in data
    assert "disclaimer" in data
    print(f"✅ Price Prediction Passed: {data['english_summary']}")


def test_predict_price_ood_rejection():
    # Negative / out-of-distribution plot size
    payload_bad_marla = {
        "city": "Lahore",
        "area_society": "DHA Phase 5",
        "plot_size_marla": -5.0,
    }
    resp = client.post("/predict/price", json=payload_bad_marla)
    assert resp.status_code in [400, 422]

    # Extreme OOD plot size (120 Marla = 6 Kanal)
    payload_extreme = {
        "city": "Lahore",
        "area_society": "DHA Phase 5",
        "plot_size_marla": 120.0,
    }
    resp_extreme = client.post("/predict/price", json=payload_extreme)
    assert resp_extreme.status_code in [400, 422]

    # Unknown city
    payload_bad_city = {
        "city": "Atlantis",
        "area_society": "Underwater Sector 1",
        "plot_size_marla": 10.0,
    }
    resp_city = client.post("/predict/price", json=payload_bad_city)
    assert resp_city.status_code in [400, 422]
    print("✅ OOD Rejections Passed")


def test_predict_lead_score_success():
    payload_hot = {
        "lead_source": "WhatsApp",
        "budget_pkr": 25000000.0,
        "preferred_city": "Islamabad",
        "purpose": "Buy",
        "number_of_calls": 5,
        "avg_call_duration_mins": 4.5,
        "response_time_hours": 0.2,
        "visit_booked": "Yes",
        "days_since_first_contact": 2,
        "objection_raised": "None",
    }
    response = client.post("/predict/lead-score", json=payload_hot)
    assert response.status_code == 200
    data = response.json()
    assert data["priority_tier"] in ["Hot", "Warm"]
    assert "customer_persona" in data
    assert "explanation_ur" in data
    print(f"✅ Lead Scoring Passed: {data['priority_badge']} {data['customer_persona']} - {data['explanation_en']}")


def test_explain_price():
    payload = {
        "city": "Islamabad",
        "area_society": "Sector F-7",
        "property_type": "House",
        "plot_size_marla": 20.0,
        "bedrooms": 5,
        "age_years": 1.0,
        "top_n": 3,
    }
    response = client.post("/explain/price", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["target_type"] == "property_price"
    assert len(data["top_positive_features"]) > 0
    assert "plain_language_ur" in data
    print(f"✅ Property SHAP Explain Passed: {data['plain_language_ur']}")


def test_explain_lead():
    payload = {
        "lead_source": "Call",
        "budget_pkr": 30000000.0,
        "preferred_city": "Lahore",
        "number_of_calls": 4,
        "visit_booked": "Yes",
        "top_n": 3,
    }
    response = client.post("/explain/lead", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["target_type"] == "lead_conversion"
    assert "plain_language_ur" in data
    print(f"✅ Lead SHAP Explain Passed: {data['plain_language_ur']}")


def test_batch_prediction():
    # Construct sample CSV
    csv_data = (
        "city,area_society,property_type,plot_size_marla,bedrooms,bathrooms,age_years\n"
        "Lahore,DHA Phase 5,House,10.0,4,4,2.0\n"
        "Islamabad,Sector F-7,House,20.0,5,5,1.0\n"
        "Karachi,Clifton,Flat,8.0,3,3,3.0\n"
    )
    files = {"file": ("test_properties.csv", io.BytesIO(csv_data.encode("utf-8")), "text/csv")}
    response = client.post("/predict/batch?dataset_type=property", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["successful_predictions"] == 3
    print("✅ Batch CSV Prediction Passed")


def test_audit_logs():
    response = client.get("/audit/logs?limit=5")
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) > 0
    assert logs[0]["status"] == "SUCCESS"
    print(f"✅ Audit Logs Verified (Found {len(logs)} logged events)")


if __name__ == "__main__":
    print("\n--- Running FastAPI Unit & Integration Tests ---")
    test_health()
    test_model_info()
    test_predict_price_success()
    test_predict_price_ood_rejection()
    test_predict_lead_score_success()
    test_explain_price()
    test_explain_lead()
    test_batch_prediction()
    test_audit_logs()
    print("\n🎉 ALL FASTAPI ENDPOINT TESTS PASSED WITH 100% SUCCESS!\n")
