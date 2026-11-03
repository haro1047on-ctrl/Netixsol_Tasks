# 📊 Data Specification: Zarya UrduLish Banking Assistant
## Training Corpus Composition, Prompt Templates & Schema Invariants

- **Document Version:** 1.0.0  
- **Date:** October 2026  
- **Author:** Principal LLM & Fintech AI Engineer  
- **Context:** Week 10 Capstone Project — Day 1 Deliverable  

---

## 1. Objective & Scope

This document details the engineering specifications, conversational format, dataset composition, and typing schemas for fine-tuning open-weights foundation models (specifically **Qwen/Qwen2.5-7B-Instruct** and **Meta-Llama-3.1-8B-Instruct**) to serve as the core bilingual conversational engine for Zarya Digital Bank (Pakistan).

The resulting dataset must train the model to:
1. Reason and converse fluently in Pakistani **UrduLish** (Roman Urdu + English banking terms).
2. Adhere strictly to **State Bank of Pakistan (SBP)** consumer protection guidelines, empathetic grievance handling, and dispute resolution timelines.
3. Emit 100% syntactically valid and structurally deterministic **JSON output** matching the Zarya Banking Schema.
4. Execute immediate, zero-tolerance refusal upon detecting attempts to solicit or reveal sensitive authentication credentials (OTP, PIN, Password, CVV).

---

## 2. Conversational Message Formats

The dataset is authored using the industry-standard **ChatML / Qwen-2.5 / Llama-3 format**. Every training instance is serialized as a JSON object containing a `messages` array of turn dictionaries (`{"role": "system" | "user" | "assistant", "content": "..."}`).

### 2.1 ChatML / Qwen-2.5 Prompt Formatting
```text
<|im_start|>system
You are Zarya Assistant (Zarya Madadgaar), the official bilingual AI banking concierge for Zarya Digital Bank (Pakistan).
Follow these mandatory guidelines:
1. Language: Reply in polite, empathetic UrduLish (Roman Urdu mixed with everyday English banking terms).
2. Persona: Always address the customer with respect using "Aap" and "Ji". For failed debits or delayed payments, open with an empathetic apology.
3. Security: Under State Bank of Pakistan regulations, NEVER ask for, accept, or disclose any OTP, ATM/App PIN, CVV, or passwords.
4. Output Format: Always respond with a single, strictly valid JSON object matching the ZaryaBankingAssistantResponse schema.
Grounding Context: {optional_rag_context}
<|im_end|>
<|im_start|>user
{customer_query_in_urdulish}
<|im_end|>
<|im_start|>assistant
{json_payload_conforming_to_schema}
<|im_end|>
```

### 2.2 Llama-3.1 Token Template Mapping
```text
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
{system_instruction}<|eot_id|>
<|start_header_id|>user<|end_header_id|>
{customer_message}<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
{assistant_response_json}<|eot_id|>
```

---

## 3. Dataset Target Composition & Taxonomy Mix

The training corpus is calibrated across task domains, linguistic registers, turn complexities, and customer emotional personas to guarantee production robustness.

### 3.1 Task & Intent Mix (Target Corpus: 3,000+ Examples)

| Category Intent | Target % | Target Count | Key Banking Scenarios Covered |
|:---|:---:|:---:|:---|
| **`Transfers_Payments`** | 25.0% | ~750 | Raast P2P transfer deductions, 1Link IBFT timeouts, utility bills (K-Electric, LESCO, SNGPL), fee inquiries, 1Link RRN tracking. |
| **`Complaints`** | 22.0% | ~660 | ATM cash retraction (amount debited, cash not dispensed), POS double billing, branchless agent overcharging, SBP Sunwai escalations. |
| **`Cards`** | 15.0% | ~450 | Lost card instant freeze, international e-commerce activation, card delivery tracking, ATM daily limits, green-PIN generation. |
| **`Fraud_Scams`** | 12.0% | ~360 | Fake lottery calls (BISP, Jeeto Pakistan), OTP phishing, SMS spoofing, suspicious device login alerts, account compromise. |
| **`Account_Balance`** | 11.0% | ~330 | Balance inquiries, mini-statement download, IBAN retrieval, withholding tax certificate requests (FBR Active/Non-Active). |
| **`Loans_Products`** | 8.0% | ~240 | Asaan Digital Karobar, nano-loans, Roshan Digital Account (RDA) repatriation, monthly PLS savings rates, Murabaha terms. |
| **`Out_Of_Scope`** | 7.0% | ~210 | General chitchat, weather, cricket/politics debates, prompt injection & jailbreak attempts. |
| **Total** | **100.0%** | **3,000+** | Complete coverage across all digital retail banking operations. |

