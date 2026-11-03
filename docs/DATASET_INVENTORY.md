# 📊 Dataset Inventory & Data Governance Runbook

**System:** RealEstate Hub Unified Platform  
**Data Custodian:** ML & Data Architecture Team  
**Audit Date:** September 30, 2026  

---

## 1. Authoritative Datasets Inventory

| Dataset Name | File Path & Format | Primary Key & Rel | Row / Doc Count | Data Freshness | Purpose | Consuming Modules | Status | Safe to Delete? |
|---|---|---|---|---|---|---|---|---|
| **Authoritative Knowledge Base** | `week7-RE_Agent/day5-langgraph-agent/db/realestate_kb.db` (SQLite) | `property_id`, `location_id`, `agent_id` | 750 Properties, 18 Locations, 151 Amenities, 20 FAQs, 8 Agents | Verified Q3 2026 | Production | `search_tools.py`, `availability_tools.py`, `crm_tools.py` | `KEEP` | ❌ **NEVER** (Authoritative DB) |
| **Cleaned Property Listings** | `week8/Day1/data/processed/cleaned_properties.csv` (CSV) | `property_id` | 5,000 records (1.7 MB) | Verified Q3 2026 | ML Training | `feature_engineering.py`, `property_inference.py`, CatBoost Model | `KEEP` | ❌ **NEVER** (Baseline Model Data) |
| **Cleaned Inbound Leads** | `week8/Day1/data/processed/cleaned_leads.csv` (CSV) | `lead_id` | 3,500 records (618 KB) | Verified Q3 2026 | ML Training | `lead_inference.py`, LightGBM Lead Classifier, K-Means | `KEEP` | ❌ **NEVER** (Classification Baseline) |
| **Property Train/Val/Test Splits** | `week8/Day1/data/processed/properties_{train,val,test}.csv` | `property_id` | 3,500 train / 750 val / 750 test (70/15/15) | Verified | ML Evaluation | Model evaluation & regression test suites | `KEEP` | ❌ **NO** (Benchmark integrity) |
| **Lead Train/Val/Test Splits** | `week8/Day1/data/processed/leads_{train,val,test}.csv` | `lead_id` | 2,450 train / 525 val / 525 test (70/15/15) | Verified | ML Evaluation | PR-AUC benchmarks & persona clustering | `KEEP` | ❌ **NO** (Evaluation benchmark) |
| **Raw Unprocessed Properties** | `week8/Day1/data/raw/raw_properties.csv` (CSV) | Implicit index | 5,200 records (1.1 MB) | Raw source | Ingestion pipeline | `Day1/src/data_cleaning.py` | `KEEP` | ❌ **NO** (Represents raw raw feed) |
| **Raw Unprocessed Leads** | `week8/Day1/data/raw/raw_leads.csv` (CSV) | Implicit index | 3,600 records (455 KB) | Raw source | Ingestion pipeline | `Day1/src/data_cleaning.py` | `KEEP` | ❌ **NO** (Represents raw raw feed) |
| **Multi-Turn Voice Eval Suite** | `week7-RE_Agent/day6-evaluation-security/eval_suite/test_conversations.json` (JSON) | `conversation_id` | 46 Dialogues (184 turns) | Curated | Production QA | `eval_runner.py`, `benchmark_engine.py` | `KEEP` | ❌ **NEVER** (Regression test ground truth) |
| **Locality RAG Vector Store** | `week7-RE_Agent/realestate-hub/data/vectorstores/chroma_db` (ChromaDB) | Document chunk ID | 150 embedded chunks | Embedded via `all-MiniLM-L6-v2` | RAG Retrieval | `rag_tools.py`, `rag_node.py` | `KEEP` | ⚠️ **Can be rebuilt** from `faqs` and `locations` tables |

---

## 2. Data Governance & Ingestion Pipelines

### A. Property Data Dictionary
* `price_pkr` (float): Property transaction price in Pakistani Rupees (authoritative ground truth).
* `plot_size_marla` (float): Standardized land surface area in Marlas ($1\text{ Kanal} = 20\text{ Marlas}$).
* `city` (string): Target urban center (Lahore, Karachi, Islamabad, Rawalpindi, Faisalabad, Peshawar).
* `locality` (string): Housing society / sector (e.g., DHA Phase 6, Bahria Town, Gulberg III, F-11).
* `property_type` (string): House, Flat, Upper Portion, Lower Portion, Plot, Commercial.
* `price_per_marla` (float): Engineered metric normalized against locality median price.
* `age_years` (int): Structural age of the building ($0\text{ years} = \text{Brand New}$).

### B. Lead Data Dictionary
* `converted` (int): Ground truth binary label ($1 = \text{Purchased/Leased}, 0 = \text{Abandoned}$).
* `lead_engagement_score` (float): $\text{calls} \times \text{avg\_call\_duration\_mins}$.
* `interaction_intensity` (float): $\frac{\text{calls}}{\text{days\_since\_first\_contact} + 1}$.
* `response_speed_category` (string): Immediate ($<15\text{m}$), Fast ($15\text{-}60\text{m}$), Standard ($1\text{-}6\text{h}$), Slow ($>6\text{h}$).
* `objection_raised` (string): None, Price too high, Low trust in scheme/NOC, Location too far, Waiting for family approval.

---

## 3. Backup & Regeneration Procedures

1. **Database Snapshot**:
   ```powershell
   # Backup SQLite database prior to migration
   Copy-Item -Path "week7-RE_Agent/day5-langgraph-agent/db/realestate_kb.db" -Destination "week7-RE_Agent/day5-langgraph-agent/db/realestate_kb_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
   ```
2. **Deterministic Data Pipeline Re-execution**:
   To reproduce the cleaned datasets from raw sources:
   ```bash
   python week8/Day1/run_day1.py
   ```
   This performs idempotent cleaning, IQR outlier filtering, domain feature engineering, and stratified train/val/test splitting.
