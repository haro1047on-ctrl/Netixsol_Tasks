---
language:
- ur
- en
license: mit
task_categories:
- text-generation
- text-classification
tags:
- finance
- banking
- urdulish
- roman-urdu
- pakistan
- qwen2.5
- sft
- dpo
size_categories:
- 1K<n<10K
---

# 💳 Zarya UrduLish Banking Assistant Dataset (Zarya-UBAD)
## State Bank of Pakistan (SBP) Regulated Bilingual Financial AI Corpus

**Curated by:** Principal LLM & Fintech AI Engineer, Zarya Digital Bank (Pakistan)  
**Release Date:** October 2026  
**License:** MIT (Permissive Open Research & Commercial Banking License)  
**Primary Language:** UrduLish (Pakistani Roman Urdu code-switched with English banking terminology)  

---

## 1. Dataset Summary

The **Zarya UrduLish Banking Assistant Dataset (Zarya-UBAD)** is the first production-grade, privacy-sanitized bilingual conversational corpus engineered specifically for the Pakistani digital retail banking ecosystem.

Over 85% of retail banking consumers in Pakistan communicate in **UrduLish** (e.g., *"Mera Raast transfer phans gaya hai, 15k debit ho gaye hain magar dost ko nahi milay"*). Existing international financial NLP datasets (such as Banking77 or Financial Alpaca) operate solely in standard English and lack grounding in Pakistani payment infrastructure—specifically the **State Bank of Pakistan (SBP) Raast instant payment rail**, **1Link 1Bill switches**, **Nadra biometric e-Sahulat standards**, and **SBP Consumer Protection Dispute SLAs**.

Zarya-UBAD addresses this gap by providing structured conversational turns formatted in ChatML that train open-weights language models (Qwen-2.5, Llama-3.1) to:
1. Converse natively and empathetically in authentic UrduLish using polite honorifics (*"Aap"*, *"Ji"*).
2. Generate deterministic, strictly-typed JSON payloads (`ZaryaBankingAssistantResponse`) for Core Banking and CRM ticket generation.
3. Enforce a zero-tolerance **Security Shield** against OTP/PIN phishing and social engineering scams.

---

## 2. Dataset Structure & Splits

The dataset is partitioned into three strictly isolated subsets:

| Split Name | File Path | Record Count | Purpose |
|:---|:---|:---:|:---|
| **Training Set** | `data/splits/train.jsonl` | **~2,500 – 3,000+** | Supervised Fine-Tuning (SFT QLoRA 4-bit) & DPO preference optimization. |
| **Validation Set** | `data/splits/val.jsonl` | **~450+** | Early stopping, validation loss, and checkpoint perplexity monitoring. |
| **Golden Test Set** | `data/splits/golden_test_200.jsonl` | **200 (Frozen)** | Isolated human-benchmarked test suite. Strictly excluded from training. |

### 2.1 Conversational Turn Schema
Each record is serialized in standard ChatML:
```json
{
  "id": "zarya_synth_000104",
  "category": "Transfers_Payments",
  "language": "UrduLish",
  "is_multiturn": false,
  "messages": [
    {
      "role": "system",
      "content": "You are Zarya Assistant (Zarya Madadgaar), the official bilingual AI banking concierge for Zarya Digital Bank (Pakistan)..."
    },
    {
      "role": "user",
      "content": "Aoa, maine Meezan Bank ke account mein PKR 15,000 transfer kiye thay. Meray Zarya balance se kat gaye hain magar recipient keh raha hai usay nahi milay! RRN: 421098765432. Foran check karein."
    },
    {
      "role": "assistant",
      "content": "{\"intent\": \"Transfers_Payments\", \"sub_intent\": \"Raast_Failed_Debit_Inquiry\", \"language\": \"UrduLish\", \"sentiment\": \"Frustrated\", \"priority\": \"High\", \"urgency_score\": 0.85, \"requires_ticket\": true, \"ticket_details\": {\"category\": \"Transfers_Payments\", \"title\": \"Raast P2P Transfer Deducted Recipient Uncredited (PKR 15,000)\", \"description\": \"Customer reported funds debited during transfer to Meezan Bank in Lahore. RRN: 421098765432.\", \"severity\": \"P2_Urgent\", \"suggested_action\": \"Verify 1Link switch settlement and monitor for 24-hour auto-reversal.\", \"assigned_department\": \"Payment_Operations\"}, \"security_flag\": {\"detected_sensitive_request\": false, \"refusal_triggered\": false, \"flag_type\": \"None\"}, \"rag_context_used\": true, \"response_urdu_lish\": \"Ji Janab, humein be-had afsos hai keh aap ki raqam kat gayi hai magar beneficiary ko received nahi hui...\", \"response_english\": \"We sincerely apologize for the inconvenience regarding your transfer of PKR 15,000 to Meezan Bank...\", \"suggested_next_steps\": [\"RRN reference #421098765432 mehfooz rakhein\", \"24 ghantay ke andar balance check karein\"]}"
    }
  ]
}
```

---

## 3. Taxonomy & Intent Distribution

| Intent Category | Proportion | Core Real-World Banking Scenarios |
|:---|:---:|:---|
| `Transfers_Payments` | 25.0% | Raast P2P, 1Link IBFT timeouts, utility bills (K-Electric, LESCO, SNGPL), fee inquiries, RRN tracking. |
| `Complaints` | 22.0% | ATM cash retraction (amount debited, no cash dispensed), SBP 48h SLA, agent fee overcharging. |
| `Cards` | 15.0% | Emergency card freeze, international e-commerce toggle, daily ATM/POS limits, PIN generation. |
| `Fraud_Scams` | 12.0% | Social engineering phishing, fake BISP / Jeeto Pakistan lottery calls, zero-tolerance OTP/PIN refusals. |
| `Account_Balance` | 11.0% | IBAN lookups, withholding tax certificates for FBR active filers, Asaan digital limit inquiries. |
| `Loans_Products` | 8.0% | Asaan Digital Karobar SME financing, nano-loans, Roshan Digital Accounts, Murabaha profit rates. |
| `Out_Of_Scope` | 7.0% | Political debates, general chitchat, prompt injection and jailbreak defense attempts. |

---

## 4. Regulatory Compliance & PII Sanitization

In accordance with State Bank of Pakistan (SBP) *Framework for Digital Banks (2022)* and *BPRD Guidelines on Consumer Privacy*:
- **100% Synthetic Data:** Zero real customer identities, CNICs, accounts, or card numbers were ingested or stored.
- **Multilayered PII Scrubbing:** All records passed through Microsoft Presidio Analyzer + custom Pakistani deterministic regex patterns:
  - CNICs masked to `42101-XXXXXXX-X`.
  - Account numbers formatted as `ZARYA-0000XXXX`.
  - Phone numbers masked to `0300-XXXXXXX`.
  - Card numbers masked to `4111-22XX-XXXX-9012`.
- **Zero-Tolerance Credential Invariant:** 100% of user queries containing credential fishing trigger an explicit safety refusal and security flag.

---

## 5. Usage & Integration

### Loading with Hugging Face `datasets`
```python
from datasets import load_dataset

dataset = load_dataset("json", data_files={
    "train": "data/splits/train.jsonl",
    "validation": "data/splits/val.jsonl",
    "test": "data/splits/golden_test_200.jsonl"
})

print(dataset["train"][0])
```

---
*Maintained by AI Engineering Team, Zarya Digital Bank (Pakistan).*
