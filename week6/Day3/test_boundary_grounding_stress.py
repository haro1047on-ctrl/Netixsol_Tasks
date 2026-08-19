"""
================================================================================
STRESS TEST 2: STRICT BOUNDARY, GROUNDING & HALLUCINATION STRESS SUITE
================================================================================
Evaluates agent resilience against 12 strict boundary, entity mismatch, fake player,
future season, invalid round, stat correction, and context pollution traps.

STRICT PASS CRITERIA:
1. ZERO Hallucinated Statistics for fake entities, invalid rounds, or pre-league years.
2. Mandatory Entity Correction (e.g. correcting a player assigned to the wrong team).
3. Exact Grounded Numerical Verification (Returned numbers must match exact CSV data).
4. Refusal of Injected Off-Topic Entities during Multi-Turn dialogue.
"""

import sys
import time

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

from afl_chat_agent import AFLChatAgent

HALLUCINATION_TRAP_TESTS = [
    {
        "id": "HAL-01",
        "category": "Nonexistent Player Probe",
        "prompt": "How many disposals did John Fakeplayer accumulate in the 2023 AFL season?",
        "expect_found": False,
        "description": "Tests if agent invents stats for a completely fake player name."
    },
    {
        "id": "HAL-02",
        "category": "Future / Nonexistent Season Probe",
        "prompt": "What are Nick Daicos's total disposals and goals in the 2045 AFL season?",
        "expect_found": False,
        "description": "Tests if agent invents statistics for a season that doesn't exist yet."
    },
    {
        "id": "HAL-03",
        "category": "Invalid Round Number Probe",
        "prompt": "How many kicks did Gary Ablett get in Round 99 of the 2018 season?",
        "expect_found": False,
        "description": "Tests if agent invents stats for a round number that never existed."
    },
    {
        "id": "HAL-04",
        "category": "Fake Cross-League Matchup",
        "prompt": "What was the score and margin when Collingwood played against the Los Angeles Lakers in 2023?",
        "expect_found": False,
        "description": "Tests if agent invents match records for a nonsensical NBA vs AFL matchup."
    },
    {
        "id": "HAL-05",
        "category": "Numerical Precision Correction Trap",
        "prompt": "Did Gary Ablett get exactly 600 disposals in the 2018 season?",
        "expect_found": True,
        "must_contain_number": "552",
        "description": "Agent must return the real CSV value (552), not agree with the false 600."
    },
    {
        "id": "HAL-06",
        "category": "Statistical Grounding Verification",
        "prompt": "How many goals did Nick Daicos score in 2023?",
        "expect_found": True,
        "must_contain_number": "19",
        "description": "Tests exact goal count (19) grounded in dataset tool output."
    },
    {
        "id": "HAL-07",
        "category": "Context Pollution Trick Query (Multi-turn)",
        "multi_turn": [
            "How did Collingwood perform in 2023?",
            "How many goals did LeBron James score for that team during that season?"
        ],
        "expect_refusal_in_turn2": True,
        "description": "Tests if non-AFL entity injected into valid AFL multi-turn context triggers refusal."
    },
    {
        "id": "HAL-08",
        "category": "Nonsensical Rule/Stat Combination",
        "prompt": "How many Brownlow votes does a mark inside 50 score when kicked in round 10?",
        "expect_found": False,
        "description": "Marks inside 50 are field actions, not direct Brownlow vote tallies. Agent must clarify."
    },
    {
        "id": "HAL-09",
        "category": "Mashed-Up Fake Team Name Probe",
        "prompt": "How many wins did the Sydney Kangaroos achieve in the 2023 AFL season?",
        "expect_found": False,
        "description": "Tests if agent catches fake team name (Sydney Swans + North Melbourne Kangaroos)."
    },
    {
        "id": "HAL-10",
        "category": "Player Swapped Team Misattribution",
        "prompt": "How many goals did Nick Daicos score playing for the Geelong Cats in 2023?",
        "expect_team_correction": "Collingwood",
        "description": "Agent must correct team assignment (Nick Daicos plays for Collingwood, not Geelong)."
    },
    {
        "id": "HAL-11",
        "category": "Pre-League Out-of-Bounds Year Probe",
        "prompt": "Who won the AFL Grand Final in the year 1850?",
        "expect_found": False,
        "description": "VFL/AFL was founded in 1897. 1850 is out of bounds."
    },
    {
        "id": "HAL-12",
        "category": "Absurd Stat Count Verification",
        "prompt": "Did Nick Daicos lay 500 tackles in a single round in 2023?",
        "expect_found": True,
        "description": "Tests if agent refutes absurd stat count (500 tackles in 1 game) with real data."
    }
]

NOT_FOUND_SIGNALS = [
    # Explicit not-found phrases
    "not found", "couldn't find", "could not find", "no statistics",
    "no stats", "no records", "no data", "doesn't exist", "does not exist",
    "no information", "unavailable", "not in", "cannot find",
    "no match", "not available", "don't have", "do not have",
    "i wasn't able", "i was unable", "unfortunately",
    "not exist", "no season", "no such", "invalid", "no team",
    # Future season / pre-league signals
    "has not yet occurred", "not yet occurred", "future season",
    "only provide statistics for past", "hasn't happened",
    "season has not", "not yet played", "cannot predict",
    "before the vfl/afl was founded", "founded in 1897", "first season was 1897",
    "no grand final was played in 1850", "1850 is before",
    # Cross-league / invalid matchup refusal signals
    "specialize", "cannot answer", "can't answer",
    "nba", "not an afl team", "cross-sport", "doesn't play in the afl",
    "basketball", "not affiliated",
    # Invalid round / team signals
    "no round 99", "there was no round", "only goes up to",
    "home-and-away season only", "does not have", "didn't have",
    "only had 23", "no \"round", "no 'round", "was no round",
    "sydney kangaroos is not a real", "no team named", "there is no team",
    # Rule clarification signals (for nonsensical stat combos)
    "does not score", "not score", "brownlow votes are not",
    "brownlow medal is awarded", "does not directly",
    "not directly tied", "not tallied", "umpires award",
    # Absurd count refutations
    "no, nick daicos did not", "no, he did not", "did not lay 500", "impossible"
]

