"""Test user edge case queries."""
from langgraph_afl_agent import afl_app

queries = [
    "What is Carlton's win rate against Collingwood in away games?",
    "What happened between Brisbane and Sydney?",
    "will Patrick Cripps dominate next week?",
    "Who won the AFL Grand Final in 1950",
    "Give me a prediction and some stats about the Swans."
]

BLANK = {
    "user_query": "", "messages": [], "detected_intent": "", "entities": {},
    "tool_results": {}, "validation_status": "", "clarification_prompt": None, "final_response": ""
}

for q in queries:
    state = {**BLANK, "user_query": q}
    res = afl_app.invoke(state)
    print("Q:", q)
    print("Intent:", res["detected_intent"])
    print("Ans:", res["final_response"][:180])
    print("-" * 60)
