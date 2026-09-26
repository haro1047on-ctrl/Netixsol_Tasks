"""Week 7 Day 6: Unified Configuration for Testing, Evaluation & Security."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Path resolutions
DAY6_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = DAY6_DIR.parent
DAY5_DIR = WORKSPACE_DIR / "day5-langgraph-agent"
REALESTATE_HUB_DIR = WORKSPACE_DIR / "realestate-hub"
BACKEND_DIR = REALESTATE_HUB_DIR / "backend"
DATA_DIR = REALESTATE_HUB_DIR / "data"
RESULTS_DIR = DAY6_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(DAY5_DIR / ".env")
load_dotenv(REALESTATE_HUB_DIR / ".env")
load_dotenv(DAY6_DIR / ".env")

# Model & API configurations
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004")

# Storage & DB (Aligned with workspace data architecture)
DB_DIR = DATA_DIR / "db"
SQLITE_PATH = DB_DIR / os.getenv("SQLITE_DB", "realestate_kb.db")
if not SQLITE_PATH.exists():
    fallback_db = BACKEND_DIR / "storage" / "realestate.db"
    if fallback_db.exists():
        SQLITE_PATH = fallback_db

VECTORSTORE_DIR = DATA_DIR / "vectorstores"
CHROMA_DIR = Path(VECTORSTORE_DIR / os.getenv("CHROMA_DIR", "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "properties").strip()

# Production server configs
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
APP_ENV = os.getenv("APP_ENV", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SECRET_KEY = os.getenv("SECRET_KEY", "realestate-hub-production-secret-key-day6")

# Evaluation & Benchmark parameters
EVAL_CONVERSATIONS_PATH = DAY6_DIR / "eval_suite" / "test_conversations.json"
BENCHMARK_REPORT_MD = RESULTS_DIR / "eval_report.md"
BENCHMARK_RESULTS_JSON = RESULTS_DIR / "eval_results.json"
TELEMETRY_LOG_PATH = RESULTS_DIR / "telemetry_metrics.json"

# SLA / SLO thresholds
SLO_LATENCY_P95_MS = float(os.getenv("SLO_LATENCY_P95_MS", "3500.0"))
SLO_MAX_ERROR_RATE = float(os.getenv("SLO_MAX_ERROR_RATE", "0.05"))
SLO_MIN_SUCCESS_RATE = float(os.getenv("SLO_MIN_SUCCESS_RATE", "0.85"))
SLO_MAX_HALLUCINATION_RATE = float(os.getenv("SLO_MAX_HALLUCINATION_RATE", "0.05"))
