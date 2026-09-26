"""Task 3: CRM Persistence & Lead Management Tool.

Provides database logging for CRM leads, appointment records, reminders,
and client interaction history.
"""
from __future__ import annotations

import datetime
import json
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import Column, MetaData, String, Table, Text, create_engine, select, text
from langchain_core.tools import tool

from config import get_engine

metadata = MetaData()

crm_leads = Table(
    "crm_leads",
    metadata,
    Column("lead_id", String(64), primary_key=True),
    Column("client_name", String(128)),
    Column("phone", String(64)),
    Column("email", String(128)),
    Column("city", String(64)),
    Column("budget", String(64)),
    Column("property_type", String(64)),
    Column("purpose", String(32)),
    Column("stage", String(64)),
    Column("preferences_json", Text),
    Column("created_at", String(64)),
    Column("updated_at", String(64)),
)

crm_appointments = Table(
    "crm_appointments",
    metadata,
    Column("appointment_id", String(64), primary_key=True),
    Column("lead_id", String(64)),
    Column("client_name", String(128)),
    Column("client_phone", String(64)),
    Column("property_id", String(64)),
    Column("property_title", String(256)),
    Column("agent_name", String(128)),
    Column("date_str", String(64)),
    Column("time_str", String(64)),
    Column("status", String(32)),
    Column("calendar_event_id", String(64)),
    Column("calendar_link", Text),
    Column("notes", Text),
    Column("created_at", String(64)),
    Column("updated_at", String(64)),
)


def init_crm_tables():
    """Ensure CRM tables exist."""
    try:
        engine = get_engine()
        metadata.create_all(engine)
    except Exception:
        pass


init_crm_tables()


def upsert_lead(
    client_name: str,
    phone: str,
    email: str = "",
    city: str = "",
    budget: str = "",
    property_type: str = "",
    purpose: str = "For Sale",
    stage: str = "Qualified",
    preferences: Optional[Dict[str, Any]] = None,
    lead_id: Optional[str] = None,
) -> str:
    """Create or update a client lead record in CRM."""
    engine = get_engine()
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    prefs_str = json.dumps(preferences or {}, ensure_ascii=False)

    with engine.begin() as conn:
        existing = None
        if lead_id:
            res = conn.execute(select(crm_leads).where(crm_leads.c.lead_id == lead_id))
            existing = res.mappings().first()
        elif phone and phone != "Not Provided":
            res = conn.execute(select(crm_leads).where(crm_leads.c.phone == phone))
            existing = res.mappings().first()

        if existing:
            target_id = existing["lead_id"]
            conn.execute(
                crm_leads.update()
                .where(crm_leads.c.lead_id == target_id)
                .values(
                    client_name=client_name or existing["client_name"],
                    email=email or existing["email"],
                    city=city or existing["city"],
                    budget=budget or existing["budget"],
                    property_type=property_type or existing["property_type"],
                    purpose=purpose or existing["purpose"],
                    stage=stage or existing["stage"],
                    preferences_json=prefs_str if preferences else existing["preferences_json"],
                    updated_at=now_iso,
                )
            )
            return target_id
        else:
            target_id = lead_id or f"lead_{uuid.uuid4().hex[:10]}"
            conn.execute(
                crm_leads.insert().values(
                    lead_id=target_id,
                    client_name=client_name or "New Client",
                    phone=phone or "Not Provided",
                    email=email or "",
                    city=city or "",
                    budget=budget or "",
                    property_type=property_type or "",
                    purpose=purpose or "For Sale",
                    stage=stage,
                    preferences_json=prefs_str,
                    created_at=now_iso,
                    updated_at=now_iso,
                )
            )
            return target_id


def log_appointment(
    lead_id: str,
    client_name: str,
    client_phone: str,
    property_id: str,
    property_title: str,
    agent_name: str,
    date_str: str,
    time_str: str,
    status: str = "scheduled",
    calendar_event_id: str = "",
    calendar_link: str = "",
    notes: str = "",
    appointment_id: Optional[str] = None,
) -> str:
    """Log new or updated appointment into CRM."""
    engine = get_engine()
    appt_id = appointment_id or f"appt_{uuid.uuid4().hex[:10]}"
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    with engine.begin() as conn:
        res = conn.execute(select(crm_appointments).where(crm_appointments.c.appointment_id == appt_id))
        existing = res.mappings().first()
        if existing:
            conn.execute(
                crm_appointments.update()
                .where(crm_appointments.c.appointment_id == appt_id)
                .values(
                    date_str=date_str,
                    time_str=time_str,
                    status=status,
                    calendar_event_id=calendar_event_id or existing["calendar_event_id"],
                    calendar_link=calendar_link or existing["calendar_link"],
                    notes=notes or existing["notes"],
                    updated_at=now_iso,
                )
            )
        else:
            conn.execute(
                crm_appointments.insert().values(
                    appointment_id=appt_id,
                    lead_id=lead_id,
                    client_name=client_name,
                    client_phone=client_phone,
                    property_id=property_id,
                    property_title=property_title,
                    agent_name=agent_name,
                    date_str=date_str,
                    time_str=time_str,
                    status=status,
                    calendar_event_id=calendar_event_id,
                    calendar_link=calendar_link,
                    notes=notes,
                    created_at=now_iso,
                    updated_at=now_iso,
                )
            )
    return appt_id


def get_appointment(appointment_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve an appointment record from CRM."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(select(crm_appointments).where(crm_appointments.c.appointment_id == appointment_id)).mappings().first()
        return dict(row) if row else None


@tool
def crm_tool(
    action: str,  # 'upsert_lead', 'log_appointment', 'get_appointment'
    client_name: Optional[str] = "",
    phone: Optional[str] = "",
    city: Optional[str] = "",
    budget: Optional[str] = "",
    property_type: Optional[str] = "",
    lead_id: Optional[str] = None,
    appointment_id: Optional[str] = None,
    property_id: Optional[str] = "",
    property_title: Optional[str] = "",
    agent_name: Optional[str] = "Ahmed Raza",
    date_str: Optional[str] = "",
    time_str: Optional[str] = "",
    status: Optional[str] = "scheduled",
    calendar_link: Optional[str] = "",
    notes: Optional[str] = "",
) -> str:
    """Manage client leads and appointments in the CRM database."""
    action_clean = action.lower().strip()
    if action_clean == "upsert_lead":
        lid = upsert_lead(
            client_name=client_name or "Valued Client",
            phone=phone or "Not Provided",
            city=city or "",
            budget=budget or "",
            property_type=property_type or "",
            lead_id=lead_id,
        )
        return json.dumps({"status": "success", "lead_id": lid})
    elif action_clean == "log_appointment":
        aid = log_appointment(
            lead_id=lead_id or f"lead_{uuid.uuid4().hex[:8]}",
            client_name=client_name or "Valued Client",
            client_phone=phone or "Not Provided",
            property_id=property_id or "PROP-General",
            property_title=property_title or "Property Visit",
            agent_name=agent_name or "Ahmed Raza",
            date_str=date_str or "Tomorrow",
            time_str=time_str or "3:00 PM",
            status=status or "scheduled",
            calendar_link=calendar_link or "",
            notes=notes or "",
            appointment_id=appointment_id,
        )
        return json.dumps({"status": "success", "appointment_id": aid})
    elif action_clean == "get_appointment":
        appt = get_appointment(appointment_id or "")
        return json.dumps({"status": "success", "appointment": appt})

    return json.dumps({"error": f"Unknown CRM action '{action}'"})
