# 🧠 Continual Learning Layer (Day 5.5)

Makes the agent **actually get better at intent detection the more it's used** —
without touching the reliability of the existing rule-based routing, and
without any risk of a live call breaking because a model failed to load.

## Why this exists

`nodes/intent_detection_node.py`'s `_classify_intent()` is a large hand-tuned
set of keyword/regex rules (English + Roman Urdu + Urdu script, including
Deepgram phonetic mis-transcriptions like `"ریس کے جول"` for "reschedule").
That's great for the high-precision cases, but anything that doesn't match
a rule just falls through to `"recommendation"` by default — a silent guess.

This layer replaces that silent guess with a small ML classifier trained on
your own real call data, and keeps it improving as more calls come in.

## How it works

```
Every call turn                    Nightly / weekly (NOT per call)
──────────────                     ─────────────────────────────
intent_detection_node()   ──log──> learning/data/intent_training_log.jsonl
        │                                        │
        │ (rule engine decides intent,           │ python -m learning.train_intent_classifier
        │  as it always has)                     ▼
        │                          TF-IDF + LogisticRegression, trained on
        │                          every logged example, evaluated on a
        │                          held-out split
        │                                        │
        │                          new model only "promoted" (i.e. used
        │                          live) if accuracy >= current model
        │                                        │
        ▼                                        ▼
_classify_intent() rules      <──── learning/models/current_model.json
match? use that intent.              (pointer to the latest promoted .joblib)
No match? ask the ML model
for its best guess (only used
if confidence >= 0.55).
Still no answer? "recommendation"
(same safe default as before).
```

Key design choices, and why:

- **Rules are never overridden.** The ML model is only ever consulted as the
  very last fallback, after every keyword rule (cancellation, reschedule,
  off-topic, booking, email, RAG, greeting) has already failed to match. It
  can only replace the old "just guess `recommendation`" behavior — it can
  never hijack a booking or cancellation.
- **Batch retraining, not online learning.** Every call is logged instantly,
  but the model itself is retrained on a schedule (see below), not after
  every single call. This is standard practice: it's cheap, easy to audit,
  and you can always see exactly what data produced the current model.
- **Auto-promotion is regression-safe.** `train_intent_classifier.py` never
  overwrites a better model with a worse one — it compares accuracy on a
  held-out split and only updates `current_model.json` if the new model is
  at least as good.
- **Fails soft, everywhere.** If `scikit-learn` isn't installed, or no model
  has been trained yet, `learning.intent_classifier.predict()` returns
  `(None, 0.0)` and the agent silently falls back to its old behavior. A
  learning-layer bug can never take down a live call.

## Setup

```bash
pip install -r learning/requirements-learning.txt   # scikit-learn, joblib
```

Nothing else to configure — `nodes/intent_detection_node.py` already logs
every turn and consults the model automatically.

**Note on existing history:** the trace files already in `traces/` don't
store the raw utterance text (only structured state diffs), so the training
log starts fresh from whenever this feature is deployed — the model learns
from calls going forward, not retroactively from your Sept 1 test traces.

## Running it

```bash
# Check how much data has been collected
python -c "from learning.dataset import dataset_stats; print(dataset_stats())"

# Retrain (safe to run any time; no-ops with a clear message if there isn't
# enough data yet — needs 40+ examples across at least 2 intents by default)
python -m learning.train_intent_classifier
```

### Bootstrapping data without spending Vapi minutes

You don't need real phone calls to get past the 40-example minimum.
`agent_cli.py` and `vapi_server.py` both call the exact same
`intent_detection_node()` — Vapi/Deepgram is only the voice layer sitting
in front of it, and that's the only part that costs minutes. So:

```bash
# Free: talk to the agent over plain text in your terminal
python agent_cli.py

# Free and fast: runs realistic sample phrasings through the REAL rule
# engine (not fake labels) to seed the log quickly
python -m learning.seed_training_data --count 40
```

`seed_training_data.py` is meant to get you past the minimum quickly and to
show you which phrasings your rule engine does/doesn't catch — check the
resulting `label_counts` after running it, since any intent your rules
don't recognize well will show up under-represented (or absent) rather than
mislabeled. Treat it as a bootstrap, not a replacement for real call data —
extend `SAMPLE_UTTERANCES` in that file with your actual callers' phrasing
for the best results, and keep collecting real data once you're deployed.

### Scheduling periodic retraining

Pick whichever fits your deployment:

**Cron (Linux/Mac server):**
```cron
0 3 * * *  cd /path/to/day5-langgraph-agent && /path/to/venv/bin/python -m learning.train_intent_classifier >> learning/retrain.log 2>&1
```

**Windows Task Scheduler:** create a daily task running
`python -m learning.train_intent_classifier` with "Start in" set to the
`day5-langgraph-agent` folder.

**GitHub Actions (if you centralize retraining in CI, like `day6`'s
`ci_cd.yml`):** add a `schedule:` trigger (`cron: '0 3 * * *'`) that checks
out the repo, installs `learning/requirements-learning.txt`, runs the
training script, and commits the updated `learning/models/` folder.

## Files

| File | Purpose |
|---|---|
| `dataset.py` | Appends every real turn to the training log; loads/summarizes it. |
| `train_intent_classifier.py` | Batch retraining script — run this periodically, not per call. |
| `intent_classifier.py` | Loads the currently promoted model; used by `intent_detection_node.py`. |
| `data/intent_training_log.jsonl` | Growing dataset of `(utterance, intent, session_id, timestamp, ...)`. |
| `models/current_model.json` | Pointer to the currently promoted model + its accuracy/training metadata. |
| `models/intent_clf_<timestamp>.joblib` | Every trained model, kept for rollback/audit. |

## Rolling back a bad model

Every trained model stays on disk. To roll back, just hand-edit
`learning/models/current_model.json`'s `"model_path"` to point at an older
`.joblib` file (or delete `current_model.json` entirely to disable the ML
fallback and go back to pure rule-based routing).

## Honest limitations (read before demoing this as "self-learning AI")

- The very first model is trained on labels the **rule engine itself**
  produced — it's a distillation of the rules on real phrasing, not a
  human-verified ground truth. That's normal and useful (it learns to
  generalize the rules to phrasing you didn't think to hardcode), but it
  means it can also learn a rule's mistakes.
- There's no correction UI yet. If you want real supervised improvement over
  time, add a way to mark a past turn's intent as wrong (e.g. an admin
  endpoint or a CRM note) and log those as `source="human_correction"` rows
  — `dataset.log_training_example(..., source="human_correction")` already
  supports this; the trainer treats all rows the same today, but you could
  later weight human-corrected rows higher.
- This only touches **intent classification**. It doesn't change entity
  extraction, recommendation ranking, or RAG retrieval — extending the same
  pattern (log → batch retrain → fallback) to those is a separate, larger
  piece of work if you want it later.
