# 🏛️ Current Architecture & Operational Workflows

**Platform:** RealEstate Hub Unified Voice Agent & Machine Learning Suite  
**Version:** 2.0 (Integrated Baseline)  
**Date:** September 30, 2026  

---

## 1. Structural Overview

The current system is composed of two primary subsystem domains:

```
d:\netixsol_work/
├── week7-RE_Agent/
│   ├── day5-langgraph-agent/     # Voice telephony server, LangGraph 9-node agent, business tools
│   │   ├── db/realestate_kb.db   # 750 properties, 18 locations, CRM leads, appointments
│   │   ├── nodes/                # Greeting, Intent, Clarification, Recommendation, RAG, Booking, etc.
│   │   ├── tools/                # Search, Availability, Calendar, CRM, Email, RAG
│   │   ├── vapi_server.py        # FastAPI streaming SSE server for Vapi telephony
│   │   └── graph.py              # Compiled LangGraph StateGraph
│   └── day6-evaluation-security/ # 46-dialogue evaluation suite, security guardrails, benchmarking, Prometheus
│       ├── eval_suite/           # test_conversations.json
│       ├── security/             # Prompt injection defenses, PII redaction
│       └── monitoring/           # Prometheus metrics & Voice QoS tracking
└── week8/
    ├── Day1/                     # Cleaned property (1.7 MB) & lead (618 KB) CSV datasets
    ├── Day2/                     # CatBoost Regressor (R²=0.988) & LightGBM Quantile models (P10/P50/P90)
    ├── Day3/                     # LightGBM Lead Classifier (PR-AUC=0.562), K-Means Personas (k=4), SHAP
    ├── Day4/                     # FastAPI Serving, LangGraph 5-Tool Assistant, Streamlit Dashboard
    └── Day5/                     # Evidently AI drift monitoring, champion/challenger retraining pipeline
```

---

## 2. Sequence Diagrams

### Sequence 1: Incoming Customer Phone Call & Voice Loop

```mermaid
sequenceDiagram
    autonumber
    actor Caller as 👤 Customer
    participant Vapi as 📞 Vapi Telephony
    participant Nova3 as 🎙️ Deepgram Nova-3 (Urdu ASR)
    participant Server as ⚡ FastAPI Voice Server
    participant Guard as 🛡️ Input Security Guardrail
    participant Graph as 🧠 LangGraph StateGraph
    participant TTS as 🔊 Vapi Voice (Elliot)

    Caller->>Vapi: Speaks in Urdu / Roman Urdu ("Assalam-o-Alaikum...")
    Vapi->>Nova3: Stream raw audio frames
    Nova3-->>Vapi: High-accuracy Roman Urdu transcript
    Vapi->>Server: POST /vapi/llm/chat/completions (OpenAI SSE format)
    Server->>Guard: Scan for prompt injections, jailbreaks, SQLi
    alt Threat Detected
        Guard-->>Server: [UNSAFE] Adversarial probe detected
        Server-->>Vapi: SSE Stream: "Main sirf RealEstate Hub ke mutabiq madad kar sakta hoon."
    else Input Clean
        Guard-->>Server: [SAFE] Verified clean input
        Server->>Graph: run_agent_turn(user_message, current_state)
        Graph->>Graph: Execute Intent Detection & Node Routing
        Graph-->>Server: updated_state (final_response in UrduLish)
        Server->>Server: Run Output Guardrail (Token/Secret Redactor)
        Server-->>Vapi: SSE Stream chunks (TTFB < 50ms)
        Vapi->>TTS: Stream text to speech synthesizer
        TTS-->>Caller: Natural spoken Pakistani Urdu audio
    end
```

---

### Sequence 2: Property Search & Recommendation

