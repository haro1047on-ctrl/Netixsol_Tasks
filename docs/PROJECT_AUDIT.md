# 🔍 RealEstate Hub AI Voice Agent — Project Audit & Diagnostic Report

**Generated:** September 30, 2026  
**Auditor:** Senior AI Architect & Systems Engineer  
**Scope:** Complete repository inspection of Week 7 (`week7-RE_Agent`) and Week 8 (`week8`) assets, identifying functional baselines, breaking defects, architectural fragmentation, and repair requirements.

---

## 1. Executive Summary

RealEstate Hub is an AI-powered voice and consultation platform tailored for Pakistani real estate. Over Weeks 7 and 8, two substantial but currently disconnected codebases were built:

1. **Week 7 (`week7-RE_Agent`)**: A telephony-connected voice agent using Vapi, Deepgram Nova-3 (Urdu), and LangGraph. It incorporates a 9-node state graph, 6 business tools, ChromaDB RAG, and an automated Day 6 evaluation/security suite.
2. **Week 8 (`week8`)**: A Machine Learning & MLOps platform featuring CatBoost property valuation ($R^2=0.988$) with quantile uncertainty bands, a LightGBM lead scoring and customer persona engine (PR-AUC $0.562$), SHAP explainability in UrduLish, and an Evidently AI drift monitoring pipeline.

### Audit Verdict
The project contains high-value domain assets (750 verified Pakistani property listings, 20 locality FAQs, 150 real lead conversion traces, 46 comprehensive test dialogues, and robust ML models). However, **the agent cannot function as a unified production system in its current state** due to:
- A fatal runtime crash in `intent_detection_node.py` breaking conversational turns.
- Python namespace collisions between Day 5 and Day 6 `security` modules.
- Hard telephony dependencies on paid Vapi/Deepgram services with no local free-tier speech fallback.
- An architectural split between Week 7 (voice orchestration) and Week 8 (valuation & lead scoring), where Week 8 endpoints are served separately without live bi-directional integration into the primary LangGraph graph.

---

## 2. Root Cause Analysis of Existing Agent Failures

Through forensic execution of the test suites (`test_day5_agent.py` and `run_day6.py`), we uncovered the exact runtime failure mechanisms:

### Root Cause 1: Signature Mismatch in Continual Learning Hook (Fatal Runtime Crash)
- **Location**: `week7-RE_Agent/day5-langgraph-agent/nodes/intent_detection_node.py` (Line 991).
- **Failure**:
  ```python
  TypeError: log_training_example() got an unexpected keyword argument 'clarification_needed'
  ```
- **Analysis**: At the end of every intent detection turn, `intent_detection_node.py` calls `log_training_example(raw_input, intent, session_id=..., clarification_needed=..., source="rule_engine")`. However, `learning/dataset.py` defines `log_training_example` with only `(user_text, true_intent, session_id, confidence=1.0)`.
- **Impact**: Any conversational turn that attempts to log training data crashes the entire LangGraph execution loop immediately after intent detection. 6 out of 15 automated test cases in `test_day5_agent.py` fail immediately.

### Root Cause 2: Python Module Namespace Collision (Day 5 vs. Day 6)
- **Location**: `week7-RE_Agent/day6-evaluation-security/deployment/health_check.py` and `prod_server.py`.
- **Failure**:
  ```python
  ModuleNotFoundError: No module named 'security.security_guardrails'
  ```
- **Analysis**: Both `day5-langgraph-agent` and `day6-evaluation-security` define a top-level directory named `security/`. When both directories are present in `sys.path`, Python resolves `security` to the Day 5 folder (which contains `auth.py`, `rate_limiter.py`), shadowing Day 6's `security_guardrails.py`.
- **Impact**: Health checks fail, and production security scans cannot execute without manual path hacking.

### Root Cause 3: Incomplete Telephony & Speech Decoupling
- **Location**: `week7-RE_Agent/day5-langgraph-agent/vapi_server.py`.
- **Analysis**: The existing agent relies exclusively on an active Vapi account, a Deepgram private API key, and an open `ngrok` tunnel. If the user runs the agent locally without active cloud telephony credits or an active public URL, the agent cannot receive voice input or output synthesized speech.
- **Impact**: Violates the "Free-First" constraint. A local microphone/speaker loop and local STT (Faster-Whisper) / TTS (Edge-TTS / Piper) adapter are missing.

