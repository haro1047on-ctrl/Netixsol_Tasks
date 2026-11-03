# 🛠️ Production Operations, MLOps & Handover Runbook

**System:** RealEstate Hub Unified Platform (Week 7 Voice + Week 8 ML)  
**Target Environment:** Production / Hybrid Cloud / On-Premise  
**Document Version:** 2.0  
**Date:** September 30, 2026  

---

## 1. Quickstart & Service Launch Commands

### A. Unified Interactive Terminal CLI (Voice & Text)
Test the complete conversational agent directly from your terminal:
```bash
python run_unified_agent.py --cli
```

### B. Unified FastAPI Production Server
Serves both Vapi/WebRTC streaming endpoints (`/vapi/llm/chat/completions`, `/voice/synthesize`) AND Week 8 ML serving endpoints (`/predict/price`, `/predict/lead-score`, `/explain/lead`):
```bash
python run_unified_agent.py --serve
```
* Interactive Swagger Docs: `http://localhost:8000/docs`
* Health Endpoint: `http://localhost:8000/health`
* Prometheus Telemetry: `http://localhost:8000/metrics`

### C. Streamlit Executive Dashboard
Launches the 5-tab real estate executive dashboard:
```bash
python run_unified_agent.py --dashboard
```

### D. Automated Master Test & Verification Suite
Executes the full test pipeline (Day 5 LangGraph agent, Day 6 Security & Eval, Valuation, Lead Scoring):
```bash
python run_unified_agent.py --test
```

---

## 2. Telephony Setup (Vapi & WebRTC)

### 1. Browser WebRTC Calling (100% Free)
- No telecom subscriptions or phone numbers required.
- Access the web interface at `http://localhost:8000/` and talk directly through your computer's microphone and speakers.

### 2. Live PSTN Telephony (Phone Numbers)
1. In `week7-RE_Agent/day5-langgraph-agent/.env`, set:
   ```env
   VAPI_PRIVATE_KEY=your_vapi_private_key
   VAPI_ASSISTANT_ID=your_assistant_id
   BACKEND_PUBLIC_URL=https://your-public-domain.com
   ```
2. Run the assistant sync script:
   ```bash
   python week7-RE_Agent/day5-langgraph-agent/create_vapi_assistant.py
   ```
3. Dial the assigned Pakistani phone number. Incoming calls stream to `/vapi/llm/chat/completions` in real-time.

---

## 3. MLOps Monitoring & Automated Retraining (Week 8)

### A. Data & Prediction Drift Detection (Evidently AI)
Detects feature drift and target drift when property prices change or buyer budgets shift:
```bash
python week8/Day5/monitoring/drift_monitor.py
```
- Outputs visual HTML reports to `week8/Day5/reports/drift_report.html`.
- Alert Threshold: If MAPE exceeds $15\%$ or Drift Score $> 0.20$, automated retraining is triggered.

### B. Automated Champion/Challenger Retraining Pipeline
```bash
python week8/Day5/retraining/retrain_pipeline.py
```
- Trains a challenger CatBoost model on newly collected market listings.
- Evaluates against the champion model on a shared holdout set.
- Automatically promotes the challenger if $R^2$ improves and MAPE drops.
- Preserves timestamped backups for instant rollback:
  ```powershell
  # Rollback command if challenger underperforms in live production:
  Copy-Item -Path "week8/Day2/models/best_property_valuation_model_backup.joblib" -Destination "week8/Day2/models/best_property_valuation_model.joblib"
  ```

---

## 4. Telemetry & Observability

The platform exports live Prometheus metrics at `/metrics`:
* `realestate_turns_total`: Total conversational turns completed.
* `realestate_turn_latency_avg_ms`: Rolling average turn latency.
* `realestate_turn_latency_p95_ms`: 95th percentile latency (Target: $< 1500\text{ ms}$).
* `realestate_booking_success_total`: Total property viewing visits confirmed.
* `realestate_security_blocks_total`: Total intercepted prompt injections / attacks.

---

## 5. Security & Incident Response

* **Adversarial Injections**: Handled automatically by `SecurityGuardrailEngine`. Malicious prompts are deflected with polite real estate redirection.
* **Database Outage**: Agent operates in degraded mode using cached valuation estimates and logs inquiries for manual agent follow-up.
* **Secret Leak Redactor**: All outgoing messages are sanitized before speech synthesis; API keys and bearer tokens are automatically replaced with `[CONFIDENTIAL_REDACTED]`.