```mermaid
sequenceDiagram
    autonumber
    actor Caller as 👤 Customer
    participant Graph as 🧠 RecommendationNode
    participant SearchTool as 🔍 PropertySearchTool
    participant DB as 🗄️ SQLite realestate_kb.db
    participant ValEngine as 📈 CatBoost Valuation Engine

    Caller->>Graph: "DHA Phase 6 mein 10 Marla ghar chahiye 4 crore tak"
    Graph->>Graph: Extract: City=Lahore, Locality=DHA Phase 6, Size=10 Marla, Budget=4 Crore
    Graph->>SearchTool: search_properties_core(city="Lahore", max_budget=40000000, size=10)
    SearchTool->>DB: SELECT * FROM properties WHERE city='Lahore' AND price <= 40000000...
    DB-->>SearchTool: Return matching verified records (e.g. PROP-1042)
    SearchTool->>ValEngine: evaluate_property(prop_data, listed_price=38000000)
    ValEngine-->>SearchTool: Fair Value: 3.75 Cr, Range: 3.50-4.00 Cr, Verdict: Fair Market Price
    SearchTool-->>Graph: Verified listing with valuation verdict & amenity ranking
    Graph-->>Caller: "DHA Phase 6 mein hamare pas 10 Marla ghar 3.8 crore mein mojood hai jo fair market price par hai..."
```

---

### Sequence 3: Property Visit Scheduling & Anti-Double-Booking

```mermaid
sequenceDiagram
    autonumber
    actor Caller as 👤 Customer
    participant Graph as 🧠 BookingNode
    participant AvailTool as 🛡️ AvailabilityTool
    participant CalTool as 📅 CalendarTool
    participant CRMTool as 🏢 CRMTool
    participant LeadEngine as 🎯 LeadScoringEngine
    participant EmailTool as 📧 EmailTool

    Caller->>Graph: "Kal dopehar 3 baje visit rakh lein, mera naam Hamza hai (0300-8877665)"
    Graph->>AvailTool: check_slot_availability(date="Tomorrow", time="3:00 PM", agent="Ahmed Raza")
    alt Slot Already Booked / Outside Hours (9 AM - 7 PM)
        AvailTool-->>Graph: [UNAVAILABLE] Slot conflict
        Graph-->>Caller: "Maaf kijiye ga, 3 baje agent busy hain. Kya 4:00 PM ya 5:00 PM munasib rahe ga?"
    else Slot Verified Open
        AvailTool-->>Graph: [AVAILABLE] Slot open
        Graph->>CalTool: create_event(client="Hamza", prop_id="PROP-1042", time="3:00 PM")
        CalTool-->>Graph: google_calendar_link & .ics payload
        Graph->>LeadEngine: score_lead(calls=2, visit_booked="Yes", budget=38000000)
        LeadEngine-->>Graph: Priority: [HOT] (88.5%), Persona: Serious First-Time Homebuyer, SLA: 1h
        Graph->>CRMTool: upsert_lead_and_appointment(lead_data, priority="HOT", persona=...)
        CRMTool-->>Graph: Appointment ID #APT-8821 confirmed
        Graph->>EmailTool: send_appointment_confirmation(client_email, agent_email, details)
        EmailTool-->>Graph: Email dispatched
        Graph-->>Caller: "Aap ki visit kal 3:00 PM confirm ho chuki hai. Senior agent Ahmed Raza aap se rabta karein ge."
    end
```

---

### Sequence 4: Rescheduling or Cancellation

```mermaid
sequenceDiagram
    autonumber
    actor Caller as 👤 Customer
    participant Graph as 🧠 Reschedule / Cancel Node
    participant CRMTool as 🏢 CRMTool
    participant CalTool as 📅 CalendarTool

    Caller->>Graph: "Kal wali visit cancel kar dein" / "Time change karke 5 baje kar dein"
    Graph->>CRMTool: lookup_active_appointment(phone=caller_phone)
    CRMTool-->>Graph: Found APT-8821 for PROP-1042
    alt Intent: Cancellation
        Graph->>CRMTool: update_status(APT-8821, status="cancelled")
        Graph->>CalTool: cancel_event(event_id)
        Graph-->>Caller: "Aap ki visit cancel kar di gayi hai. Agar koi aur property dekhni ho toh zaroor bataiye ga."
    else Intent: Rescheduling
        Graph->>CRMTool: update_slot(APT-8821, new_time="5:00 PM")
        Graph->>CalTool: reschedule_event(event_id, new_time="5:00 PM")
        Graph-->>Caller: "Aap ki visit kal shaam 5:00 PM par reschedule kar di gayi hai."
    end
```

