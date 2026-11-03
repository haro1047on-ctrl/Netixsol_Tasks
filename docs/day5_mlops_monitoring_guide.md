# Zarya Digital Bank (Pakistan) — Production MLOps Monitoring, Telemetry & Continuous DPO Guide

This document defines the complete enterprise MLOps lifecycle, production telemetry framework, drift detection methodology, and automated model rollback runbook for the **Zarya Digital Bank Fine-Tuned UrduLish Banking Concierge**.

---

## 1. High-Level Architecture & Feedback Flywheel

The Zarya Bank AI platform employs a closed-loop flywheel architecture. Production customer interactions, automated guardrail intercepts, and customer satisfaction (CSAT) ratings are securely captured, sanitized, and channeled back into continuous Direct Preference Optimization (DPO) and Supervised Fine-Tuning (SFT) iterations.

```
       [ Customer (Web / Mobile App) ]
                     │ (UrduLish Queries)
                     ▼
       ┌───────────────────────────────┐
       │   Edge API Gateway (FastAPI)  │
       │   - Presidio PII Masking      │
       │   - Multi-Layer Guardrails    │
       └──────────────┬────────────────┘
                      │ Sanitized Input
                      ▼
       ┌───────────────────────────────┐
       │   Hybrid Orchestration Engine │
       │   - ChromaDB RAG (BGE-M3)     │
       │   - Fine-Tuned 3B AWQ Model   │
       └──────────────┬────────────────┘
                      │ Structured JSON Response
                      ▼
     ┌────────────────────────────────────────────────────────┐
     │           Telemetry & Telemetry Consumers              │
     ├──────────────────────────┬─────────────────────────────┤
     │ Prometheus & Grafana     │ PostgreSQL Persistence      │
     │ - TTFT & Latency (p99)   │ - PII-Masked Conversations  │
     │ - Throughput (tok/sec)   │ - CSAT Thumbs Up / Down     │
     │ - Safety Block Rates     │ - Guardrail Traps & Alerts  │
     └──────────────────────────┴──────────────┬──────────────┘
                                               │
                                               ▼
                              ┌─────────────────────────────────┐
                              │  Continuous DPO Pipeline        │
                              │  (`src/monitoring/`)            │
                              │  1. Extract Flawed Turns        │
                              │  2. RAG Policy Grounding        │
                              │  3. Synthesize (Chosen, Reject) │
                              └────────────────┬────────────────┘
                                               │
                                               ▼
                              ┌─────────────────────────────────┐
                              │ Scheduled DPO Retraining &      │
                              │ Automated Canary Rollback Gates │
                              └─────────────────────────────────┘
```

---

## 2. PII-Masked Structured Telemetry Specification

Under State Bank of Pakistan (SBP) cybersecurity directives and data privacy regulations, **no raw customer PII or financial credentials may ever be logged to disk, database, or external Application Performance Monitoring (APM) dashboards**.

### 2.1 Masking Standards

Every message entering the API or persistent logs passes through `StructuredEventLogger.mask_pii()` before write operations:

| PII Entity | Identification Pattern | Production Mask Token |
| :--- | :--- | :--- |
| **CNIC** | `\b\d{5}[-\s]?\d{7}[-\s]?\d\b` | `[MASKED_CNIC]` |
| **Debit / Credit Card (PAN)** | `\b(?:\d{4}[-\s]?){3}\d{4}\b` (Luhn Validated) | `[MASKED_CARD_PAN]` |
| **Pakistani IBAN** | `\bPK\d{2}[A-Z]{4}\d{16}\b` | `[MASKED_PK_IBAN]` |
| **Pakistani Mobile** | `\b(?:03\d{2}\|(?:\+92\|0092)3\d{2})[-\s]?\d{7}\b` | `[MASKED_MOBILE]` |
| **Credentials (OTP / PIN)** | `\b(?:OTP\|PIN\|code)[:\s=]*([0-9]{4,6})\b` | `OTP:[MASKED_CREDENTIAL]` |

### 2.2 Standard JSON Structured Log Event Format

All logs are emitted as single-line JSON strings to `stdout` and collected by Fluentd/Promtail into central Elasticsearch/Loki storage:

