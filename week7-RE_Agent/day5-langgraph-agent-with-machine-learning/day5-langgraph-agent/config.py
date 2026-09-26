"""Configuration and environment initialization for Day 5 LangGraph Agent."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Directory structure:
# Workspace Root: c:/Users/PMYLS/Downloads/realestate-hub vapi and deepgram
# RealEstate Hub: c:/Users/PMYLS/Downloads/realestate-hub vapi and deepgram/realestate-hub
# Day5 Agent:     c:/Users/PMYLS/Downloads/realestate-hub vapi and deepgram/day5-langgraph-agent
AGENT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = AGENT_DIR.parent
REALESTATE_HUB_DIR = WORKSPACE_ROOT / "realestate-hub"
VAPI_FIRST_MESSAGE = (
    "Assalam-o-Alaikum! RealEstate Hub mein khush aamdeed. Main aap ka property consultant hoon. "
    "Bataiye, aap ghar dekh rahe hain ya flat?"
)

# Add backend directory to sys.path so we can import legacy service helpers safely if needed
BACKEND_DIR = REALESTATE_HUB_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))

# Load .env (agent local first, fallback to realestate-hub)
if (AGENT_DIR / ".env").exists():
    load_dotenv(AGENT_DIR / ".env")
elif (REALESTATE_HUB_DIR / ".env").exists():
    load_dotenv(REALESTATE_HUB_DIR / ".env")

# Directories
DATA_DIR = REALESTATE_HUB_DIR / "data"
CSV_DIR = DATA_DIR / "csv"
DB_DIR = DATA_DIR / "db"
VECTORSTORE_DIR = DATA_DIR / "vectorstores"
STORAGE_DIR = REALESTATE_HUB_DIR / "storage"
TRACES_DIR = AGENT_DIR / "traces"
TRACES_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

DB_BACKEND = os.getenv("DB_BACKEND", "postgres").strip().lower()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001").strip()
GEMINI_LLM_MODEL = os.getenv("GEMINI_LLM_MODEL", "gemini-3.5-flash-lite").strip()
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))
RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.15"))
CHROMA_DIR = str(VECTORSTORE_DIR / os.getenv("CHROMA_DIR", "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "properties").strip()
SQLITE_PATH = DB_DIR / os.getenv("SQLITE_DB", "realestate_kb.db")


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
