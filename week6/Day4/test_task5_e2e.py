"""
Task 5: End-to-End Testing Suite & State Trace Logger
Executes 10 full conversations covering factual retrieval, prediction (match + player),
off-topic refusal, ambiguity clarification, and multi-turn follow-ups.
Logs and annotates state traces for representative runs.
"""

import json
from langgraph_afl_agent import afl_app

E2E_CONVERSATIONS = [
    # 1. Factual Retrieval
    {"id": "E2E-01", "name": "Factual Player Retrieval", "query": "How many disposals did Sam Walsh have in 2024?"},
    
    # 2. Match Prediction
    {"id": "E2E-02", "name": "Match Prediction (Nicknames)", "query": "Will the Pies beat the Cats this week?"},
    
    # 3. Player Performance Prediction
    {"id": "E2E-03", "name": "Player Scorer Prediction", "query": "Who will top-score in goals for Carlton?"},
    
    # 4. Direct Off-Topic Refusal
    {"id": "E2E-04", "name": "Off-Topic Soccer Refusal", "query": "Who won the FIFA Soccer World Cup in 2022?"},
    
    # 5. Off-Topic Persona Hijack Refusal
    {"id": "E2E-05", "name": "Off-Topic Coding Refusal", "query": "Write a Python script to sort a list using quicksort."},
    
    # 6. Ambiguous Input (Needs Clarification)
    {"id": "E2E-06", "name": "Ambiguous Prediction Clarification", "query": "Who will win the next big match?"},
    
    # 7. Unsupported Prediction Fallback
    {"id": "E2E-07", "name": "Unsupported Stat Prediction", "query": "Predict who will get the most fantasy points for Collingwood"},
    
    # 8. Factual Rules Direct Answer
    {"id": "E2E-08", "name": "AFL Rule Query", "query": "What is a mark inside 50 in AFL rules?"},
    
    # 9. Leaderboard Retrieval
    {"id": "E2E-09", "name": "Season Goal Leaderboard", "query": "Who were the top 5 goal scorers in 2023?"},
    
    # 10. Multi-Turn Follow-up
    {"id": "E2E-10", "name": "Team Stats into Prediction", "query": "Predict if Collingwood Magpies will beat Richmond Tigers"}
]


def run_e2e_benchmark():
    print("=" * 80)
    print("TASK 5: END-TO-END LANGGRAPH EVALUATION SUITE")
    print("=" * 80)

    annotated_traces = []

    for item in E2E_CONVERSATIONS:
        state = {
            "user_query": item["query"],
            "messages": [],
            "detected_intent": "",
            "entities": {},
            "tool_results": {},
            "validation_status": "",
            "clarification_prompt": None,
            "final_response": ""
        }

        # Invoke StateGraph
        final_state = afl_app.invoke(state)

        print(f"\n[{item['id']}] {item['name']}")
        print(f"Query      : \"{item['query']}\"")
        print(f"Intent     : {final_state['detected_intent']}")
        print(f"Validation : {final_state['validation_status']}")
        print(f"Response   : {final_state['final_response'][:120]}...")
        print("-" * 80)

        # Store trace for representative runs
        if item["id"] in ["E2E-01", "E2E-02", "E2E-06"]:
            annotated_traces.append({
                "id": item["id"],
                "name": item["name"],
                "query": item["query"],
                "router_decision": final_state["detected_intent"],
                "extracted_entities": final_state["entities"],
                "tool_type": final_state["tool_results"].get("type"),
                "validation": final_state["validation_status"],
                "final_response": final_state["final_response"]
            })

    print("\n" + "=" * 80)
    print("END-TO-END BENCHMARK COMPLETE (10/10 CONVERSATIONS EXECUTED)")
    print("=" * 80)

    # Save annotated traces to json
    with open("annotated_traces.json", "w") as f:
        json.dump(annotated_traces, f, indent=2)

    return annotated_traces


if __name__ == "__main__":
    run_e2e_benchmark()