```json
{
  "timestamp": "2026-10-15T12:04:18.492Z",
  "environment": "production",
  "service": "zarya-banking-ai",
  "session_id": "sess_89f0a213e4b7",
  "event_name": "CHAT_COMPLETION_SUCCESS",
  "model_version": "qwen2.5-3b-zarya-dpo-v1.2",
  "latency_ms": 118.4,
  "time_to_first_token_ms": 28.5,
  "tokens_generated": 142,
  "tokens_per_second": 89.2,
  "guardrail_triggered": false,
  "intent": "Transfers_Payments",
  "sub_intent": "Raast_Failed_Debit_Inquiry",
  "prompt_sanitized": "AOA, maine Raast se [MASKED_MOBILE] ko 5000 rupay bhejey magar deduct ho gaye aur pohanchay nahi. RRN 763595448017.",
  "response_sanitized": "{\"intent\":\"Transfers_Payments\",\"sub_intent\":\"Raast_Failed_Debit_Inquiry\",\"response_urdu_lish\":\"Ji Janab, humein be-had afsos hai...\"}",
  "rag_citations": ["data/policies/02_fund_transfers_raast.md#L45-L68"],
  "csat_rating": null
}
```

---

## 3. Production Metric Taxonomy (SLIs & SLOs)

The bank operations team tracks performance using four core metric quadrants:

### 3.1 Operational & Latency SLOs

| Metric | Target (SLO) | Prometheus Metric Name | Critical Alert Threshold |
| :--- | :--- | :--- | :--- |
| **Time-to-First-Token (TTFT)** | $< 45\text{ ms}$ (p95) | `zarya_llm_ttft_milliseconds` | $> 120\text{ ms}$ for 5 consecutive mins |
| **Total Generation Latency** | $< 250\text{ ms}$ (p99) | `zarya_llm_total_latency_ms` | $> 500\text{ ms}$ |
| **Inference Throughput** | $\ge 80\text{ tok/s/GPU}$ | `zarya_llm_tokens_per_second` | $< 35\text{ tok/s}$ |
| **GPU VRAM Utilization** | $< 80\%$ (Single L4/T4) | `nvidia_smi_memory_used_bytes` | $> 92\%$ (OOM danger) |
| **Service Availability** | $\ge 99.95\%$ Uptime | `zarya_api_http_requests_total` | Error rate $> 0.5\%$ |

### 3.2 Model Quality & Governance Metrics

| Metric | Target | Prometheus / DB Counter | Action on Breach |
| :--- | :--- | :--- | :--- |
| **Intent Classification Accuracy** | $\ge 94.0\%$ | `zarya_model_intent_accuracy` | Trigger human audit |
| **JSON Parse Validity Rate** | $\ge 99.0\%$ | `zarya_model_json_valid_ratio` | Fallback regex reparsing |
| **RAG Hallucination Rate** | $\le 1.0\%$ | `zarya_rag_unverified_fee_total` | Re-index ChromaDB |
| **Customer CSAT (Thumbs Up)** | $\ge 88.0\%$ | `zarya_csat_positive_feedback_ratio`| Trigger DPO extraction job |

### 3.3 Security & Regulatory Guardrail Metrics

| Metric | Target | Threshold | Enforcement |
| :--- | :--- | :--- | :--- |
| **Adversarial Safety Refusal Rate** | **100.0%** | $< 100\%$ | **P1 Immediate Rollback** |
| **Prompt Injection Intercepts** | Monitored | $> 50\text{ attacks/hr}$ | Auto IP rate-limiting |
| **False Refusal Rate (Benign Queries)** | $\le 1.5\%$ | $> 3.0\%$ | Guardrail sensitivity tuning |

---

## 4. Drift Detection Framework

Fintech UrduLish models are vulnerable to two distinct drift types:

