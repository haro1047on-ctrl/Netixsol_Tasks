# Zarya Digital Bank (Pakistan) — Operations & Reproducibility Guide

This operational handbook provides step-by-step instructions for training, quantizing, serving, monitoring, and rolling back the **Zarya Digital Bank Fine-Tuned UrduLish Banking Concierge**.

---

## 1. System Requirements & Prerequisites

### 1.1 Compute Architectures Supported
- **Cloud / On-Prem GPU (Primary):** 1x NVIDIA GPU with $\ge 16\text{ GB}$ VRAM (NVIDIA L4, A10G, T4, RTX 4090).
- **Free Colab / Kaggle T4:** 100% compatible for SFT and DPO training using Unsloth.
- **CPU Fallback / Edge:** Any x86_64 or ARM64 multi-core server with $\ge 8\text{ GB}$ RAM running Ollama / llama.cpp.

### 1.2 Software Dependencies
- **Python:** `3.10` to `3.13`
- **Docker Engine:** `24.0+` & Docker Compose `v2.20+`
- **CUDA / cuDNN:** CUDA 12.1+ / 12.4+ (if GPU serving)
- **Key Python Packages:** `torch`, `transformers`, `peft`, `bitsandbytes`, `fastapi`, `chromadb`, `presidio-analyzer`, `streamlit`.

---

## 2. End-to-End Execution Workflow

```
[ Step 1: Data Engineering & PII Cleaning ]
                   │
                   ▼
[ Step 2: 4-bit QLoRA SFT Training (Colab / Local) ]
                   │
                   ▼
[ Step 3: DPO Alignment Training (Colab / Local) ]
                   │
                   ▼
[ Step 4: Adapter Merge & AWQ/GGUF Quantization ]
                   │
                   ▼
[ Step 5: ChromaDB Policy KB Indexing ]
                   │
                   ▼
[ Step 6: Multi-Stage Automated Evaluation Harness ]
                   │
                   ▼
[ Step 7: Production Docker Compose Deployment ]
                   │
                   ▼
[ Step 8: Continuous DPO Flywheel & Rollback Gates ]
```

---

## 3. Step-by-Step Execution Guide

### Step 1: Environment Setup
```bash
# Clone the repository
git clone https://github.com/zarya-bank/zarya-urdulish-banking-assistant.git
cd zarya-urdulish-banking-assistant

# Create and activate Python virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install production dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 2: Data Engineering & PII Anonymization
```bash
# Run Presidio scrubbing and Pakistani regex sanitization
python -m src.data.clean_dataset

# Generate stratified 80/10/10 splits (Train: 3,200, Val: 400, Golden Test: 200)
python -m src.data.generate_dataset_splits
```
*Artifacts Produced:*
- `data/splits/train_3200.jsonl`
- `data/splits/val_400.jsonl`
- `data/splits/golden_test_200.jsonl`

### Step 3: Supervised Fine-Tuning (QLoRA)
Execute the notebook `notebooks/01_Day2_QLoRA_SFT_Qwen2_5_3B.ipynb` on Google Colab / Kaggle with a T4 GPU:
1. Opens `Qwen/Qwen2.5-3B-Instruct` in 4-bit NF4 precision.
2. Applies LoRA adapters ($r=16, \alpha=32$) across all linear projection modules.
3. Trains on `train_3200.jsonl` for 3 epochs with gradient checkpointing.
4. Saves adapter checkpoints to `checkpoints/zarya_qwen2.5_3b_sft/`.

### Step 4: Preference Alignment via DPO
Execute the notebook `notebooks/02_Day3_DPO_Alignment.ipynb`:
1. Loads SFT adapter checkpoint.
2. Trains on `data/dpo/preference_pairs_500.jsonl` with $\beta=0.1$ and $lr=5\times 10^{-5}$.
3. Saves aligned adapter checkpoints to `checkpoints/zarya_qwen2.5_3b_dpo/`.

### Step 5: Model Merging & Quantization
Execute `notebooks/03_Day4_Merge_and_Quantize.ipynb`:
1. Merges LoRA adapters into base weights in full 16-bit precision.
2. Exports merged model:
   - **FP16:** `models/merged/zarya-qwen2.5-3b-dpo-fp16/`
   - **4-bit AWQ:** `models/quantized/zarya-qwen2.5-3b-awq/` (vLLM target)
   - **4-bit GGUF (`Q4_K_M`):** `models/quantized/zarya-qwen2.5-3b-Q4_K_M.gguf` (Ollama/CPU target)

### Step 6: Knowledge Base Indexing (ChromaDB)
```bash
# Ingest and embed the 4 official bank policy markdown documents using BGE-M3
python -m src.rag.retriever --reindex
```
*Vector DB Location:* `data/knowledge_base/chroma_db/`

### Step 7: Automated Multi-Stage Evaluation Gate
```bash
# Run Day 1 to Day 5 verification tests
pytest tests/week10/ -v

