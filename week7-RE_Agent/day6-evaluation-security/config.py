"""Unified Day 6 configuration bridging Day 5 agent, Chroma, SQLite, and Day 6 evaluation."""
from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Base directories
DAY6_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = DAY6_DIR.parent
DAY5_DIR = WORKSPACE_DIR / "day5-langgraph-agent"
REALESTATE_HUB_DIR = WORKSPACE_DIR / "realestate-hub"
BACKEND_DIR = REALESTATE_HUB_DIR / "backend"
DATA_DIR = REALESTATE_HUB_DIR / "data"

# Subdirectories
CSV_DIR = DATA_DIR / "csv"
DB_DIR = DATA_DIR / "db"
VECTORSTORE_DIR = DATA_DIR / "vectorstores"
STORAGE_DIR = REALESTATE_HUB_DIR / "storage"
RESULTS_DIR = DAY6_DIR / "results"
TRACES_DIR = DAY5_DIR / "traces"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
TRACES_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Load environment variables
load_dotenv(DAY5_DIR / ".env")
load_dotenv(REALESTATE_HUB_DIR / ".env")
load_dotenv(DAY6_DIR / ".env")

# Settings
DB_BACKEND = os.getenv("DB_BACKEND", "sqlite").strip().lower()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-2.5-flash").strip()
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/text-embedding-004").strip()
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))
RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.15"))
CHROMA_DIR = str(VECTORSTORE_DIR / os.getenv("CHROMA_DIR", "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "properties").strip()
SQLITE_PATH = DB_DIR / os.getenv("SQLITE_DB", "realestate_kb.db")
if not SQLITE_PATH.exists():
    fallback_db = BACKEND_DIR / "storage" / "realestate.db"
    if fallback_db.exists():
        SQLITE_PATH = fallback_db

PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
APP_ENV = os.getenv("APP_ENV", "production")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SECRET_KEY = os.getenv("SECRET_KEY", "realestate-hub-production-secret-key-day6")

EVAL_CONVERSATIONS_PATH = DAY6_DIR / "eval_suite" / "test_conversations.json"
BENCHMARK_REPORT_MD = RESULTS_DIR / "eval_report.md"
BENCHMARK_RESULTS_JSON = RESULTS_DIR / "eval_results.json"
TELEMETRY_LOG_PATH = RESULTS_DIR / "telemetry_metrics.json"

SLO_LATENCY_P95_MS = float(os.getenv("SLO_LATENCY_P95_MS", "1500.0"))
SLO_MAX_ERROR_RATE = float(os.getenv("SLO_MAX_ERROR_RATE", "0.05"))
SLO_MIN_SUCCESS_RATE = float(os.getenv("SLO_MIN_SUCCESS_RATE", "0.90"))
SLO_MAX_HALLUCINATION_RATE = float(os.getenv("SLO_MAX_HALLUCINATION_RATE", "0.05"))


def get_engine():
    """Return SQLAlchemy engine for Postgres or SQLite."""
    if DB_BACKEND == "postgres":
        host = os.getenv("PG_HOST", "localhost")
        port = os.getenv("PG_PORT", "5432")
        db = os.getenv("PG_DB", "realestate_kb")
        user = os.getenv("PG_USER", "postgres")
        password = os.getenv("PG_PASSWORD", "")
        from sqlalchemy.engine import URL
        url = URL.create(
            "postgresql+psycopg2",
            username=user,
            password=password,
            host=host,
            port=int(port),
            database=db,
        )
        return create_engine(url, pool_pre_ping=True)

    return create_engine(f"sqlite:///{SQLITE_PATH}", pool_pre_ping=True)


def get_llm(temperature: float = 0.1, model_name: str | None = None):
    """Return configured LangChain Google Generative AI LLM."""
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not configured in .env file.")
    from langchain_google_genai import ChatGoogleGenerativeAI
    model = model_name or GEMINI_LLM_MODEL
    return ChatGoogleGenerativeAI(
        model=model,
        temperature=temperature,
        google_api_key=GOOGLE_API_KEY,
    )


def get_embeddings():
    """Return configured Gemini embedding model."""
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY is not configured in .env file.")
    from langchain_google_genai import GoogleGenerativeAIEmbeddings
    return GoogleGenerativeAIEmbeddings(
        model=GEMINI_EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )
