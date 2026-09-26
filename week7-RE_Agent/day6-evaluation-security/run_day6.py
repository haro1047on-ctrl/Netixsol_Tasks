"""Week 7 Day 6: Master CLI Runner for Testing, Evaluation, Security & Deployment.

Usage:
  python run_day6.py --eval       # Run 40+ conversation evaluation suite
  python run_day6.py --security   # Run adversarial prompt injection & security tests
  python run_day6.py --bench      # Run benchmark engine & generate reports
  python run_day6.py --health     # Run pre-flight health checks
  python run_day6.py --serve      # Launch production FastAPI server
  python run_day6.py --all        # Execute complete test, eval & benchmark pipeline
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add paths
CURRENT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = CURRENT_DIR.parent
DAY5_DIR = WORKSPACE_DIR / "day5-langgraph-agent"
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(DAY5_DIR) not in sys.path:
    sys.path.insert(0, str(DAY5_DIR))


def run_security():
    """Execute Task 2 security penetration suite."""
    print("\n==========================================================")
    print(" [TASK 2] RUNNING PROMPT INJECTION & SECURITY PENETRATION SUITE")
    print("==========================================================")
    import unittest
    from security.test_security import TestSecurityGuardrails
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSecurityGuardrails)
    runner = unittest.TextTestRunner(verbosity=2)
    res = runner.run(suite)
    if not res.wasSuccessful():
        sys.exit(1)


def run_eval():
    """Execute Task 1 40+ conversation evaluation suite."""
    print("\n==========================================================")
    print(" [TASK 1] RUNNING 40+ TEST CONVERSATION EVALUATION SUITE")
    print("==========================================================")
    from eval_suite.eval_runner import EvaluationRunner
    runner = EvaluationRunner()
    summary = runner.run_all()
    print(f"\nTotal Conversations Evaluated: {summary.total_conversations}")
    print(f"Passed Conversations:          {summary.passed_conversations} / {summary.total_conversations}")
    print(f"Conversation Success Rate:     {summary.conversation_success_rate:.2f}%")
    print(f"Total Turns Evaluated:         {summary.total_turns}")
    print(f"Turn Success Rate:             {summary.turn_success_rate:.2f}%\n")
    print("Category Breakdown:")
    for cat, data in summary.category_breakdown.items():
        print(f" - {cat:20}: {data['passed']}/{data['total']} passed ({data['success_rate']:.1f}%) | Avg Latency: {data['avg_latency_ms']:.2f} ms")


def run_bench():
    """Execute Task 3 Performance Benchmark & Report Generation."""
    print("\n==========================================================")
    print(" [TASK 3] RUNNING PERFORMANCE BENCHMARK & REPORT GENERATOR")
    print("==========================================================")
    from performance.benchmark_engine import BenchmarkEngine
    from performance.report_generator import save_benchmark_artifacts
    engine = BenchmarkEngine()
    report, summary = engine.run_benchmark()
    md_path, json_path = save_benchmark_artifacts(report, summary)
    print("\nBenchmark Execution Complete!")
    print(f" - Verdict:                  {report.summary_verdict}")
    print(f" - Latency p50:              {report.latency_metrics.p50_ms} ms")
    print(f" - Latency p95:              {report.latency_metrics.p95_ms} ms (SLO Target: < 1500 ms)")
    print(f" - Conversation Success:     {report.conversation_success_rate:.2f}%")
    print(f" - Booking Success:          {report.booking_success_rate:.2f}%")
    print(f" - Tool Failure Rate:        {report.tool_failure_rate:.2f}%")
    print(f" - RAG Retrieval Accuracy:   {report.rag_accuracy:.2f}%")
    print(f" - Memory Accuracy:          {report.memory_fidelity_accuracy:.2f}%")
    print(f" - Hallucination Rate:       {report.hallucination_rate:.2f}%")
    print(f"\nArtifacts Saved:")
    print(f" - Markdown Report: {md_path}")
    print(f" - JSON Results:    {json_path}")


def run_health():
    """Execute Task 5 Preflight Health Checks."""
    from deployment.health_check import run_local_preflight_checks
    success = run_local_preflight_checks()
    if not success:
        sys.exit(1)


def run_serve():
    """Execute Task 5 FastAPI Production Server."""
    print("\n[SERVER] Starting RealEstate Hub Production FastAPI Server...")
    import uvicorn
    from deployment.env_validator import app_settings
    uvicorn.run("deployment.prod_server:app", host=app_settings.HOST, port=app_settings.PORT, reload=False)


def main():
    parser = argparse.ArgumentParser(description="RealEstate Hub Week 7 Day 6 Master Runner")
    parser.add_argument("--eval", action="store_true", help="Run 40+ conversation evaluation suite")
    parser.add_argument("--security", action="store_true", help="Run prompt injection security suite")
    parser.add_argument("--bench", action="store_true", help="Run performance benchmark and generate reports")
    parser.add_argument("--health", action="store_true", help="Run pre-flight health checks")
    parser.add_argument("--serve", action="store_true", help="Start FastAPI production server")
    parser.add_argument("--all", action="store_true", help="Run full health, security, eval, and benchmark pipeline")

    args = parser.parse_args()

    if args.health:
        run_health()
    elif args.security:
        run_security()
    elif args.eval:
        run_eval()
    elif args.bench:
        run_bench()
    elif args.serve:
        run_serve()
    elif args.all or len(sys.argv) == 1:
        run_health()
        run_security()
        run_eval()
        run_bench()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
