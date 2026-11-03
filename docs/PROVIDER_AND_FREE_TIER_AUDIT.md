# 🌐 Provider & Free-Tier Architectural Audit

**System:** RealEstate Hub Unified Platform  
**Compliance Level:** Free-First Open-Source Priority  
**Audit Date:** September 30, 2026  

---

## 1. Provider Evaluation & Licensing Audit

To uphold the non-negotiable constraint of **Free-First Resources**, every service utilized by the unified agent has been audited for cost, quotas, commercial terms, offline viability, and Pakistani Urdu capability:

| Component | Candidate Technology | Cost / Free Tier Terms | Offline / Self-Hosted? | Pakistani Urdu Capability | Production Recommendation |
|---|---|---|---|---|---|
| **Speech-to-Text (STT)** | **Faster-Whisper (Large-v3/Medium)** | **100% Free** (MIT License, Open Weights) | ✅ Yes (Local CPU/GPU) | Excellent on Pakistani Urdu, code-switching, and Roman Urdu. | **Primary Default Engine** |
| | **Groq Whisper (`whisper-large-v3`)** | Free Tier (Rate limited: 20 req/min) | ❌ Cloud API | Very high accuracy; near-zero latency (<250ms). | **Secondary Cloud Adapter** |
| | **Deepgram Nova-3** | Paid after initial $200 trial credits ($0.0043/min) | ❌ Cloud API | High accuracy with custom Pakistani real estate keyterms. | **Telephony Cloud Option** |
| **Text-to-Speech (TTS)** | **Edge-TTS (`ur-PK-UzmaNeural`, `ur-PK-AsadNeural`)** | **100% Free** (No API Key or Billing required) | ⚠️ Streaming via MS Edge socket | **Native Pakistani Urdu accent**, authentic prosody, fluent bilingual reading. | **Primary Default Voice Engine** |
| | **Piper TTS** | **100% Free** (MIT Open-Source, C++ binary) | ✅ Yes (Fully Offline) | High performance, but limited natural Urdu prosody. | **Offline Fallback** |
| | **Vapi Voice (Elliot)** | Paid after trial credits | ❌ Cloud Telephony | Natural conversational voice for live phone calls. | **Telephony Adapter** |
| **Large Language Model (LLM)** | **Google Gemini 2.5 / 1.5 Flash** | Free Tier on AI Studio (15 RPM, 1M TPM, zero cost) | ❌ Cloud API | Exceptional UrduLish generation, nuanced cultural politeness. | **Primary Cloud LLM** |
| | **Groq Llama 3.3 70B Versatile** | Free Tier (30 RPM, 6K TPM) | ❌ Cloud API | Ultra-fast token generation (~250 tokens/sec). | **Fast Alternative LLM** |
| | **Ollama (`llama3.1:8b` / `qwen2.5:7b`)** | **100% Free** (Open Weights) | ✅ Yes (Local GPU/CPU) | Capable of local reasoning; higher hardware footprint. | **Local Offline Engine** |
| **Vector Database (RAG)** | **ChromaDB / FAISS** | **100% Free** (Apache 2.0 Open Source) | ✅ Yes (Local File Storage) | Semantic vector matching without recurring cloud fees. | **Permanent Vector Store** |
| **Embeddings** | **Sentence-Transformers (`all-MiniLM-L6-v2`)** | **100% Free** (Apache 2.0 Open Source) | ✅ Yes (Local Execution) | Fast, reliable semantic retrieval over society bylaws and FAQs. | **Permanent Embeddings** |
| **Relational Database** | **SQLite / PostgreSQL** | **100% Free** (Public Domain / Open Source) | ✅ Yes (Local File / Docker) | Standard SQL ACID storage for 750 listings, CRM, appointments. | **Primary Database** |
| **Calendar Sync** | **Local RFC 5545 `.ics` Generator** | **100% Free** (No external dependencies) | ✅ Yes (Local File Engine) | Universally imports into Apple, Google, Outlook, and Android. | **Primary Default Scheduler** |
| | **Google Calendar API** | Free Tier (1,000,000 queries/day) | ❌ Cloud OAuth | Generates direct web viewable event URLs for customers. | **Configurable Adapter** |
| **Email Dispatch** | **Local Development Mock / SMTP Relay** | **100% Free** (Standard smtplib) | ✅ Yes (Local Disk or Free Gmail Relay up to 500/day) | Delivers responsive HTML property brochures and dossiers. | **Primary Dispatcher** |
| **ML Inference (Week 8)** | **CatBoost, LightGBM, Scikit-Learn** | **100% Free** (Apache/BSD Open Source) | ✅ Yes (Local Model Artifacts) | $R^2=0.988$ valuation, PR-AUC $0.562$ lead scoring, SHAP XAI. | **Production ML Engines** |

---

## 2. Telephony Limitations & Transparency Disclosure

> [!IMPORTANT]
> ### Honest Disclosure on Public Phone Numbers (PSTN)
> A public Pakistani telephone number (e.g. `+92-300-XXXXXXX` or landline DID) that can be dialed from local cellular networks (Jazz, Zong, Telenor, PTCL) **cannot be provided 100% free of charge indefinitely**. Telecommunication carriers legally mandate line rental fees and per-minute PSTN termination tariffs.
> 
> **How our Free-First Architecture solves this:**
> 1. **WebRTC Web Browser Voice Calling (100% Free)**: The agent provides an in-browser voice interface where anyone can talk to the agent in real-time via their microphone/speaker with zero telecom fees.
> 2. **Pluggable Telephony Adapter**: The agent exposes the standard Vapi/Twilio/SIP webhook (`/vapi/llm/chat/completions`). When a company attaches a real phone number to Vapi or Twilio, the exact same agent answers the phone immediately with no code changes.
> 3. **Local CLI Voice Loop**: Developers can speak to the agent directly in terminal using local microphone and speaker loops without any internet connection.
