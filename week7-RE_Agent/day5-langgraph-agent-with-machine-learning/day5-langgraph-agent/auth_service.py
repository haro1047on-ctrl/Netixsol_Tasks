"""Authentication & User Management Service for RealEstate Hub.

Provides persistent user registration, authentication, role-based checks (Admin vs User),
and default pre-seeded demo accounts.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import secrets
from typing import Any, Dict, Optional
from sqlalchemy import Column, MetaData, String, Table, Text, create_engine, select, text

from config import get_engine

metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("user_id", String(64), primary_key=True),
    Column("name", String(128), nullable=False),
    Column("email", String(128), unique=True, nullable=False),
    Column("password_hash", String(256), nullable=False),
    Column("role", String(32), default="user"),  # "admin" or "user"
    Column("phone", String(64), default=""),
    Column("created_at", String(64)),
)

# Active token store: token -> user_dict
ACTIVE_TOKENS: Dict[str, Dict[str, Any]] = {}


def hash_password(password: str) -> str:
    """Deterministic salted SHA-256 hash."""
    salt = "realestate_hub_secure_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()


def init_users_table():
    """Ensure users table exists and seed demo accounts if empty."""
    engine = get_engine()
    try:
        metadata.create_all(engine)
    except Exception:
        pass

    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Pre-seed Admin and User demo accounts
    demo_accounts = [
        {
            "user_id": "usr-admin-default",
            "name": "Admin Director (Sahi RealEstate)",
            "email": "admin@realestatehub.pk",
            "password_hash": hash_password("admin123"),
            "role": "admin",
            "phone": "+92 300 1234567",
            "created_at": now_iso,
        },
        {
            "user_id": "usr-client-default",
            "name": "Muhammad Umer",
            "email": "user@realestatehub.pk",
            "password_hash": hash_password("user123"),
            "role": "user",
            "phone": "+92 321 7654321",
            "created_at": now_iso,
        },
    ]

    with engine.begin() as conn:
        for acc in demo_accounts:
            existing = conn.execute(
                select(users_table).where(users_table.c.email == acc["email"])
            ).first()
            if not existing:
                conn.execute(users_table.insert().values(**acc))


init_users_table()


def register_user(
    name: str,
    email: str,
    password: str,
    role: str = "user",
    phone: str = "",
) -> Dict[str, Any]:
    """Register a new user or admin."""
    email_clean = email.strip().lower()
    if not email_clean or "@" not in email_clean:
        return {"ok": False, "error": "Invalid email address format."}
    if len(password) < 6:
        return {"ok": False, "error": "Password must be at least 6 characters long."}

    engine = get_engine()
    with engine.begin() as conn:
        existing = conn.execute(
            select(users_table).where(users_table.c.email == email_clean)
        ).first()
        if existing:
            return {"ok": False, "error": "An account with this email already exists."}

        user_id = f"usr-{secrets.token_hex(8)}"
        role_clean = "admin" if role.strip().lower() == "admin" else "user"
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        pwd_hash = hash_password(password)

        conn.execute(
            users_table.insert().values(
                user_id=user_id,
                name=name.strip(),
                email=email_clean,
                password_hash=pwd_hash,
                role=role_clean,
                phone=phone.strip(),
                created_at=now_iso,
            )
        )

    token = secrets.token_urlsafe(32)
    user_data = {
        "user_id": user_id,
        "name": name.strip(),
        "email": email_clean,
        "role": role_clean,
        "phone": phone.strip(),
    }
    ACTIVE_TOKENS[token] = user_data
    return {"ok": True, "token": token, "user": user_data}


def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """Authenticate with email and password."""
    email_clean = email.strip().lower()
    pwd_hash = hash_password(password)
    engine = get_engine()

    with engine.connect() as conn:
        row = conn.execute(
            select(users_table).where(
                users_table.c.email == email_clean,
                users_table.c.password_hash == pwd_hash,
            )
        ).mappings().first()

    if not row:
        return {"ok": False, "error": "Invalid email or password."}

    token = secrets.token_urlsafe(32)
    user_data = {
        "user_id": row["user_id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "phone": row["phone"],
    }
    ACTIVE_TOKENS[token] = user_data
    return {"ok": True, "token": token, "user": user_data}


def get_current_user(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return current user dict from session token."""
    if not token:
        return None
    return ACTIVE_TOKENS.get(token)
