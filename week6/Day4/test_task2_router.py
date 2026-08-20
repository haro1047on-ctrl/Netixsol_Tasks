"""
Task 2: Router Node Routing Accuracy Benchmark
Evaluates intent routing accuracy on 16 varied queries across 4 intent categories.
"""

from langgraph_afl_agent import intent_router_node

ROUTER_TEST_CASES = [
    # 1. Prediction Queries (4)
    {"query": "Will the Pies beat the Cats this week?", "expected": "prediction"},
    {"query": "Who will win between Collingwood Magpies and Geelong Cats?", "expected": "prediction"},
    {"query": "Predict top scorer for Carlton in the next match", "expected": "prediction"},
    {"query": "Who has a higher probability of winning between Swans and Hawks?", "expected": "prediction"},

    # 2. Retrieval Queries (4)
    {"query": "How many disposals did Sam Walsh have in 2024?", "expected": "retrieval"},
    {"query": "What were the match records for the Geelong Cats in 2024?", "expected": "retrieval"},
    {"query": "How many goals did Nick Daicos score in 2023?", "expected": "retrieval"},
    {"query": "Who were the top 5 goal scorers in 2023?", "expected": "retrieval"},

    # 3. Factual AFL Queries (4)
    {"query": "What is a mark inside 50 in AFL rules?", "expected": "factual"},
    {"query": "What is the Brownlow Medal in AFL?", "expected": "factual"},
    {"query": "What counts as a disposal in AFL rules?", "expected": "factual"},
    {"query": "Tell me about the history of the MCG stadium", "expected": "factual"},

    # 4. Off-Topic Queries (4)
    {"query": "Who won the FIFA Soccer World Cup in 2022?", "expected": "off_topic"},
    {"query": "Write a Python script to sort a list using quicksort", "expected": "off_topic"},
    {"query": "What is the weather forecast for London tomorrow?", "expected": "off_topic"},
    {"query": "Give me a step-by-step recipe for baking apple pie", "expected": "off_topic"}
]


def run_router_benchmark():
    print("=" * 80)
    print("TASK 2: INTENT ROUTER ACCURACY EVALUATION BENCHMARK")
    print("=" * 80)

    passed = 0
    total = len(ROUTER_TEST_CASES)

    print(f"{'#':<3} | {'Query':<50} | {'Expected':<12} | {'Detected':<12} | {'Status'}")
    print("-" * 90)

    for idx, case in enumerate(ROUTER_TEST_CASES, 1):
        state = {
            "user_query": case["query"],
            "messages": [],
            "detected_intent": "",
            "entities": {},
            "tool_results": {},
            "validation_status": "",
            "clarification_prompt": None,
            "final_response": ""
        }
        res_state = intent_router_node(state)
        detected = res_state["detected_intent"]
        expected = case["expected"]

        is_ok = detected == expected
        if is_ok:
            passed += 1

        status_str = "PASS [OK]" if is_ok else "FAIL [X]"
        q_short = (case["query"][:47] + "...") if len(case["query"]) > 50 else case["query"]
        print(f"{idx:<3} | {q_short:<50} | {expected:<12} | {detected:<12} | {status_str}")

    accuracy = (passed / total) * 100
    print("=" * 90)
    print(f"ROUTER ACCURACY SUMMARY: {passed}/{total} ({accuracy:.1f}%) Passed")
    print("=" * 90)

    return accuracy


if __name__ == "__main__":
    run_router_benchmark()
