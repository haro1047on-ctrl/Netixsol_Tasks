# AFL AI Assistant — Monitoring & Maintenance Plan

**System:** AFL Chat + Prediction Assistant (LangGraph + Gemini + FastAPI)
**Environment:** Production / Staging
**Owner:** AI Engineering Team
**Cadence:** Weekly review, monthly model audit

---

## 1. Metrics to Track

| Metric | Source | Tool | Alert Threshold |
|--------|--------|------|-----------------|
| Response latency p50 | API logs (`logs/afl_api_structured.jsonl`) | Log aggregation | > 2 000 ms |
| Response latency p95 | API logs | Log aggregation | > 5 000 ms |
| Tool invocation error rate | API logs (`tools_called` vs error flag) | Log aggregation | > 5% |
| Off-topic leak rate | Intent log distribution | Weekly query audit | > 2% of total queries |
| Prediction probability plausibility | Manual spot-check | Human review | p(winner) < 50% on heavy favourite |
| Retrieval "not found" rate | Response text pattern match | Log scan | > 10% of retrieval queries |
| Abuse flag rate | `check_abuse()` trigger rate | API logs | > 3 conversations flagged/day |
| API uptime | Health endpoint `/health` | Uptime monitor | < 99.5% weekly |

---

## 2. Alert Thresholds & Actions

| Condition | Action |
|-----------|--------|
| `latency_p95 > 5 000 ms` | Check Gemini API quota; consider response caching for frequent queries |
| `tool_error_rate > 5%` | Inspect CSV dataset integrity; re-run dataset validation scripts |
| `off_topic_leak_rate > 2%` | Audit `_OFF_TOPIC_KEYWORDS` list; add newly detected bypass phrases |
| `retrieval_not_found_rate > 10%` | Check `resolve_player()` and `resolve_team()` matching; review player name mappings |
| `prediction_drift detected` | Trigger model retraining (see Section 4) |

---

## 3. Weekly Query Audit Checklist

Each Monday, sample 20 random queries from the JSONL log and check:

- [ ] All `off_topic` intents returned appropriate refusal messages
- [ ] No non-AFL content appeared in `prediction` or `retrieval` responses
- [ ] Prediction probabilities are within [45%, 75%] for most matchups (extreme values flag model issues)
- [ ] All prediction responses contain the disclaimer phrase "predicted probability, not a certainty"
- [ ] No `player_stats` responses returned raw query strings as player name (old bug pattern)
- [ ] Latency p95 within threshold
- [ ] No new injection bypass patterns identified in queries

---

## 4. Weekly Retraining / Refresh Loop

**Trigger:** New AFL round results become available (weekly during season)

### Step 1 — Update Raw Data
```bash
# Append new match results to the feature table source data
# (home/away match records, player round-by-round stats)
python update_data.py --round 15  # hypothetical data pipeline
```

### Step 2 — Rebuild Feature Table
```bash
# Re-run Day 2 Jupyter notebook feature engineering cells
# OR run the standalone feature builder script
python rebuild_features.py
```

### Step 3 — Retrain Match Winner Model
```bash
cd week6/Day2
python train_match_winner.py  # re-trains and saves match_winner_model.joblib
```

### Step 4 — Evaluate Against New Holdout
```bash
python eval_suite.py   # confirm >= 80% overall pass rate still holds
```

### Step 5 — Deploy
```bash
# Restart API server to reload updated joblib model
uvicorn afl_api:app --host 0.0.0.0 --port 8000 --reload
```

**Retrain Trigger Conditions (beyond weekly):**
- Prediction accuracy on recent rounds drops below 55% for 3 consecutive rounds
- A new team enters the competition or team name changes
- Major squad changes (trades, drafts) affect player roster completeness

---

## 5. Model Review Cadence

| Frequency | Activity |
|-----------|----------|
| Weekly | Data refresh + feature table update |
| Monthly | Full model accuracy audit vs real round results |
| End of Season | Full retrain on complete season data |
| Pre-Finals | Retrain including finals momentum features |

---

## 6. Known Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Player name changes / transfers | Rebuild `afl_comb_CLdata.csv` mapping after every trade period |
| New team or rebranding | Update `TEAM_ALIASES` dict and `valid_teams.csv` |
| Gemini API rate limiting | Rate-limit retry with exponential backoff already in `AFLChatAgent._safe_invoke_llm()` |
| Dataset staleness beyond 2025 | Update `max_year` in `_validate_date()` and add new season data |
| Embedding drift in LLM intent classifier | Re-evaluate router accuracy quarterly with `test_task2_router.py` |
