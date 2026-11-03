"""
src/db/models.py
================
Zarya Digital Bank (Pakistan) — Persistence Layer & Database Models

SQLAlchemy database layer supporting:
- PostgreSQL (Production default)
- SQLite (Local zero-config fallback at data/zarya_bank.db)

Entities:
- Ticket: Automated CRM / core banking customer complaint records.
- Conversation: Multi-turn chat trace logs with PII sanitization.
- Feedback: CSAT ratings and customer sentiment feedback.
- GuardrailLog: Intercepted prompt injections, credential traps, and security violations.
"""

from datetime import datetime, timezone
import logging
import os
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Database")

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SQLITE_PATH = REPO_ROOT / "data" / "zarya_bank.db"

# Database connection URL (PostgreSQL with SQLite fallback)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{str(DEFAULT_SQLITE_PATH)}"

# SQLite requires check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=False,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==============================================================================
# Model Definitions
# ==============================================================================

class Ticket(Base):
    """Core Banking CRM dispute and complaint ticket."""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticket_number = Column(String(64), unique=True, index=True, nullable=False)
    session_id = Column(String(128), index=True, nullable=True)
    category = Column(String(64), index=True, nullable=False)  # e.g., Complaints, Transfers_Payments
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(32), default="P3_Normal", index=True)  # P1_Critical, P2_Urgent, P3_Normal, P4_Low
    status = Column(String(32), default="Open", index=True)  # Open, In_Progress, Resolved, Closed
    assigned_department = Column(String(64), default="Dispute_Resolution")
    suggested_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)


class Conversation(Base):
    """Customer chat history turn."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(128), index=True, nullable=False)
    user_message = Column(Text, nullable=False)  # Sanitized with PII masked
    assistant_message = Column(Text, nullable=False)
    intent = Column(String(64), index=True, nullable=True)
    sentiment = Column(String(32), nullable=True)
    priority = Column(String(32), nullable=True)
    latency_ms = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class Feedback(Base):
    """Customer satisfaction rating and audit feedback."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(128), index=True, nullable=True)
    rating = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class GuardrailLog(Base):
    """Audit log of blocked prompt injections and sensitive credential traps."""
    __tablename__ = "guardrail_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(128), index=True, nullable=True)
    guardrail_type = Column(String(64), index=True, nullable=False)
    action = Column(String(32), nullable=False)  # BLOCK_PRE_INFERENCE, TRIGGER_SECURITY_WARNING, etc.
    blocked_input = Column(Text, nullable=False)  # Sanitized text
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ==============================================================================
# Database Helper Functions
# ==============================================================================

from contextlib import contextmanager


def init_db():
    """Creates all database tables."""
    Base.metadata.create_all(bind=engine)
    dialect = "SQLite" if DATABASE_URL.startswith("sqlite") else "PostgreSQL"
    logger.info(f"Initialized database tables successfully ({dialect} mode).")


def get_db() -> Generator[Session, None, None]:
    """Dependency generator for FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for standalone scripts and background tasks."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("✅ Database tables successfully created.")

