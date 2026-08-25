"""Test user's specific prediction queries."""
from langgraph_afl_agent import afl_app

queries = [
    "according to previous stats, which team will have most chances to win the AFL final in upcoming season",
    "making a prediction for 2027 season"
]

BLANK = {
    "user_query": "", "messages": [], "detected_intent": "", "entities": {},
    "tool_results": {}, "validation_status": "", "clarification_prompt": None, "final_response": ""
}

print("=" * 80)
for q in queries:
    state = {**BLANK, "user_query": q}
    res = afl_app.invoke(state)
    print("Q:", q)
    print("Detected Intent:", res["detected_intent"])
    print("Response:\n", res["final_response"])
    print("=" * 80)
