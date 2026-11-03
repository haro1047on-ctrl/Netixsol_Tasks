# MLOps & Platform Maintenance Guide: Production Real Estate Platform

**Audience:** MLOps Engineers, Platform Reliability Engineers (SRE), Data Engineers  
**System Architecture:** Dockerized FastAPI Gateway + Streamlit Dashboard + SQLite/PostgreSQL  

---

## 1. MLOps Monitoring & Surveillance

Real estate prices and customer behavioral patterns shift continuously due to interest rates, inflation, and seasonal trends.

### 1.1 Automated Drift Monitoring (`drift_detector.py`)
Run weekly surveillance checks against incoming production transaction data:
```bash
python week8/Day5/src/drift_detector.py
```
Outputs generated:
- Interactive HTML Dashboard: [`week8/Day5/reports/data_drift_report.html`](file:///d:/netixsol_work/week8/Day5/reports/data_drift_report.html)
- Machine-Readable JSON: [`week8/Day5/reports/data_drift_report.json`](file:///d:/netixsol_work/week8/Day5/reports/data_drift_report.json)

### 1.2 Alert Thresholds & Service Level Agreements (SLAs)
| Metric | Healthy | Warning | Critical (Auto-Retrain) |
| :--- | :---: | :---: | :---: |
| **Model MAPE** | $< 8.0\%$ | $8.0\% - 15.0\%$ | **$> 15.0\%$** |
| **Drifted Features Ratio** | $< 15\%$ | $15\% - 30\%$ | **$> 30\%$** |
| **Prediction KS p-value** | $> 0.05$ | $0.01 - 0.05$ | **$< 0.01$** |
| **API Latency (p95)** | $< 100\text{ ms}$ | $100 - 300\text{ ms}$ | **$> 500\text{ ms}$** |

---

## 2. Model Retraining & Rollback Protocols

### 2.1 Retraining Schedules
1. **Scheduled Monthly Retraining (`0 2 1 * *`):** Executes on the 1st of every calendar month at 02:00 AM UTC, incorporating all transactions collected over the prior 30 days.
2. **Event-Driven Retraining:** Automatically triggered by the monitoring daemon when `RETRAIN_ALERT` fires (e.g. MAPE $> 15\%$).

### 2.2 Triggering Retraining Manually
To execute retraining and challenge the champion model:
```bash
python week8/Day5/src/retraining_pipeline.py
```

### 2.3 Zero-Downtime Rollback Procedure
If the newly promoted model exhibits unexpected behavior or regression post-deployment, execute the instant rollback command:
```python
from retraining_pipeline import RetrainingPipeline
pipeline = RetrainingPipeline()
status = pipeline.rollback_to_last_backup()
print(status)
# Restores previous champion model from archive/ in < 50ms
```

---

## 3. Docker Container Operations

### 3.1 Managing Containers with Docker Compose
```bash
# Start all services (FastAPI, Streamlit, PostgreSQL) in background
docker compose -f week8/Day5/docker/docker-compose.yml up -d

# Inspect running healthchecks
docker compose -f week8/Day5/docker/docker-compose.yml ps

# View live service logs
docker compose -f week8/Day5/docker/docker-compose.yml logs -f api
docker compose -f week8/Day5/docker/docker-compose.yml logs -f dashboard

# Stop and gracefully terminate services
docker compose -f week8/Day5/docker/docker-compose.yml down
```

### 3.2 Healthcheck Probes
- FastAPI Gateway: `GET http://localhost:8000/health` (Reports engine readiness and loaded models).
- Streamlit Dashboard: `GET http://localhost:8501/_stcore/health`

---

## 4. SQLite Audit Store & Log Maintenance
- **Database Location:** [`week8/Day4/logs/prediction_audit.db`](file:///d:/netixsol_work/week8/Day4/logs/prediction_audit.db)
- **Log Rotation:** Rotate monthly or after reaching 1,000,000 recorded predictions.
- **Querying Audit Logs:** Access recent logs via `GET /audit/logs?limit=50` or using the sqlite3 CLI:
  ```bash
  sqlite3 week8/Day4/logs/prediction_audit.db "SELECT timestamp, endpoint, latency_ms, status FROM prediction_audit_logs ORDER BY id DESC LIMIT 10;"
  ```
