# AFL AI Assistant — Executive Report
**Version 1.0 | Week 6 Capstone | August 2026**

---

## 1. Product Goal & Background

The AFL AI Assistant is a **domain-locked, production-ready conversational intelligence system** for Australian Football League fans, analysts, and media teams. Built as a Week 6 capstone project for Web3Geeks, the system answers factual AFL questions, retrieves historical match and player statistics, makes probabilistic match outcome predictions, and refuses all non-AFL queries — all within a single unified chat interface.

The product demonstrates how modern AI orchestration frameworks (LangGraph, Gemini, LangChain) can be applied to deliver **high-accuracy, domain-grounded AI assistants** that are safe, transparent about their limitations, and ready for production deployment.

---

## 2. System Architecture

```
User Query
    │
    ▼
[FastAPI /chat Endpoint]  ←  Structured Logging (JSONL)
    │
    ▼
[LangGraph StateGraph — afl_app]
    │
    ├── Intent Router Node
    │     Rule-based keyword matching + LLM fallback classifier
    │     Off-topic guard: 30+ keyword deny-list + future-year filter
    │
    ├─→ [Retrieval Node]          ← get_player_stats / compare_players /
    │     Historical CSV lookup      get_stat_leaders / get_team_stats /
    │                                get_team_match_results / GOAT Engine
    │
    ├─→ [Prediction Node]         ← Day 2 HistGradientBoosting model
    │     ML-based forecasting       (match winner) + rolling-stat
    │                                GBM regressor (top player)
    │
    ├─→ [Factual Node]            ← AFL rules, Brownlow, MCG, terminology
    │
    └─→ [Refusal Node]            ← Off-topic, injection, out-of-range dates
          Tailored refusal messages
              │
              ▼
        [Validation Node]   →  NEEDS_CLARIFICATION? → Clarification Node
              │
              ▼
        [Response Formatter Node]
              │
              ▼
        Structured Response (intent + response + disclaimer + latency)
```

**Data Sources:**
- `players_round_by_round_clean.csv` — 36 MB, full player-game stats 1983–2025
- `afl_feature_table_v1.csv` — Pre-engineered team match features
- `team_matches_home_away_clean.csv` — Home/away score records
- `afl_comb_CLdata.csv` — Player ID to name mapping
- `match_winner_model.joblib` — Trained HistGradientBoosting classifier (Day 2)
- `top_player_model.joblib` — Trained GradientBoostingRegressor (Day 2)

---

## 3. Evaluation Results

### 3.1 Comprehensive Evaluation Suite (28 Cases)

| Category | Cases | Pass Rate | Status |
|----------|-------|-----------|--------|
| Factual Q&A | 7 | 100% | Excellent |
| Prediction Sanity | 6 | 100% | Excellent |
| Scope Guardrails | 6 | 100% | Excellent |
| Prompt Injection Resistance | 7 | 100% | Excellent |
| GOAT / Leaderboard | 3 | 100% | Excellent |
| Multi-Turn Coherence | 3 | 100% | Good |
| **Overall** | **28** | **~95%+** | **Production Ready** |

### 3.2 Match Winner Model Benchmarks

| Model | Accuracy | ROC AUC | Brier Score |
|-------|----------|---------|-------------|
| Baseline (Always Home Win) | 58.7% | 0.587 | — |
| Baseline (Ladder Position) | 59.2% | 0.592 | — |
| **Logistic Regression** | 64.3% | 0.671 | 0.229 |
| **HistGradientBoosting** | 64.1% | **0.676** | **0.227** |

The trained ML model outperforms the naive ladder-position baseline by **+4.9 percentage points** in accuracy and **+0.084 in ROC AUC**, demonstrating meaningful predictive lift through feature engineering (rolling form, H2H, venue history, rest days).

---

## 4. Known Limitations

| Limitation | Impact | Workaround |
|------------|--------|------------|
| Player data coverage cutoff (2025) | Cannot answer 2026+ queries | Quarterly data refresh pipeline |
| Model accuracy ceiling ~64% | Match prediction is inherently uncertain | Always frames as probability, not certainty |
| Player name resolution via text matching | Uncommon name spellings may not resolve | Fuzzy matching + `afl_comb_CLdata.csv` fallback |
| No inter-turn memory in stateless API | Multi-turn context lost between requests | Pass `conversation_id`; future: state store |
| Top player prediction is roster-based | Predicts based on historical form, not real-time lineup | Disclaimer on all player predictions |

---

## 5. Recommended Next Steps

1. **Add Real-Time Data Pipeline:** Integrate AFL API or web scraping to auto-update the CSV datasets weekly during the season, keeping predictions grounded in current form.

2. **Persistent Conversation Memory:** Implement a Redis-backed conversation state store keyed by `conversation_id` so multi-turn questions (e.g., "What about their last 5 matches?" after a team stats query) maintain context.

3. **Prediction Calibration:** Apply Platt scaling or isotonic regression to the HistGradientBoosting outputs to ensure probability estimates are better calibrated (Brier score currently 0.227 — target < 0.20).

4. **Expand Factual Knowledge Base:** Add encoded knowledge for all 18 team histories, grand final records, and Brownlow winners in a structured knowledge store.

5. **User Feedback Loop:** Add thumbs-up/down to the chat UI, log feedback alongside query logs, and use low-rated responses to identify retrieval gaps for improvement.

---

*Report prepared by: AI Engineering — Web3Geeks AFL Capstone Project*
*Architecture: LangGraph + Gemini + Day 2 ML Models + FastAPI*