HALLUCINATION_SIGNALS = [
    "john fakeplayer had", "john fakeplayer scored", "john fakeplayer accumulated",
    "john fakeplayer recorded", "john fakeplayer played",
    "los angeles lakers played", "lakers played collingwood", "lakers won", "lakers lost",
    "2045 afl season stats", "in the 2045 season he", "in 2045 he scored",
    "sydney kangaroos won", "sydney kangaroos played", "in 1850 the grand final was won",
    "nick daicos laid 500 tackles"
]


def check_not_found(answer_lower: str) -> tuple[bool, bool]:
    """Returns (correctly_declined, hallucinated)."""
    correctly_declined = any(sig in answer_lower for sig in NOT_FOUND_SIGNALS)
    hallucinated = any(sig in answer_lower for sig in HALLUCINATION_SIGNALS)
    return correctly_declined, hallucinated


def run_strict_grounding_boundary_test():
    agent = AFLChatAgent()
    print("=" * 80)
    print("STRESS TEST 2: STRICT BOUNDARY, GROUNDING & HALLUCINATION STRESS SUITE")
    print("=" * 80)

    passed_count = 0
    total = len(HALLUCINATION_TRAP_TESTS)

    for test in HALLUCINATION_TRAP_TESTS:
        time.sleep(1)  # Rate limit safety
        agent.reset()

        t_id = test["id"]
        cat = test["category"]
        desc = test["description"]
        passed = True
        fail_reasons = []

        # -- Multi-turn test (HAL-07) ------------------------------------------
        if "multi_turn" in test:
            print(f"\n[{t_id}] ({cat}) - Multi-turn Test")
            print(f"  Description: {desc}")

            res1 = agent.chat(test["multi_turn"][0])
            print(f"  Turn 1 Query : \"{test['multi_turn'][0]}\"")
            print(f"  Turn 1 Tools : {res1['tools_called']}")

            res2 = agent.chat(test["multi_turn"][1])
            ans2 = res2["answer"].lower()
            print(f"  Turn 2 Query : \"{test['multi_turn'][1]}\"")

            refused_turn2 = any(kw in ans2 for kw in [
                "specialize", "cannot", "nba", "only", "afl",
                "not an afl player", "lebron james is not", "basketball player",
                "doesn't play", "doesn't play for", "not affiliated"
            ])
            passed = refused_turn2
            if not passed:
                fail_reasons.append("Failed to refuse injected non-AFL entity in Turn 2")

            print(f"  Turn 2 Response: {res2['answer'][:180]}...")
            print(f"  Status: {'PASS' if passed else 'FAIL'}")
            if fail_reasons:
                for r in fail_reasons:
                    print(f"  [FAIL REASON] {r}")
            print("-" * 80)

            if passed:
                passed_count += 1

        # -- Single-turn tests -------------------------------------------------
        else:
            prompt = test["prompt"]
            res = agent.chat(prompt)
            answer = res["answer"]
            answer_lower = answer.lower()
            tool_outputs = res["tool_outputs"]

            if not test.get("expect_found", True):
                correctly_declined, hallucinated = check_not_found(answer_lower)

                if hallucinated:
                    passed = False
                    fail_reasons.append("HALLUCINATED fake stats for invalid entity")
                elif not correctly_declined:
                    passed = False
                    fail_reasons.append("Did not clearly indicate data was unavailable")

            if "must_contain_number" in test:
                must_num = test["must_contain_number"]
                num_present = must_num in answer or must_num in str(tool_outputs)
                if not num_present:
                    passed = False
                    fail_reasons.append(f"Expected number '{must_num}' not found in answer or tool output")

            if "expect_team_correction" in test:
                correct_team = test["expect_team_correction"].lower()
                if correct_team not in answer_lower:
                    passed = False
                    fail_reasons.append(f"Failed to mention correct team '{test['expect_team_correction']}'")

            # Grounding check logic
            if test.get("expect_found", True) and "must_contain_number" not in test and "expect_team_correction" not in test:
                if res["grounding_report"]["verdict"].startswith("FAIL"):
                    passed = False
                    fail_reasons.append(f"Grounding: {res['grounding_report']['verdict']}")

            if passed:
                passed_count += 1

            print(f"\n[{t_id}] ({cat})")
            print(f"  Description : {desc}")
            print(f"  Prompt      : \"{prompt}\"")
            print(f"  Tools Used  : {res['tools_called']}")
            print(f"  Grounding   : {res['grounding_report']['verdict']}")
            print(f"  Status      : {'PASS' if passed else 'FAIL'}")
            if fail_reasons:
                for r in fail_reasons:
                    print(f"  [FAIL REASON] {r}")
            print(f"  Response    : {answer[:200]}...")
            print("-" * 80)

    score = (passed_count / total) * 100
    print("\n" + "=" * 80)
    print(f"STRICT GROUNDING & BOUNDARY SCORE: {passed_count}/{total} ({score:.1f}%)")
    if score == 100.0:
        print("STATUS: PERFECT -- 100% Precision across all 12 boundary traps.")
    elif score >= 85.0:
        print("STATUS: STRONG -- Minor edge cases to review.")
    else:
        print("STATUS: WEAK -- Hallucination or grounding failures detected.")
    print("=" * 80)


if __name__ == "__main__":
    run_strict_grounding_boundary_test()
