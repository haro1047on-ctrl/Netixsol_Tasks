# Enterprise Roadmap: Future Architectural Enhancements

This document details the architectural roadmaps and technical specifications for scaling the Real Estate AI Platform into a commercial, multi-modal enterprise system.

---

## 1. Multi-Modal Image-Based Valuation via Computer Vision (CNN / Vision Transformers)

### Problem Statement
Current tabular models rely on self-reported inputs (e.g. `age_years`, `amenity_score`), missing nuanced architectural finishes, aesthetic quality, and physical structural wear.

### Technical Architecture
- **Backbone Architecture:** Fine-tuned Vision Transformer (ViT-B/16) or EfficientNet-V2.
- **Input Pipeline:** Ingests up to 10 listing photographs (Elevation/Frontage, Kitchen, Master Bathroom, Living Lounge, Flooring).
- **Multi-Modal Fusion:** Late fusion architecture combining:
  1. Dense image feature embeddings ($D=512$).
  2. Tabular engineered features from CatBoost.
  3. Joint regression head with cross-attention layers.
- **Business Impact:** Accurately prices luxury finishes (Spanish tiles, imported sanitary ware, false ceilings), reducing valuation MAPE on the luxury segment ($>4\text{ Crore}$) from **8.15% down to $<4.5\%$**.

---

## 2. Micro-Market Time-Series Price Forecasting (Prophet / Temporal Fusion Transformers)

### Problem Statement
Property buyers, overseas investors, and developers frequently ask: *"Agley 6 mahinay mein is society mein kitna appreciation expected hai?"*

### Technical Architecture
- **Modeling Framework:** Temporal Fusion Transformer (TFT) or Prophet with macroeconomic regressors (KIBOR interest rates, construction material CPI, cement index).
- **Granularity:** 1-month to 24-month ahead forecasting per residential society (e.g., DHA Phase 6 vs Bahria Town).
- **Deliverables:**
  - Automated appreciation forecast curve with $80\%$ and $95\%$ confidence intervals.
  - Investment Scorecard ranking societies by expected 12-month capital gain.

---

## 3. Two-Tower Recommendation Engine for Property-Buyer Matching

### Problem Statement
Sales agents manually search portal listings to match buyer inquiries, resulting in mismatched suggestions and slow deal progression.

### Technical Architecture
- **Two-Tower Deep Neural Network:**
  - **User Tower:** Embeds client stated budget, preferred city, required bedrooms, customer persona, and interaction history.
  - **Property Tower:** Embeds property attributes, location embeddings, and visual features.
- **Real-Time Vector Retrieval:** Milvus or Qdrant vector database performing sub-10ms Approximate Nearest Neighbor (ANN) search over 100,000 active listings.
- **Business Impact:** Automatically sends the top 3 best-matched properties via WhatsApp within 60 seconds of a caller completing an inquiry.

---

## 4. Native WhatsApp Business API Lead Scoring Bot

### Problem Statement
Over 65% of Pakistani real estate transactions originate on WhatsApp, but leads sit unreviewed in agent chat windows for hours.

### Technical Architecture
- **Meta WhatsApp Cloud API Webhook:** Ingests incoming WhatsApp messages in real-time.
- **FastAPI Scoring Pipeline:** Evaluates conversation urgency, stated budget, and response latency.
- **Automated Interaction Flow:**
  - If lead scores **🔥 Hot**: Instantly routes the conversation to a Senior Closer and triggers an urgent push notification.
  - If lead scores **🌤 Warm**: AI bot continues qualification conversation in UrduLish, sending PDF property brochures.

---

## 5. Multi-Touch Automated Follow-Up Drip Engine

### Problem Statement
Cold leads ($p < 0.35$) are discarded, yet 15-20% of cold prospects convert 3 to 6 months later after saving capital.

### Technical Architecture
- **Stateful Drip Engine:** LangGraph / Celery recurring workflow.
- **Cadence:**
  - Day 3: Market price update in preferred society.
  - Day 7: New listing alert matching stated budget.
  - Day 14: Automated re-scoring check. If client responds with interest, lead is dynamically promoted from ❄️ Cold to 🌤 Warm or 🔥 Hot.

---

## 6. Enterprise Bi-Directional CRM Connectors (HubSpot & Salesforce)

### Problem Statement
Real estate brokerages rely on centralized CRMs; models must sync predictions directly into existing agent workflows.

### Technical Architecture
- **HubSpot / Salesforce REST API Webhooks:**
  - On deal creation: Ingests CRM deal record, calls `/predict/lead-score`, and writes back custom fields: `ml_conversion_probability`, `ml_priority_badge`, `ml_customer_persona`, `ml_recommended_sla`.
  - Automatic task creation in Salesforce for High-Priority deals assigned to the designated closer with a 60-minute countdown timer.
