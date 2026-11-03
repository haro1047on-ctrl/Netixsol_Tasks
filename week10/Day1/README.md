# 🏛️ Week 10 — Day 1: Problem Framing, Schemas & Dataset Engineering
## Zarya Digital Bank (Pakistan) — Sovereign UrduLish Banking Concierge

---

## 📋 Day 1 Executive Summary
Day 1 establishes the foundational data architecture, regulatory framing, and synthetic dataset pipeline for Zarya Digital Bank:
1. **Architecture Decision Record (ADR):** Evaluated Prompt Engineering, RAG only, Fine-Tuning only, and Fine-Tuning + RAG Hybrid across Quality, Cost, SBP Data Sovereignty, Latency, and Updateability. Formally selected the **Fine-Tuning + RAG Hybrid** architecture.
2. **Data Specification:** Defined the ChatML format (`system`, `user`, `assistant`), balanced task mix (20% FAQ, 25% Complaints, 20% Fraud/Security, 20% Accounts, 15% Transfers), and strict Pydantic JSON schema (`ZaryaBankingAssistantResponse`).
3. **Presidio PII Sanitization:** Automated scrubbing and replacement of sensitive Pakistani identifiers (CNICs, 16-digit Card PANs, 24-character Pakistani IBANs, phone numbers, OTPs) with zero raw customer credential leaks.
4. **Stratified Splitting:** Partitioned 4,000 synthesized dialogues into 80/10/10 stratified splits:
   - `train_3200.jsonl` (3,200 training examples)
   - `val_400.jsonl` (400 validation examples)
   - `golden_test_200.jsonl` (200 golden benchmark examples)

---

## 📂 Directory Layout
```
├── docs/
│   ├── day1_architecture_decision_record.md
│   ├── day1_data_specification.md
│   └── day1_cleaning_report.md
├── src/
│   ├── schemas.py
│   ├── generate_synthetic_data.py
│   ├── clean_dataset.py
│   └── prepare_splits.py
└── tests/
    └── test_dataset_engineering.py
```

---

## 🧪 Verification
```bash
pytest tests/test_dataset_engineering.py -v
```
All 10 tests passed (100% PII scrubbed, valid JSON schemas, and exact category proportions).
