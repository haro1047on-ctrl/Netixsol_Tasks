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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
HUGGINGFACE_EMBEDDING_MODEL = os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "all-MiniLM-L6-v2").strip()
GROQ_LLM_MODEL = os.getenv("GROQ_LLM_MODEL", "llama-3.1-70b-versatile").strip()
RETRIEVAL_K = int(os.getenv("RETRIEVAL_K", "4"))
RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.15"))
CHROMA_DIR = str(VECTORSTORE_DIR / os.getenv("CHROMA_DIR", "chroma_db"))
COLLECTION_NAME = os.getenv("CHROMA_COLLECTION", "properties").strip()
SQLITE_PATH = AGENT_DIR / "db" / os.getenv("SQLITE_DB", "realestate_kb.db")


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

def init_db():
    engine = get_engine()
    with engine.begin() as conn:
        from sqlalchemy import text
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                turn_index INTEGER,
                user_message TEXT,
                agent_message TEXT,
                intent TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT,
                intent TEXT,
                confidence FLOAT,
                session_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))

# Initialize DB
init_db()


def get_llm(temperature: float = 0.1, model_name: str | None = None):
    """Return configured LangChain Groq LLM."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured in .env file.")
    from langchain_groq import ChatGroq
    model = model_name or GROQ_LLM_MODEL
    return ChatGroq(
        model=model,
        temperature=temperature,
        api_key=GROQ_API_KEY,
    )


def get_embeddings():
    """Return configured HuggingFace embedding model."""
    from langchain_huggingface import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(
        model_name=HUGGINGFACE_EMBEDDING_MODEL,
    )