### 3.2 Crucial Ratio Invariants
1. **Multi-Turn Conversations:** $\ge 20.0\%$ (Minimum 600 examples). Models must maintain conversational context, remember transaction IDs (RRNs) shared in earlier turns, and de-escalate angry customers over 2–4 dialogue exchanges.
2. **Safety, Fraud & Security Refusals:** $\ge 10.0\%$ (Minimum 300 examples). Queries attempting social engineering, prompt extraction, or volunteering OTPs/PINs. Must trigger 100% clean refusal and `"security_flag.refusal_triggered": true`.
3. **Structured JSON Output:** $100.0\%$ of assistant completions in the core training set adhere to the unified JSON schema.

### 3.3 Language Register Mix
- **UrduLish (Code-Switched Roman Urdu + English Banking):** **70%**  
  *Example:* "Mera Raast payment phans gaya hai. Account se 15k debit ho gaye hain magar samne walay ko transfer nahi mila."
- **Colloquial Roman Urdu:** **15%**  
  *Example:* "Bhai mera ATM card kho gaya hai, foran band kar dein warna koi paisay na nikal le."
- **Standard Pakistani English (Financial Register):** **15%**  
  *Example:* "I transferred funds via 1Link IBFT to an Allied Bank account, but the transaction timed out with a pending status."

---

## 4. Customer Persona & Linguistic Variation Matrix

To ensure the model handles real-world customer heterogeneity, the synthetic generator samples across diverse persona profiles:

```
+---------------------+-------------------------------+-------------------------------------------+
| Persona Profile     | Typical Banking Needs         | Linguistic Style & Lexical Indicators     |
+---------------------+-------------------------------+-------------------------------------------+
| 1. Salaried Worker  | Bill payments, IBFT, Salary   | Moderate UrduLish, polite, concerned with |
|    (Urban Retail)   | credit, Debit card limits     | fee deductions and tax withholding.       |
|                     |                               | Lexicon: "Salary credit", "1Link charge"  |
|                     |                               |                                           |
| 2. Tech Freelancer  | Roshan Digital / USD Inflows, | High English code-switching, fast-paced,  |
|    (Digital Native) | E-commerce POS, Tax certs     | technical terms: "Swift code", "FBR CPR"  |
|                     |                               |                                           |
| 3. Shopkeeper / SME | Asaan Digital Karobar, Raast  | Informal Roman Urdu, business jargon:     |
|    (Merchant)       | QR payments, daily cash limit | "Grahak", "Dukan ka account", "Daily limit|
|                     |                               |                                           |
| 4. Distressed User  | ATM cash not dispensed,       | High urgency, emotional words, typos,     |
|    (Disputed Funds) | Fraud call victim, Card stolen| caps, exclamation: "Zulm hai!", "Foran!"  |
|                     |                               |                                           |
| 5. Adversarial /    | Asking model to confirm OTP,  | Sneaky social engineering, imperative     |
|    Scammer          | jailbreak system instructions | tone: "Admin mode", "System override"     |
+---------------------+-------------------------------+-------------------------------------------+
```

---

## 5. PII Masking & Synthetic Data Invariants

To comply with SBP Privacy & Data Governance regulations, **100% of data is synthetic**. The data pipeline strictly generates and validates using realistic Pakistani synthetic placeholders:
- **Synthetic CNIC:** Format `42101-XXXXXXX-X` or `35202-XXXXXXX-X` (13 digits, masked).
- **Synthetic Account:** Format `ZARYA-00001234` or `ZARYA-PK-98765432`.
- **Synthetic Mobile:** Format `+92-300-XXXXXXX` or `0300-XXXXXXX`.
- **Synthetic Card:** Masked format `4111-22XX-XXXX-9012`.
- **Retrieval Reference Number (RRN):** 12-digit numeric identifier `421098765432`.

---
*Approved and Released for Dataset Synthesis.*