### 4.1 Linguistic & Vocabulary Drift (UrduLish Slang)
Pakistani digital banking users continuously adopt novel shorthand (e.g., *"Raast پھنس گیا"*, *"reverse kab hoga"*, *"tax kitna kata"*, *"OTP nahi aa raha"*).
- **Detection Algorithm:** We compute daily rolling vocab OOV (Out-of-Vocabulary) rates and token perplexity.
- **Embedding Drift:** 500 daily sampled customer queries are embedded via `BAAI/bge-m3`. We compute the **Wasserstein Distance** and **Population Stability Index (PSI)** against the Golden Reference baseline:
  $$\text{PSI} = \sum \left( \% \text{Actual} - \% \text{Expected} \right) \times \ln\left(\frac{\% \text{Actual}}{\% \text{Expected}}\right)$$
  - $\text{PSI} < 0.1$: No drift.
  - $0.1 \le \text{PSI} < 0.25$: Moderate drift (scheduled retraining flag).
  - $\text{PSI} \ge 0.25$: Significant linguistic drift (alert ML engineering).

### 4.2 Concept & Policy Drift (Regulatory Updates)
When the State Bank of Pakistan alters inter-bank transfer caps, foreign exchange markups, or tax withholding rates (e.g. Finance Act modifications):
- Monitored via RAG citation freshness and user dispute spikes.
- **Dynamic Hot-Reloading:** The ChromaDB policy store (`src/rag/retriever.py`) is updated within 60 seconds without requiring LLM redeployment or GPU restarts.

---

## 5. Automated DPO Retraining & Quality Gates

The continuous feedback flywheel is automated via `src/monitoring/feedback_to_dpo.py`:

```
   [ Daily User Traffic ]
            │
            ├─► Thumbs Down (Rating <= 2)  ──┐
            │                                 │
            ├─► Guardrail Traps / Attacks  ───┼─► [ Continuous DPO Pipeline ]
            │                                 │   - PII Scrubbing
            └─► Human Agent Overrides       ──┘   - RAG Grounding
                                                  - Formats (Prompt, Chosen, Rejected)
                                                              │
                                                              ▼
                                              `data/dpo/feedback_preference_pairs.jsonl`
                                                              │
                                                              ▼
                                              [ Bi-Weekly LoRA + DPO Training Job ]
                                                              │
                                                              ▼
                                              [ Automated Candidate Verification ]
```

### 5.1 Verification Checklist Prior to Traffic Cutover

Every freshly retrained candidate model undergoes an automated battery against `data/splits/golden_test_200.jsonl`:

1. **Adversarial Safety Probe (50 Attack Prompts):**
   - Refusal Rate must be **exactly 100%**.
   - Zero credential leaks tolerated.
2. **JSON Syntax Integrity:**
   - Must achieve $\ge 98.5\%$ valid parse rate without fallback parsers.
3. **Intent Classification & Routing:**
   - Intent Accuracy drop must be $\le 2.0\%$ compared to current active production model.
4. **Tone & Empathy Benchmark:**
   - LLM-as-a-Judge score on UrduLish fluency and polite persona ("Ji", "Aap") must be $\ge 4.5/5.0$.

---

## 6. Automated Canary Deployment & Rollback Runbook

When a retrained model is ready for deployment:

### Phase 1: Canary Routing (10% Traffic)
```
                  ┌─────────[ 90% ]─────────► Current Model (v1.2)
   Inbound Traffic │
                  └─────────[ 10% ]─────────► Candidate Model (v1.3)
```
- Evaluate candidate model for 2 hours on live non-critical queries (FAQs, Account balance inquiries).
- Real-time Prometheus evaluation of error rate, latency, and CSAT.

### Phase 2: Traffic Promotion (100% Cutover)
- If canary error rate $\le 0.1\%$ and CSAT $\ge 90\%$, promote candidate model to active production.

### Phase 3: Emergency Automated Rollback Trigger
If **ANY** of the following conditions occur during canary or production serving:
- Safety Refusal Rate drops below 100% on security probes.
- Exception / 500 error rate exceeds 0.5% over a 3-minute window.
- JSON unparseable response rate exceeds 2.0%.

**The automated orchestrator triggers an immediate rollback:**
```bash
# Emergency one-command model rollback
python -m src.monitoring.feedback_to_dpo --action test-rollback
# Re-routes traffic instantaneously to previous checkpoint v1.2
```

The system immediately flushes GPU memory, flips the symlink `/models/active` back to `checkpoint_v1.2`, and reloads vLLM/Ollama in $< 500\text{ ms}$, ensuring 100% operational resilience and compliance with SBP digital banking continuity mandates.
