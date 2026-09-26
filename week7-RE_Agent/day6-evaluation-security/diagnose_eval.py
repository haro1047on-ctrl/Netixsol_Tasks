"""Diagnostic script to inspect evaluation failure reasons."""
import sys
from pathlib import Path

DAY6_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = DAY6_DIR.parent
DAY5_DIR = WORKSPACE_DIR / "day5-langgraph-agent"

sys.path.insert(0, str(DAY6_DIR))
sys.path.insert(1, str(DAY5_DIR))

from eval_suite.eval_runner import EvaluationRunner

runner = EvaluationRunner()
summary = runner.run_all()

for conv_res in summary.results:
    if not conv_res.conversation_passed:
        print(f"\n[FAIL] {conv_res.conversation_id} ({conv_res.category}): {conv_res.title}")
        for t in conv_res.turn_results:
            if not t.passed:
                print(f"   Turn {t.turn_index}: Input='{t.user_input}'")
                print(f"      Response: '{t.agent_response}'")
                print(f"      Reasons:  {t.failure_reasons}")