# Run multi-dimensional benchmark against the Golden Test set
python -m src.eval.evaluation_harness --test-file data/splits/golden_test_200.jsonl
```

---

## 4. Production Deployment & Serving

### 4.1 Zero-Config Docker Compose Deployment
```bash
# Build and start all services (PostgreSQL, FastAPI Gateway, Streamlit UI, Ollama fallback)
docker compose up -d --build

# Verify container statuses
docker compose ps
```

### 4.2 Endpoint Access
- **Customer Chat & Agent Operations Portal:** `http://localhost:8501`
- **FastAPI OpenAPI Documentation:** `http://localhost:8000/docs`
- **Health Check Probe:** `http://localhost:8000/health`
- **OpenAI-Compatible Chat Completion:** `http://localhost:8000/v1/chat/completions`

### 4.3 Serving with vLLM (Production GPU Host)
```bash
# Launch vLLM OpenAI-compatible server on GPU host
python -m vllm.entrypoints.openai.api_server \
  --model models/quantized/zarya-qwen2.5-3b-awq \
  --quantization awq \
  --dtype float16 \
  --gpu-memory-utilization 0.85 \
  --max-model-len 4096 \
  --port 8000
```

### 4.4 Serving with Ollama (CPU / Edge Fallback)
```bash
# Create custom Ollama model from Modelfile
ollama create zarya-bank -f src/serving/Modelfile

# Start Ollama serving
ollama run zarya-bank
```

---

## 5. Live Policy Updates Without Model Retraining

When the State Bank of Pakistan or Zarya Bank updates schedule of charges (fees, limits, taxes):
1. Navigate to **Tab 3: Live Policy Manager** in the UI (`http://localhost:8501`).
2. Edit the policy markdown file or upload a revised document.
3. Click **"Save Policy & Re-Index Knowledge Base"**.
4. ChromaDB automatically splits chunks and generates new embeddings in $< 5\text{ seconds}$.
5. The LLM immediately cites the updated fees with zero model retraining or downtime.

---

## 6. Continuous MLOps Feedback & Rollback Runbook

### 6.1 Extract Production Feedback for Retraining
```bash
# Extract negative customer reviews (rating <= 2) and guardrail intercepts
python -m src.monitoring.feedback_to_dpo --action extract --output data/dpo/feedback_preference_pairs.jsonl
```

### 6.2 Pre-Cutover Model Verification Gate
Before promoting any retrained model to live production traffic, run the automated verification gate:
```bash
python -m src.monitoring.feedback_to_dpo --action test-rollback
```

### 6.3 Automated Rollback Logic
If candidate fails **ANY** of the following conditions:
- **Safety Refusal Rate < 100.0%** (zero-tolerance on security traps).
- **JSON Syntax Validity Rate < 98.0%**.
- **Intent Classification Accuracy drop > 2.0%** vs baseline.

The gate triggers an immediate rollback:
```
[CANARY BREACH DETECTED]
-> Rolling back traffic to previous checkpoint v1.2
-> Restoring models/active symlink
-> Alerting on-call engineering team via PagerDuty
```

---

## 7. Troubleshooting & Disaster Recovery

| Issue | Symptom | Diagnostic Command | Remediation Action |
| :--- | :--- | :--- | :--- |
| **CUDA OOM Error** | `torch.cuda.OutOfMemoryError` | `nvidia-smi` | Lower `max-model-len` to 2048 or enable `--quantization awq`. |
| **ChromaDB Index Stale** | Model cites outdated fee | `python -m src.rag.retriever` | Delete `data/knowledge_base/chroma_db` and re-index. |
| **FastAPI Connection Timeout** | Streamlit UI shows fallback | `curl http://localhost:8000/health` | Restart `zarya_api` container: `docker compose restart api`. |
| **Database Lock (SQLite)** | `sqlite3.OperationalError: database is locked` | Check background processes | Set `timeout=30.0` or switch to PostgreSQL service via `DATABASE_URL`. |

---

## 8. Summary Verification Command
To verify that the entire software stack, database models, RAG vector store, guardrails, and continuous DPO pipeline are working seamlessly on this machine:
```bash
pytest tests/week10/ -v
```
All tests must report **PASSED**.
