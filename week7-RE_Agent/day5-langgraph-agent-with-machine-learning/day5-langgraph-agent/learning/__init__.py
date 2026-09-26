"""Day 5.5: Continual Learning Layer for the LangGraph Agent.

This package lets the agent learn from every real call and get better at
intent detection over time, without touching the core graph's reliability.

Flow:
    1. Every turn, `dataset.log_training_example(...)` appends one row to
       `learning/data/intent_training_log.jsonl` (the growing "memory" of
       every call the agent has ever handled).
    2. Periodically (nightly / weekly, NOT on every call), you run
       `python -m learning.train_intent_classifier` which retrains a
       classifier on the accumulated log and only "promotes" the new
       model if it is at least as accurate as the current one.
    3. `intent_classifier.predict(text)` loads the currently promoted
       model and is consulted by `nodes/intent_detection_node.py` as a
       *fallback* — it never overrides the high-precision keyword rules
       (cancellation, reschedule, off-topic, booking, email, RAG). It only
       helps with the fuzzy cases the rules used to just default to
       "recommendation" for.

Nothing in this package can crash the agent: every public function fails
soft (logs a warning, returns None / does nothing) if scikit-learn isn't
installed or no model has been trained yet.
"""
