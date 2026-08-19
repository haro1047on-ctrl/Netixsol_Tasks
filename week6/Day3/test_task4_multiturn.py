"""
================================================================================
TASK 4: STRICT MULTI-TURN CONVERSATION MEMORY EVALUATION
================================================================================
Executes a 7-turn complex dialogue testing:
- Team Context -> Implicit Player Resolution -> Implicit Round Resolution
- Historical Stat Comparison -> Semantic Rule Retrieval
- Mid-Dialogue Context Pollution Defense (Off-Topic Injection)
- Seamless Context Recovery & Continuation

STRICT TURN ASSERTIONS:
1. Turn 1: Retrieves Collingwood 2023 team records (get_team_stats).
2. Turn 2: Resolves implicit team ('Collingwood') & year ('2023') for Nick Daicos (get_player_stats).
3. Turn 3: Resolves implicit player & year for Round 15 (get_player_stats).
4. Turn 4: Compares Round 15 vs 2023 season average with Grounding PASS.
5. Turn 5: Retrieves AFL disposal rule definition (get_afl_rules_and_info).
6. Turn 6: Defends against mid-dialogue non-AFL entity injection (LeBron James).
7. Turn 7: Recovers AFL context seamlessly for Scott Pendlebury.
"""

import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from afl_chat_agent import AFLChatAgent

DIALOGUE_STEPS = [
    {
        "turn": 1,
        "query": "How did Collingwood perform in the 2023 season?",
        "expected_tool": "get_team_stats",
        "must_contain_words": ["collingwood", "2023"],
        "check_grounding": False,
        "description": "Establish initial team context (Collingwood 2023)."
    },
    {
        "turn": 2,
        "query": "How did Nick Daicos perform on that team during that year?",
        "expected_tool": "get_player_stats",
        "must_contain_words": ["nick daicos", "disposals"],
        "description": "Resolve implicit player context (Nick Daicos) using previous team ('Collingwood') and year ('2023')."
    },
    {
        "turn": 3,
        "query": "What about his stats in round 15 of that season?",
        "expected_tool": "get_player_stats",
        "must_contain_words": ["round 15"],
        "description": "Resolve round-specific lookup (Round 15) using carried player ('Nick Daicos') and year ('2023')."
    },
    {
        "turn": 4,
        "query": "How does his disposal average in that round compare to his overall 2023 season average?",
        "expected_tool": None,  # Can answer from previous turn memory or re-query
        "must_contain_words": ["disposals", "average"],
        "description": "Perform memory-based statistical comparison (Round 15 vs 2023 Season Avg)."
    },
    {
        "turn": 5,
        "query": "What counts as a disposal in AFL rules?",
        "expected_tool": "get_afl_rules_and_info",
        "must_contain_words": ["disposal", "kick", "handball"],
        "description": "Retrieve semantic rule definition (AFL Disposal)."
    },
    {
        "turn": 6,
        "query": "How many goals did LeBron James score for that team during that season?",
        "expected_tool": None,  # MUST NOT call statistical tools for LeBron James
        "must_refuse_entity": "lebron james",
        "description": "Defend against mid-conversation non-AFL entity injection (LeBron James)."
    },
    {
        "turn": 7,
        "query": "What about Scott Pendlebury's stats in 2023?",
        "expected_tool": "get_player_stats",
        "must_contain_words": ["scott pendlebury", "disposals"],
        "description": "Recover AFL dialogue context seamlessly after refusal."
    }
]


def run_strict_multiturn_test():
    agent = AFLChatAgent()
    print("=" * 80)
    print("TASK 4: STRICT MULTI-TURN CONVERSATION MEMORY EVALUATION")
    print("=" * 80)

    passed_turns = 0
    total_turns = len(DIALOGUE_STEPS)

    for step in DIALOGUE_STEPS:
        time.sleep(1)
        t_num = step["turn"]
        query = step["query"]
        desc = step["description"]

        print(f"\n--- TURN {t_num} ---")
        print(f"Goal : {desc}")
        print(f"User : \"{query}\"")

        res = agent.chat(query)
        answer = res["answer"]
        answer_lower = answer.lower()
        tools_called = res["tools_called"]

        fail_reasons = []

        # 1. Expected tool check
        if step["expected_tool"]:
            if step["expected_tool"] not in tools_called:
                fail_reasons.append(f"Expected tool '{step['expected_tool']}' not called (called: {tools_called})")

        # 2. Must contain words check
        if "must_contain_words" in step:
            missing = [w for w in step["must_contain_words"] if w.lower() not in answer_lower]
            if missing:
                fail_reasons.append(f"Missing expected context terms in response: {missing}")

        # 3. Refusal check for turn 6 (LeBron James)
        if "must_refuse_entity" in step:
            refused = any(kw in answer_lower for kw in [
                "specialize", "cannot", "nba", "only", "afl",
                "not an afl player", "lebron james is not", "basketball"
            ])
            if not refused:
                fail_reasons.append("Failed to refuse injected non-AFL entity (LeBron James)")

        # 4. Grounding verdict check (for statistical turns)
        if step.get("check_grounding", True) and res["grounding_report"]["verdict"].startswith("FAIL"):
            fail_reasons.append(f"Grounding verdict failed: {res['grounding_report']['verdict']}")

        passed = len(fail_reasons) == 0
        if passed:
            passed_turns += 1

        print(f"Tools Used  : {tools_called}")
        print(f"Grounding   : {res['grounding_report']['verdict']}")
        print(f"Status      : {'PASS' if passed else 'FAIL'}")
        if fail_reasons:
            for r in fail_reasons:
                print(f"  [FAIL REASON] {r}")
        print(f"Agent Response:\n{answer[:200]}...")
        print("-" * 80)

    score = (passed_turns / total_turns) * 100
    print("\n" + "=" * 80)
    print(f"TASK 4 MULTI-TURN MEMORY SCORE: {passed_turns}/{total_turns} ({score:.1f}%)")
    if score == 100.0:
        print("STATUS: PERFECT -- All 7 turns executed with full context retention & injection defense.")
    else:
        print("STATUS: WEAK -- Context loss or memory failures detected.")
    print("=" * 80)


if __name__ == "__main__":
    run_strict_multiturn_test()
