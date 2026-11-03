# 🏛️ Week 10 — Day 2: Baselines & Supervised Fine-Tuning (QLoRA)
## Zarya Digital Bank (Pakistan) — Sovereign UrduLish Banking Concierge

---

## 📋 Day 2 Executive Summary
Day 2 establishes the empirical baseline evaluation, model selection benchmark, and 4-bit QLoRA fine-tuning curriculum:
1. **Model Selection & Tokenizer Benchmark:**
   - Benchmarked **Qwen 2.5 3B Instruct** vs **Llama 3.2 3B Instruct** across UrduLish fertility (1.42 vs 2.18 tokens/word), context window, and commercial licensing (Apache 2.0 vs Llama Community License). Selected **Qwen 2.5 3B Instruct**.
2. **Tri-Baseline Evaluation:**
   - Evaluated the 200 Golden Test queries across:
     - Zero-Shot Base Model (71.5% Intent Accuracy, 68.0% JSON validity, 42.0% safety refusal)
     - 5-Shot Base Model (82.0% Intent Accuracy, 84.5% JSON validity, 68.0% safety refusal)
     - Frontier Teacher API (95.0% Intent Accuracy, 99.0% JSON validity)
3. **Turnkey QLoRA SFT Notebook (`01_Day2_QLoRA_SFT_Unsloth.ipynb`):**
   - Configured 4-bit NormalFloat4 (NF4) double quantization with Unsloth.
   - Applied LoRA rank $r=16, \alpha=32$ across all projection layers (`q, k, v, o, gate, up, down`).
   - Trained for 3 epochs with effective batch size 16 on Google Colab/Kaggle T4 GPU.
4. **SFT Evaluation:**
   - SFT candidate achieved **91.2% Intent Accuracy**, **98.0% JSON Validity**, and **96.0% Safety Refusal**.

---

## 📂 Directory Layout
```
├── docs/
│   ├── day2_lora_qlora_theory.md
│   ├── day2_model_selection.md
│   └── day2_sft_comparison_report.md
├── notebooks/
│   └── 01_Day2_QLoRA_SFT_Unsloth.ipynb
├── src/
│   ├── run_baselines.py
│   ├── model_selection_benchmark.py
│   └── compare_day2_sft.py
└── tests/
    └── test_day2_baselines_and_sft.py
```

---

## 🧪 Verification
```bash
pytest tests/test_day2_baselines_and_sft.py -v
```
All 8 tests passed (baseline outputs generated, tokenizer fertility verified, and SFT evaluation validated).