---

### Sequence 5: Telephony & Integration Failure Fallback

```mermaid
sequenceDiagram
    autonumber
    actor Caller as 👤 Customer
    participant Server as ⚡ FastAPI Engine
    participant Fallback as 🔄 Resilient Fallback Handler
    participant Logger as 📝 Audit & Trace Logger

    Caller->>Server: Request tool execution (e.g. SMTP or Database disconnect)
    Server->>Server: Execute external integration with timeout (2500ms)
    alt Timeout / Connection Refused
        Server->>Logger: Log error code INT-503 (Database/Provider timeout)
        Server->>Fallback: Trigger graceful degraded mode
        Fallback-->>Server: Cached offline listing / queued manual callback record
        Server-->>Caller: "Hamare system mein thora waqti masla aya hai, lekin maine aap ki inquiry note kar li hai aur agent foran rabta kare ga."
    end
```

---

### Sequence 6: Week 8 Real-Time Valuation & Lead Triage Workflow

```mermaid
sequenceDiagram
    autonumber
    actor SalesAgent as 🧑‍💼 Sales Agent / Voice Caller
    participant Assistant as 🤖 Unified AI Assistant
    participant ValTool as 🏷️ PropertyValuationTool
    participant LeadTool as 🎯 LeadScoringTool
    participant SHAPTool as 🔍 SHAPExplainerTool
    participant DB as 🗄️ SQL DB & Audit Log

    SalesAgent->>Assistant: "Mera DHA Phase 6 mein 1 kanal ghar kitne ka bikega?"
    Assistant->>ValTool: predict_price(city="Lahore", locality="DHA Phase 6", size=20)
    ValTool->>ValTool: CatBoost Model + LightGBM Quantile Bands (P10, P50, P90)
    ValTool-->>Assistant: Price: 6.98 Cr, Range: 6.63 Cr – 7.94 Cr
    Assistant->>SHAPTool: explain_price(prop_features)
    SHAPTool-->>Assistant: Drivers: plot_size_marla (+42%), locality (+31%), age_years (-8%)
    Assistant-->>SalesAgent: "Model ke mutabiq iski fair market value 6.63 se 7.94 crore ke darmiyan hai..."
    
    Note over Assistant,DB: After call termination, transcript is sent to Webhook
    Assistant->>LeadTool: score_lead(transcript_features)
    LeadTool-->>DB: Priority: HOT, Score: 87.1%, Persona: Serious Buyer, Trigger Webhook to Sales Team
```

---

## 3. Database Schema Overview (`realestate_kb.db`)

The SQLite database contains 13 relational tables:
1. `properties`: 750 records with `property_id`, `city`, `location`, `price`, `property_type`, `plot_size_marla`, `bedrooms`, `baths`, `is_active`.
2. `locations`: 18 prime societies (DHA, Bahria, Gulberg, F-11, etc.) with development status and average marla rate.
3. `amenities`: 151 amenities linked by property identifier.
4. `developers`: 18 established builders with NOC accreditation.
5. `schools` & `hospitals`: Proximity infrastructure records.
6. `faqs`: 20 verified legal, tax (FBR), and society transfer procedures.
7. `agents`: 8 accredited human consultants with assignment schedules.
8. `crm_leads`: Captured customer leads with phone numbers and budgets.
9. `crm_appointments`: Time-slotted property viewing schedules.
10. `conversations`: Turn-by-turn transcribed dialogue history.
11. `training_data`: Continual learning dataset for periodic intent retraining.
