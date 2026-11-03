# 📋 Requirements Traceability Matrix (RTM) — Week 7 & Week 8

**System:** RealEstate Hub Unified AI Voice Agent & ML Platform  
**Status:** Integrated Architecture  

This traceability matrix maps every capability from the Week 7 Voice Agent specification and the Week 8 ML/MLOps Capstone assignment to its existing implementation, architectural gap, planned module, test verification, and resolution status.

---

## Traceability Matrix

| Requirement | Week | Existing Implementation | Identified Gap | Planned Module | Dependencies | Verification Test | Status |
|---|---|---|---|---|---|---|---|
| **Urdu/UrduLish/English Speech Recognition (STT)** | Week 7 | Deepgram Nova-3 configured via Vapi | Paid cloud dependency; lacks local free-tier fallback | `speech/stt_service.py` | `faster-whisper`, `deepgram-sdk` | `test_stt_transcription` | `EXTEND` |
| **Bilingual Voice Synthesis (TTS)** | Week 7 | Vapi Elliot voice / ElevenLabs | Paid cloud dependency; no offline/free pipeline | `speech/tts_service.py` | `edge-tts`, `piper-tts` | `test_tts_audio_synthesis` | `EXTEND` |
| **Natural UrduLish Real Estate Sales Persona** | Week 7 | System prompts in `vapi_server.py` | Needs inclusion of ML valuation & lead guidance rules | `agents/prompts.py` | LLM API / Local Model | `test_persona_consistency` | `REFACTOR` |
| **Stateful Conversational Machine** | Week 7 | `state.py` & `graph.py` (9 nodes) | Runtime crash on `log_training_example`; missing ML state | `agents/state.py`, `agents/graph.py` | `langgraph`, `langchain` | `test_task1_state_initialization` | `REPAIR` |
| **Pakistani Entity & Budget Parsing** | Week 7 | Regex & LLM extraction in `intent_detection_node.py` | Robustness on mixed Urdu numerals & Lakh/Crore | `agents/intent_extractor.py` | Python standard library | `test_entity_extraction` | `KEEP` |
| **Verified SQL Property Search Tool** | Week 7 | `search_tools.py` (750 listings in `realestate_kb.db`) | Lacks real-time valuation variance comparison | `tools/search_tools.py` | SQLAlchemy, SQLite | `test_task3_property_search_tool` | `EXTEND` |
| **ChromaDB Locality & NOC RAG** | Week 7 | `rag_tools.py` & `rag_node.py` | Needs dynamic metadata filtering per society | `rag/rag_engine.py` | `chromadb`, `sentence-transformers` | `test_rag_retrieval_grounding` | `KEEP` |
| **Invariant 1: Anti-Double-Booking** | Week 7 | `availability_tools.py` (9 AM-7 PM) | None; works as specified | `tools/availability_tools.py` | SQLite CRM tables | `test_task4_invariant1_never_book_unavailable` | `KEEP` |
| **Invariant 2: Zero Hallucinated Listings** | Week 7 | Database check in `recommendation_node.py` | None; works as specified | `agents/recommendation.py` | SQLite Property table | `test_task4_invariant2_never_recommend_unavailable` | `KEEP` |
| **Invariant 3: Proactive Clarification** | Week 7 | `clarification_node.py` | Broke due to `TypeError` in intent detection | `agents/clarification.py` | LangGraph routing | `test_task4_invariant3_ask_clarification` | `REPAIR` |
| **Calendar Sync & RFC 5545 .ics** | Week 7 | `calendar_tools.py` | Real Google Calendar OAuth requires local mock fallback | `integrations/calendar.py` | Python `urllib` / mock | `test_task3_calendar_tool` | `KEEP` |
| **CRM Lead & Visit Persistence** | Week 7 | `crm_tools.py` | Missing conversion score & persona columns | `integrations/crm.py` | SQLAlchemy | `test_task3_crm_tool` | `EXTEND` |
| **HTML Email Follow-up Dispatcher** | Week 7 | `email_tools.py` | SMTP requires dev mock adapter | `integrations/email.py` | Python `smtplib` | `test_task3_email_tool` | `KEEP` |
| **Security Guardrails & Prompt Shield** | Week 7 | `security_guardrails.py` in Day 6 | Namespace collision with Day 5 `security/` | `security/guardrails.py` | Regex, Safety rules | `test_security_guardrails` | `REPAIR` |
| **46 Multi-Turn Conversation Eval** | Week 7 | `eval_suite/test_conversations.json` | Not runnable from root CLI | `evaluation/eval_runner.py` | `pytest`, `benchmark_engine` | `test_full_conversation_eval` | `EXTEND` |
| **Production Telemetry (/metrics)** | Week 7 | `metrics_collector.py` (Prometheus) | Separate server from Week 8 API | `monitoring/telemetry.py` | `prometheus_client` | `test_metrics_endpoint` | `EXTEND` |
| **Property Valuation Model (Regression)** | Week 8 | CatBoost Regressor ($R^2=0.988$) in `Day2` | Served as standalone script, not wired into voice turns | `property/valuation_engine.py` | `catboost`, `scikit-learn` | `test_property_valuation_accuracy` | `EXTEND` |
| **Quantile Uncertainty Bands (P10-P90)** | Week 8 | LightGBM Quantile models in `Day2` | Isolated from voice agent responses | `property/valuation_engine.py` | `lightgbm` | `test_quantile_uncertainty_bands` | `EXTEND` |
| **Automated Valuation Verdicts** | Week 8 | Pricing verdict logic in `Day2` | Quoted prices in PKR not spoken naturally by voice agent | `property/valuation_engine.py` | Domain heuristics | `test_market_verdicts` | `EXTEND` |
| **Inbound Lead Scoring Classifier** | Week 8 | LightGBM Classifier (PR-AUC $0.562$) | Scored offline or via separate API | `leads/scoring_engine.py` | `lightgbm`, `joblib` | `test_lead_scoring_performance` | `EXTEND` |
| **Class Imbalance Calibration** | Week 8 | SMOTE / Class Weights in `Day3` | None; weights verified | `leads/scoring_engine.py` | `scikit-learn` | `test_model_fairness` | `KEEP` |
| **K-Means Customer Personas (k=4)** | Week 8 | K-Means clustering artifacts in `Day3` | Not saved into CRM during phone booking | `leads/persona_engine.py` | `scikit-learn` | `test_persona_clustering` | `EXTEND` |
| **SHAP Explainability in UrduLish** | Week 8 | `shap_explainers.py` in `Day3` | Batch table was slow (repaired with `explain=False`) | `leads/shap_engine.py` | `shap`, `numpy` | `test_shap_explainability_urdulish` | `KEEP` |
| **FastAPI Model Serving Suite** | Week 8 | `main.py` in `Day4` (7 REST endpoints) | Separate port from voice server | `api/ml_routes.py` | `fastapi`, `pydantic` | `test_fastapi_endpoints` | `EXTEND` |
| **LangGraph 5-Tool AI Assistant** | Week 8 | `assistant.py` in `Day4` | Separate assistant instance from Week 7 voice agent | `agents/assistant_tools.py` | `langgraph` | `test_langgraph_assistant_tools` | `EXTEND` |
| **Bi-directional Voice Webhook** | Week 8 | `webhook.py` in `Day4` | Simulates call ingestion; needs live pipeline binding | `api/webhook_routes.py` | `fastapi` | `test_voice_webhook_integration` | `EXTEND` |
| **Streamlit Executive Dashboard** | Week 8 | `app_dashboard.py` in `Day4` | Repaired NumPy 2.x `isnan` bug; runs smoothly | `ui/dashboard.py` | `streamlit` | `test_dashboard_rendering` | `KEEP` |
| **Evidently AI Data & Drift Monitor** | Week 8 | `drift_monitor.py` in `Day5` | Isolated in Day 5 folder | `monitoring/drift_service.py` | `evidently` | `test_drift_monitoring` | `EXTEND` |
| **Automated Retraining Pipeline** | Week 8 | `retrain_pipeline.py` in `Day5` | Rollback and champion promotion gate verified | `mlops/retrain_service.py` | `joblib`, `scikit-learn` | `test_retraining_promotion_gate` | `EXTEND` |
| **Production Containerization** | Week 7+8 | Dockerfiles in `day6` and `week8/Day5` | Two conflicting docker-compose setups | `docker/` | Docker, Compose | `test_docker_compose_build` | `REFACTOR` |