### Root Cause 4: NumPy 2.x Type Incompatibility in Scikit-Learn Encoders
- **Location**: `week8/Day3/src/lead_inference.py`.
- **Failure**:
  ```python
  TypeError: ufunc 'isnan' not supported for the input types
  ```
- **Analysis**: Missing values (`float('nan')`) inside categorical columns loaded from CSV caused pandas to assign numeric dtypes, forcing Scikit-Learn's `OneHotEncoder` into a numeric branch that ran `np.isnan()` on string category arrays.
- **Status**: Repaired in `lead_inference.py` and `app_dashboard.py`, but needs unified packaging into the root agent.

### Root Cause 5: Week 7 & Week 8 Structural Disconnection
- **Analysis**: Week 8 developed standalone ML models (CatBoost, LightGBM, Quantiles) and a LangGraph assistant (`week8/Day4/src/assistant.py`), but did not merge these capabilities into the main 9-node Week 7 telephony state machine (`week7-RE_Agent/day5-langgraph-agent/graph.py`).
- **Impact**: Callers on the voice agent cannot trigger real-time ML property valuations with confidence intervals, nor does the voice agent store ML lead scores directly in the central CRM database.

---

## 3. Component & File Classification

Every file in the repository has been audited and classified according to the lifecycle taxonomy:

