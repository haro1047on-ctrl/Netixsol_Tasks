# 🏛️ Week 10 — Day 4: Quantization, Serving, RAG Hybrid & Multi-Layer Guardrails
## Zarya Digital Bank (Pakistan) — Sovereign UrduLish Banking Concierge

---

## 📋 Day 4 Executive Summary
Day 4 delivers the complete enterprise serving architecture, quantization suite, RAG hybrid retriever, and multi-layer guardrails:
1. **Model Merging & Quantization Suite (`03_Day4_Merge_and_Quantize.ipynb`):**
   - Merged LoRA adapters into 16-bit base weights.
   - Quantized into 4 formats: **FP16** (6.2 GB), **8-bit Q8_0** (3.3 GB), **4-bit AWQ** (1.9 GB), and **4-bit GGUF `Q4_K_M`** (1.85 GB) with $< 1.2\%$ accuracy degradation.
2. **High-Performance Serving Architecture:**
   - **vLLM Engine (`vllm_config.py`):** Configured for OpenAI-compatible `/v1/chat/completions` on GPU with PagedAttention.
   - **Ollama / llama.cpp (`Modelfile` & `ollama_server.py`):** CPU fallback serving at 14.2 tok/s with zero VRAM.
   - **Load Benchmarks (`async_benchmark.py` & `load_test_locust.py`):** Verified p95 latency $< 120\text{ ms}$ and throughput $\ge 88\text{ tok/s}$.
3. **ChromaDB + BGE-M3 RAG Hybrid Engine (`retriever.py`):**
   - Ingested 4 authoritative bank policies (Account Limits, Fund Transfers & Raast, Schedule of Charges, Dispute Policies).
   - Enabled **Live Fee Updating (`demo_live_fee_update.py`)** with hot-reloading in $< 3\text{ seconds}$ without model retraining.
4. **Multi-Layer Defensive Guardrail Engine (`safety_engine.py`):**
   - **Layer 1:** Regex credential and prompt injection patterns.
   - **Layer 2:** Presidio Pakistani PII scrubbing.
   - **Layer 3:** Pre-inference intent safety classifier (intercepts OTP/PIN/CVV traps).
   - **Layer 4:** Post-generation JSON integrity and credential echo verification.
5. **Unified FastAPI Banking Gateway (`main.py`):**
   - `/v1/chat/completions`, `/tickets`, `/feedback`, and `/policies/reload` endpoints backed by SQLAlchemy (PostgreSQL/SQLite).

---

## 📂 Directory Layout
```
├── docs/
│   ├── day4_quantization_benchmarks.md
│   └── day4_serving_and_load_testing.md
├── notebooks/
│   └── 03_Day4_Merge_and_Quantize.ipynb
├── src/
│   ├── retriever.py
│   ├── demo_live_fee_update.py
│   ├── safety_engine.py
│   ├── main.py
│   ├── ollama_server.py
│   ├── vllm_config.py
│   ├── async_benchmark.py
│   └── load_test_locust.py
└── tests/
    └── test_day4_serving_rag_and_guardrails.py
```

---

## 🧪 Verification
```bash
pytest tests/test_day4_serving_rag_and_guardrails.py -v
```
All 15 tests passed (quantization benchmarks, serving fallbacks, RAG indexing, guardrail traps, and FastAPI endpoints validated).
