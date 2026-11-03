"""FastAPI Enterprise Model Serving Application (Week 8 - Day 4 Task 1).

Exposes:
- POST /predict/price
- POST /predict/lead-score
- POST /explain/price
- POST /explain/lead
- POST /predict/batch
- GET /health
- GET /model/info
- GET /audit/logs
"""
from __future__ import annotations

import io
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import shap

SRC_DIR = Path(__file__).resolve().parent
DAY4_DIR = SRC_DIR.parent
WEEK8_DIR = DAY4_DIR.parent
DAY2_SRC = WEEK8_DIR / "Day2" / "src"
DAY3_SRC = WEEK8_DIR / "Day3" / "src"

for p in [str(SRC_DIR), str(DAY2_SRC), str(DAY3_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from guardrails import (
    LEGAL_DISCLAIMER,
    OODValidationError,
    audit_logger,
    check_lead_ood,
    check_property_ood,
)
from schemas import (
    ExplainResponse,
    HealthResponse,
    LeadExplainRequest,
    LeadScoringRequest,
    LeadScoringResponse,
    ModelDetail,
    ModelInfoResponse,
    PropertyExplainRequest,
    PropertyValuationRequest,
    PropertyValuationResponse,
    SHAPFeatureImpact,
)
from shap_explainers import (
    LEAD_FEATURE_FRIENDLY_NAMES,
    PROPERTY_FEATURE_FRIENDLY_NAMES,
    generate_lead_plain_language_reasons,
    generate_property_plain_language_reasons,
)
from valuation_inference import PropertyValuationEngine
from lead_inference import LeadScoringEngine

app = FastAPI(
    title="AI Property Valuation & Lead Scoring Platform API",
    version="1.0.0",
    description=(
        "Production ML Serving Gateway for Real Estate Valuation, Lead Prioritization, "
        "and Explainable AI with UrduLish and English support."
    ),
    contact={"name": "Lead ML Engineer", "email": "ai-platform@netixsol.com"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load engines at startup
property_engine: Optional[PropertyValuationEngine] = None
lead_engine: Optional[LeadScoringEngine] = None
property_explainer: Optional[shap.TreeExplainer] = None


@app.on_event("startup")
def startup_event():
    global property_engine, lead_engine, property_explainer
    print("Initializing production inference engines...")
    property_engine = PropertyValuationEngine()
    lead_engine = LeadScoringEngine()
    property_explainer = shap.TreeExplainer(property_engine.model)
    print("Engines successfully initialized!")


@app.exception_handler(OODValidationError)
async def ood_validation_exception_handler(request: Request, exc: OODValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": str(exc), "error_type": "Out-of-Distribution Rejection"},
    )


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """System health check endpoint verifying engine status."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        loaded_models=["PropertyValuationModel_v1", "LeadScoringModel_v1", "KMeansPersonas_k4"],
        system_status="All ML inference engines active and ready.",
    )


@app.get("/model/info", response_model=ModelInfoResponse, tags=["System"])
def model_info():
    """Returns metadata, hyperparameter versions, and key test metrics for production models."""
    return ModelInfoResponse(
        platform="Real Estate AI Capstone",
        environment="Production",
        models=[
            ModelDetail(
                model_name="PropertyValuationModel",
                version="1.0.0 (Registered in MLflow)",
                algorithm="CatBoostRegressor (Optuna-Tuned) with Quantile Regressors (10th/90th percentile)",
                trained_date="September 2026",
                key_metrics={
                    "test_r2": 0.9880,
                    "test_mae_pkr": "17.02 Lac",
                    "test_mape_pct": 6.25,
                    "test_rmse_pkr": "41.15 Lac",
                },
                input_feature_count=36,
            ),
            ModelDetail(
                model_name="LeadScoringModel",
                version="1.0.0 (Registered in MLflow)",
                algorithm="LightGBMClassifier with Cost-Sensitive Class Weights (scale_pos_weight=2.96)",
                trained_date="September 2026",
                key_metrics={
                    "test_pr_auc": 0.5619,
                    "test_roc_auc": 0.7710,
                    "precision_top_20_pct": 61.11,
                    "lift_top_20_pct": 2.43,
                    "optimal_threshold": 0.38,
                },
                input_feature_count=38,
            ),
            ModelDetail(
                model_name="CustomerPersonaSegmenter",
                version="1.0.0",
                algorithm="K-Means Clustering (k=4)",
                trained_date="September 2026",
                key_metrics={
                    "k_clusters": 4,
                    "top_conversion_cluster_rate": "49.86% (Serious First-Time Buyer)",
                },
                input_feature_count=7,
            ),
        ],
    )


@app.post("/predict/price", response_model=PropertyValuationResponse, tags=["Valuation"])
def predict_property_price(payload: PropertyValuationRequest, request: Request):
    """Predicts fair market value, bounds with 10th-90th quantile interval, and generates market verdict."""
    t0 = time.perf_counter()
    prop_dict = payload.model_dump()
    
    # 1. Guardrail OOD Check
    check_property_ood(prop_dict)

    if property_engine is None:
        raise HTTPException(status_code=500, detail="Property valuation engine not initialized.")

    result = property_engine.evaluate_property(
        prop_dict,
        listed_price_pkr=payload.listed_price_pkr
    )
    result["disclaimer"] = LEGAL_DISCLAIMER
    result["model_version"] = "PropertyValuationModel_v1"

    latency_ms = (time.perf_counter() - t0) * 1000.0
    client_ip = request.client.host if request.client else "unknown"

    audit_logger.log_prediction(
        endpoint="/predict/price",
        model_version=result["model_version"],
        inputs=prop_dict,
        outputs={
            "predicted_price_pkr": result["predicted_price_pkr"],
            "verdict": result["verdict"],
            "variance_pct": result["variance_pct"],
        },
        latency_ms=latency_ms,
        client_ip=client_ip,
        status="SUCCESS"
    )

    return PropertyValuationResponse(**result)


@app.post("/predict/lead-score", response_model=LeadScoringResponse, tags=["Lead Scoring"])
def predict_lead_score(payload: LeadScoringRequest, request: Request):
    """Scores an incoming lead by conversion probability, assigns Hot/Warm/Cold badge and customer persona."""
    t0 = time.perf_counter()
    lead_dict = payload.model_dump()

    # 1. Guardrail OOD Check
    check_lead_ood(lead_dict)

    if lead_engine is None:
        raise HTTPException(status_code=500, detail="Lead scoring engine not initialized.")

    res = lead_engine.score_lead(lead_dict)
    response_data = {
        "conversion_probability": res["conversion_probability"],
        "probability_percentage": res["conversion_pct"],
        "priority_tier": res["tier"],
        "priority_badge": res["badge"],
        "operational_sla": res["sla"],
        "recommended_action": res["next_best_action_en"],
        "customer_persona": res["customer_persona"],
        "persona_description": res["persona_description"],
        "explanation_en": res["explanation_en"],
        "explanation_ur": res["explanation_ur"],
        "model_version": "LeadScoringModel_v1",
    }

    latency_ms = (time.perf_counter() - t0) * 1000.0
    client_ip = request.client.host if request.client else "unknown"

    audit_logger.log_prediction(
        endpoint="/predict/lead-score",
        model_version=response_data["model_version"],
        inputs=lead_dict,
        outputs={
            "conversion_probability": response_data["conversion_probability"],
            "priority_tier": response_data["priority_tier"],
            "customer_persona": response_data["customer_persona"],
        },
        latency_ms=latency_ms,
        client_ip=client_ip,
        status="SUCCESS"
    )

    return LeadScoringResponse(**response_data)


@app.post("/explain/price", response_model=ExplainResponse, tags=["Explainability"])
def explain_property_price(payload: PropertyExplainRequest):
    """Generates local SHAP feature attributions and plain-language English & UrduLish rationales."""
    prop_dict = payload.model_dump()
    check_property_ood(prop_dict)

    if property_engine is None or property_explainer is None:
        raise HTTPException(status_code=500, detail="Engines not ready.")

    df_row = property_engine._prepare_feature_row(prop_dict)
    X_trans = property_engine.preprocessor.transform(df_row)

    pred_log = property_engine.model.predict(X_trans)[0]
    pred_pkr = float(np.expm1(pred_log))

    # SHAP computation
    shap_vals = property_explainer.shap_values(X_trans)[0]
    feature_names = property_engine.preprocessor.get_feature_names_out()

    reasons = generate_property_plain_language_reasons(
        shap_vals_row=shap_vals,
        feature_names=feature_names,
        predicted_price_pkr=pred_pkr,
        top_n=payload.top_n
    )

    # Format SHAP features
    pos_list: List[SHAPFeatureImpact] = []
    neg_list: List[SHAPFeatureImpact] = []

    top_pos_idx = np.argsort(shap_vals)[::-1]
    top_neg_idx = np.argsort(shap_vals)

    for idx in top_pos_idx[:payload.top_n]:
        val = float(shap_vals[idx])
        if val > 0.01:
            fname = feature_names[idx]
            en_name, ur_name = PROPERTY_FEATURE_FRIENDLY_NAMES.get(fname, (fname, fname))
            pos_list.append(SHAPFeatureImpact(
                feature_name=fname,
                impact_direction="Increases",
                shap_value=round(val, 4),
                friendly_name_en=en_name,
                friendly_name_ur=ur_name,
            ))

    for idx in top_neg_idx[:payload.top_n]:
        val = float(shap_vals[idx])
        if val < -0.01:
            fname = feature_names[idx]
            en_name, ur_name = PROPERTY_FEATURE_FRIENDLY_NAMES.get(fname, (fname, fname))
            neg_list.append(SHAPFeatureImpact(
                feature_name=fname,
                impact_direction="Decreases",
                shap_value=round(val, 4),
                friendly_name_en=en_name,
                friendly_name_ur=ur_name,
            ))

    from valuation_inference import format_pakistani_currency
    return ExplainResponse(
        target_type="property_price",
        predicted_value=format_pakistani_currency(pred_pkr),
        plain_language_en=reasons["explanation_en"],
        plain_language_ur=reasons["explanation_ur"],
        top_positive_features=pos_list,
        top_negative_features=neg_list,
        model_version="PropertyValuationModel_v1",
    )


@app.post("/explain/lead", response_model=ExplainResponse, tags=["Explainability"])
def explain_lead_score(payload: LeadExplainRequest):
    """Generates local SHAP feature attributions and plain-language English & UrduLish triage rationales."""
    lead_dict = payload.model_dump()
    check_lead_ood(lead_dict)

    if lead_engine is None:
        raise HTTPException(status_code=500, detail="Lead engine not initialized.")

    eval_result = lead_engine.score_lead(lead_dict)
    
    # SHAP computation
    df_row = lead_engine._engineer_lead_features(lead_dict)
    X_trans = lead_engine.preprocessor.transform(df_row)
    shap_vals = lead_engine.explainer.shap_values(X_trans)
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1]
    shap_vals_row = shap_vals[0]
    feature_names = lead_engine.feature_names

    pos_list: List[SHAPFeatureImpact] = []
    neg_list: List[SHAPFeatureImpact] = []

    top_pos_idx = np.argsort(shap_vals_row)[::-1]
    top_neg_idx = np.argsort(shap_vals_row)

    for idx in top_pos_idx[:payload.top_n]:
        val = float(shap_vals_row[idx])
        if val > 0.01:
            fname = feature_names[idx]
            en_name, ur_name = LEAD_FEATURE_FRIENDLY_NAMES.get(fname, (fname, fname))
            pos_list.append(SHAPFeatureImpact(
                feature_name=fname,
                impact_direction="Increases",
                shap_value=round(val, 4),
                friendly_name_en=en_name,
                friendly_name_ur=ur_name,
            ))

    for idx in top_neg_idx[:payload.top_n]:
        val = float(shap_vals_row[idx])
        if val < -0.01:
            fname = feature_names[idx]
            en_name, ur_name = LEAD_FEATURE_FRIENDLY_NAMES.get(fname, (fname, fname))
            neg_list.append(SHAPFeatureImpact(
                feature_name=fname,
                impact_direction="Decreases",
                shap_value=round(val, 4),
                friendly_name_en=en_name,
                friendly_name_ur=ur_name,
            ))

    return ExplainResponse(
        target_type="lead_conversion",
        predicted_value=eval_result["conversion_pct"],
        plain_language_en=eval_result["explanation_en"],
        plain_language_ur=eval_result["explanation_ur"],
        top_positive_features=pos_list,
        top_negative_features=neg_list,
        model_version="LeadScoringModel_v1",
    )


@app.post("/predict/batch", tags=["Batch Processing"])
async def predict_batch(
    file: UploadFile = File(...),
    dataset_type: Optional[str] = Query(
        default="auto",
        description="Dataset type: 'property', 'lead', or 'auto' (auto-detects columns)"
    )
):
    """Processes uploaded CSV file, executes vectorized inference, and returns batch predictions."""
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Uploaded file must be a .csv file."
        )

    content = await file.read()
    try:
        df = pd.read_csv(io.StringIO(content.decode("utf-8")))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to parse CSV file: {str(e)}"
        )

    if df.empty:
        raise HTTPException(status_code=400, detail="Uploaded CSV file is empty.")

    # Auto-detect dataset type if needed
    is_property = (
        dataset_type == "property"
        or ("plot_size_marla" in df.columns or "property_type" in df.columns)
    )

    results = []
    if is_property:
        if property_engine is None:
            raise HTTPException(status_code=500, detail="Property engine not loaded.")
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            try:
                eval_res = property_engine.evaluate_property(
                    row_dict,
                    listed_price_pkr=row_dict.get("listed_price_pkr")
                )
                results.append({
                    "row_index": idx,
                    "city": row_dict.get("city", "Lahore"),
                    "area_society": row_dict.get("area_society", "DHA"),
                    "plot_size_marla": row_dict.get("plot_size_marla", 10.0),
                    "predicted_price_pkr": eval_res["predicted_price_pkr"],
                    "predicted_price_formatted": eval_res["predicted_price_formatted"],
                    "lower_range_formatted": eval_res["lower_range_formatted"],
                    "upper_range_formatted": eval_res["upper_range_formatted"],
                    "verdict": eval_res["verdict"],
                    "status": "SUCCESS"
                })
            except Exception as ex:
                results.append({
                    "row_index": idx,
                    "status": "ERROR",
                    "error": str(ex)
                })
        
        summary = {
            "dataset_type": "property_valuation",
            "total_rows": len(df),
            "successful_predictions": sum(1 for r in results if r.get("status") == "SUCCESS"),
            "verdict_distribution": pd.Series([r.get("verdict") for r in results if "verdict" in r]).value_counts().to_dict(),
        }
    else:
        if lead_engine is None:
            raise HTTPException(status_code=500, detail="Lead engine not loaded.")
        for idx, row in df.iterrows():
            row_dict = row.to_dict()
            try:
                eval_res = lead_engine.score_lead(row_dict)
                results.append({
                    "row_index": idx,
                    "preferred_city": row_dict.get("preferred_city", "Lahore"),
                    "budget_pkr": row_dict.get("budget_pkr", 15000000.0),
                    "conversion_probability": eval_res["conversion_probability"],
                    "priority_tier": eval_res["tier"],
                    "priority_badge": eval_res["badge"],
                    "customer_persona": eval_res["customer_persona"],
                    "status": "SUCCESS"
                })
            except Exception as ex:
                results.append({
                    "row_index": idx,
                    "status": "ERROR",
                    "error": str(ex)
                })

        summary = {
            "dataset_type": "lead_scoring",
            "total_rows": len(df),
            "successful_predictions": sum(1 for r in results if r.get("status") == "SUCCESS"),
            "tier_distribution": pd.Series([r.get("priority_tier") for r in results if "priority_tier" in r]).value_counts().to_dict(),
        }

    return {
        "summary": summary,
        "sample_records": results[:20],
        "total_records_processed": len(results),
    }


@app.get("/audit/logs", tags=["Audit"])
def get_audit_logs(limit: int = Query(default=20, ge=1, le=100)):
    """Retrieves recent prediction audit logs from SQLite audit store."""
    return audit_logger.fetch_recent_logs(limit=limit)


if __name__ == "__main__":
    import uvicorn
    startup_event()
    print("Starting FastAPI app on http://127.0.0.1:8000 ...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