| Directory / File | Status | Technical Rationale & Action Plan |
|---|---|---|
| **Week 7: Voice Agent Core** | | |
| `week7-RE_Agent/day5-langgraph-agent/graph.py` | `REFACTOR` | Core 9-node state machine. Keep routing logic; integrate Week 8 ML valuation and lead scoring tools directly into graph nodes. |
| `week7-RE_Agent/day5-langgraph-agent/state.py` | `EXTEND` | Central `AgentState`. Add valuation bands, lead conversion probability, persona, and ML explanation fields. |
| `week7-RE_Agent/day5-langgraph-agent/config.py` | `REFACTOR` | Consolidate path resolution, DB connections, and environment variables into a single unified root configuration. |
| `week7-RE_Agent/day5-langgraph-agent/vapi_server.py` | `EXTEND` | Fast-streaming OpenAI SSE server for Vapi. Add local audio WebSocket streaming and local speech adapters. |
| `week7-RE_Agent/day5-langgraph-agent/nodes/intent_detection_node.py` | `REPAIR` | Fix `log_training_example` keyword arguments; add valuation and scoring intent triggers. |
| `week7-RE_Agent/day5-langgraph-agent/nodes/recommendation_node.py` | `EXTEND` | Enrich listing recommendations with ML fair-market pricing checks and quantile flags. |
| `week7-RE_Agent/day5-langgraph-agent/nodes/booking_node.py` | `EXTEND` | Enrich booking logic to compute lead scores upon visit confirmation and assign priority SLA. |
| `week7-RE_Agent/day5-langgraph-agent/nodes/rag_node.py` | `KEEP` | Grounded ChromaDB retrieval for locality bylaws, NOCs, and real estate FAQs. |
| `week7-RE_Agent/day5-langgraph-agent/tools/search_tools.py` | `KEEP` | Parameterized SQL query tool over 750 verified listings. |
| `week7-RE_Agent/day5-langgraph-agent/tools/availability_tools.py` | `KEEP` | Enforces double-booking invariants and business hours (9 AM - 7 PM). |
| `week7-RE_Agent/day5-langgraph-agent/tools/calendar_tools.py` | `KEEP` | One-click Google Calendar web links and RFC 5545 `.ics` file generator. |
| `week7-RE_Agent/day5-langgraph-agent/tools/crm_tools.py` | `EXTEND` | SQLite/Postgres CRM store. Add lead priority (`HOT`/`WARM`/`COLD`) and persona persistence. |
| `week7-RE_Agent/day5-langgraph-agent/tools/email_tools.py` | `KEEP` | Responsive HTML property specification and appointment confirmation dispatcher. |
| `week7-RE_Agent/day5-langgraph-agent/learning/dataset.py` | `REPAIR` | Accept `clarification_needed` and `source` arguments; prevent database lock contention. |
| `week7-RE_Agent/day5-langgraph-agent/db/realestate_kb.db` | `KEEP` | Authoritative database containing 750 properties, 18 locations, 151 amenities, 20 FAQs. |
| **Week 7: Evaluation & Security (Day 6)** | | |
| `week7-RE_Agent/day6-evaluation-security/eval_suite/test_conversations.json` | `KEEP` | 46 comprehensive, realistic multi-turn dialogues covering 11 customer categories in Urdu/UrduLish. |
| `week7-RE_Agent/day6-evaluation-security/security/security_guardrails.py` | `REFACTOR` | Rename package to `guardrails_security` to eliminate namespace collision with Day 5 `security/`. |
| `week7-RE_Agent/day6-evaluation-security/performance/benchmark_engine.py` | `KEEP` | Benchmark engine for turn latency, booking success, and hallucination rate. |
| `week7-RE_Agent/day6-evaluation-security/monitoring/metrics_collector.py` | `KEEP` | Prometheus metrics exporter (`/metrics`) and voice QoS tracker. |
| `week7-RE_Agent/day6-evaluation-security/deployment/prod_server.py` | `REFACTOR` | Integrate with unified app entrypoint exposing both voice SSE and ML serving endpoints. |
| **Week 8: Machine Learning & MLOps Platform** | | |
| `week8/Day1/data/processed/cleaned_properties.csv` | `KEEP` | 1.7 MB processed property dataset with cleaned square footage, bedrooms, prices, and amenities. |
| `week8/Day1/data/processed/cleaned_leads.csv` | `KEEP` | 618 KB processed lead conversion dataset with call durations, latency, and objections. |
| `week8/Day2/models/best_property_valuation_model.joblib` | `KEEP` | Production CatBoost regression model ($R^2=0.988$, MAPE $8.4\%$). |
| `week8/Day2/models/quantile_bands_model.joblib` | `KEEP` | Production LightGBM quantile regression model (P10, P50, P90 confidence bands). |
| `week8/Day3/models/best_lead_scoring_model.joblib` | `KEEP` | Production LightGBM lead scoring classifier (PR-AUC $0.562$). |
| `week8/Day3/models/kmeans_customer_personas.joblib` | `KEEP` | K-Means clustering artifacts ($k=4$ customer personas). |
| `week8/Day3/src/shap_explainers.py` | `KEEP` | Local TreeExplainer SHAP attribution generator in fluent English and UrduLish. |
| `week8/Day4/src/assistant.py` | `REFACTOR` | Merge standalone LangGraph tools (Valuation, Lead Scorer, Market Stats) into unified Week 7 graph. |
| `week8/Day4/app_dashboard.py` | `KEEP` | Streamlit executive dashboard (Property Valuation, Triage Desk, SHAP lab, UrduLish assistant). |
| `week8/Day5/monitoring/drift_monitor.py` | `KEEP` | Evidently AI data & prediction drift detection engine with alert thresholds. |
| `week8/Day5/retraining/retrain_pipeline.py` | `KEEP` | Automated champion/challenger retraining pipeline with safe rollback. |
| **Legacy / Redundant Assets** | | |
| `week7-RE_Agent/day5-langgraph-agent-with-machine-learning/` | `ARCHIVE` | Intermediate draft directory superseded by Week 8 Day 4 and Day 5 implementations. |
| `week7-RE_Agent/website/` (Empty) | `ARCHIVE` | Empty placeholder directory. |
| `annotated_traces.json` (Workspace Root) | `ARCHIVE` | Sports AFL example trace file unrelated to real estate domain. |

---

## 4. Preservation Invariants

To adhere strictly to project preservation rules:
1. **Zero Data Deletion**: No property records, lead tables, audio transcripts, or evaluation datasets will be deleted.
2. **Model Continuity**: All serialized `.joblib` model weights from Day 2 and Day 3 remain authoritative and unmodified.
3. **Traceability**: All existing test cases in `test_day5_agent.py` and `test_conversations.json` must continue to pass 100% after refactoring.
