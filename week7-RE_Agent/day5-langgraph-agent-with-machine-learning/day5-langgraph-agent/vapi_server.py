"""Vapi Voice & RealEstate Hub Full-Stack API Server.

Powered by Week 7 Day 5 LangGraph AI Agent, CRM Persistence, Properties Management,
Role-Based Authentication, and Vapi Voice Webhook.
"""
from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent
load_dotenv(CURRENT_DIR / ".env", override=True)

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select, text

import auth_service
from config import get_engine
from graph import run_agent_turn
from logger import default_agent_logger
from state import AgentState, create_initial_state
from tools.calendar_tools import create_calendar_event
from tools.crm_tools import log_appointment, upsert_lead
from tools.email_tools import send_appointment_email, send_direct_contact_email
from tools.search_tools import search_properties_core

logger = logging.getLogger("VapiServer")

app = FastAPI(title="RealEstate Hub LangGraph Full-Stack API & Voice Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

VAPI_TRANSCRIBER_MODEL = os.getenv("VAPI_TRANSCRIBER_MODEL", "nova-3")
VAPI_TRANSCRIBER_LANGUAGE = os.getenv("VAPI_TRANSCRIBER_LANGUAGE", "ur")
VAPI_VOICE_PROVIDER = os.getenv("VAPI_VOICE_PROVIDER", "vapi")
VAPI_VOICE_ID = os.getenv("VAPI_VOICE_ID", "Elliot")
VAPI_ASSISTANT_NAME = os.getenv("VAPI_ASSISTANT_NAME", "RealEstate Hub LangGraph Agent")
BACKEND_PUBLIC_URL = os.getenv("BACKEND_PUBLIC_URL", "").strip().rstrip("/")
FIRST_MESSAGE = os.getenv(
    "VAPI_FIRST_MESSAGE",
    "Assalam-o-Alaikum! RealEstate Hub mein khush aamdeed. Main aap ka property consultant hoon. Bataiye, aap ghar dekh rahe hain ya flat?"
)

# Persistent in-memory session states keyed by session/call ID
CALL_SESSIONS: Dict[str, AgentState] = {}


def get_active_ngrok_url() -> str | None:
    """Auto-detect public URL from local ngrok client."""
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels", headers={"User-Agent": "realestate-hub/1.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for t in data.get("tunnels", []):
                if t.get("proto") == "https" and t.get("public_url"):
                    return str(t["public_url"]).strip().rstrip("/")
    except Exception:
        pass
    return None


def get_backend_public_url() -> str:
    ngrok_url = get_active_ngrok_url()
    if ngrok_url:
        return ngrok_url
    return os.getenv("BACKEND_PUBLIC_URL", "").strip().rstrip("/")


# ===========================================================================
# 1. Base & Health Endpoints
# ===========================================================================

@app.get("/")
async def index():
    return {
        "service": "RealEstate Hub Day 5 LangGraph Platform",
        "orchestration": "LangGraph StateGraph",
        "voice_backend": "vapi",
        "version": "2.0.0",
    }


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "engine": "LangGraph",
        "backend_public_url": get_backend_public_url(),
        "language": VAPI_TRANSCRIBER_LANGUAGE,
        "transcriber": f"Deepgram ({VAPI_TRANSCRIBER_MODEL}, {VAPI_TRANSCRIBER_LANGUAGE})",
        "voice": f"{VAPI_VOICE_PROVIDER} ({VAPI_VOICE_ID})",
        "vapi_assistant_id": os.getenv("VAPI_ASSISTANT_ID", ""),
        "vapi_public_key": os.getenv("VAPI_PUBLIC_KEY", ""),
    }


# ===========================================================================
# 2. Authentication Endpoints (Admin & Client Sign Up / Login)
# ===========================================================================

@app.post("/api/auth/signup")
async def auth_signup(payload: dict[str, Any]):
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip()
    password = payload.get("password", "").strip()
    role = payload.get("role", "user").strip()
    phone = payload.get("phone", "").strip()

    if not name or not email or not password:
        return JSONResponse({"ok": False, "error": "Name, email, and password are required."}, status_code=400)

    result = auth_service.register_user(name=name, email=email, password=password, role=role, phone=phone)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    return result


@app.post("/api/auth/login")
async def auth_login(payload: dict[str, Any]):
    email = payload.get("email", "").strip()
    password = payload.get("password", "").strip()

    if not email or not password:
        return JSONResponse({"ok": False, "error": "Email and password are required."}, status_code=400)

    result = auth_service.authenticate_user(email=email, password=password)
    if not result.get("ok"):
        return JSONResponse(result, status_code=401)
    return result


@app.get("/api/auth/me")
async def auth_me(authorization: Optional[str] = Header(None)):
    token = ""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
    user = auth_service.get_current_user(token)
    if not user:
        return JSONResponse({"ok": False, "error": "Unauthorized or session expired."}, status_code=401)
    return {"ok": True, "user": user}


# ===========================================================================
# 3. Properties Management (CRUD & Public Search)
# ===========================================================================

@app.get("/api/properties")
async def get_properties(
    city: Optional[str] = None,
    property_type: Optional[str] = None,
    purpose: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(18, ge=1, le=100),
):
    """List properties with search, filtering, and pagination."""
    engine = get_engine()
    clauses = ["1=1"]
    params: Dict[str, Any] = {}

    if city and city.strip():
        clauses.append("LOWER(city) = LOWER(:city)")
        params["city"] = city.strip()
    if property_type and property_type.strip():
        clauses.append("LOWER(property_type) = LOWER(:prop_type)")
        params["prop_type"] = property_type.strip()
    if purpose and purpose.strip():
        clauses.append("LOWER(purpose) = LOWER(:purpose)")
        params["purpose"] = purpose.strip()
    if min_price is not None and min_price > 0:
        clauses.append("price >= :min_price")
        params["min_price"] = float(min_price)
    if max_price is not None and max_price > 0:
        clauses.append("price <= :max_price")
        params["max_price"] = float(max_price)
    if search and search.strip():
        clauses.append("(LOWER(locality) LIKE :search OR LOWER(location) LIKE :search OR LOWER(property_id) LIKE :search)")
        params["search"] = f"%{search.strip().lower()}%"

    where_sql = " AND ".join(clauses)
    offset = (page - 1) * limit
    params["limit"] = limit
    params["offset"] = offset

    count_sql = f"SELECT count(*) FROM properties WHERE {where_sql}"
    data_sql = f"""
        SELECT property_id, property_type, purpose, city, locality, location,
               price, price_bin, area_marla, area_sqft, bedrooms, baths,
               latitude, longitude, date_added, agent_id, agent
        FROM properties
        WHERE {where_sql}
        ORDER BY price DESC
        LIMIT :limit OFFSET :offset
    """

    with engine.connect() as conn:
        total = conn.execute(text(count_sql), params).scalar() or 0
        rows = conn.execute(text(data_sql), params).mappings().all()

    properties = [dict(r) for r in rows]
    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return {
        "ok": True,
        "properties": properties,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }


@app.post("/api/properties")
async def create_property(payload: dict[str, Any]):
    """Admin: Add a new property to the database."""
    engine = get_engine()
    pid = payload.get("property_id") or f"PROP-{uuid.uuid4().hex[:6].upper()}"
    p_type = payload.get("property_type", "House")
    purpose = payload.get("purpose", "For Sale")
    city = payload.get("city", "Lahore")
    locality = payload.get("locality", "DHA Phase 6")
    location = payload.get("location") or f"{locality}, {city}"
    price = float(payload.get("price") or 25000000.0)
    area_marla = float(payload.get("area_marla") or 5.0)
    area_sqft = float(payload.get("area_sqft") or (area_marla * 225.0))
    bedrooms = int(payload.get("bedrooms") or 3)
    baths = int(payload.get("baths") or 3)
    agent = payload.get("agent", "Ahmed Raza (Sahi RealEstate)")
    agent_id = payload.get("agent_id", "AGT-01")
    date_added = datetime.date.today().strftime("%Y-%m-%d")

    price_bin = "< 1 Crore" if price < 10000000 else ("1-2 Crore" if price < 20000000 else "2+ Crore")

    sql = """
        INSERT INTO properties (
            property_id, property_type, purpose, city, locality, location,
            price, price_bin, area_marla, area_sqft, bedrooms, baths,
            latitude, longitude, date_added, agent_id, agent
        ) VALUES (
            :property_id, :property_type, :purpose, :city, :locality, :location,
            :price, :price_bin, :area_marla, :area_sqft, :bedrooms, :baths,
            31.5204, 74.3587, :date_added, :agent_id, :agent
        )
    """
    with engine.begin() as conn:
        conn.execute(
            text(sql),
            {
                "property_id": pid,
                "property_type": p_type,
                "purpose": purpose,
                "city": city,
                "locality": locality,
                "location": location,
                "price": price,
                "price_bin": price_bin,
                "area_marla": area_marla,
                "area_sqft": area_sqft,
                "bedrooms": bedrooms,
                "baths": baths,
                "date_added": date_added,
                "agent_id": agent_id,
                "agent": agent,
            },
        )

    return {"ok": True, "message": "Property added successfully", "property_id": pid}


@app.put("/api/properties/{property_id}")
async def update_property(property_id: str, payload: dict[str, Any]):
    """Admin: Edit an existing property in the database."""
    engine = get_engine()
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT property_id FROM properties WHERE property_id = :pid"),
            {"pid": property_id},
        ).first()
        if not existing:
            return JSONResponse({"ok": False, "error": "Property not found"}, status_code=404)

        updates = []
        params: Dict[str, Any] = {"pid": property_id}

        fields = ["property_type", "purpose", "city", "locality", "location", "agent"]
        for f in fields:
            if f in payload:
                updates.append(f"{f} = :{f}")
                params[f] = str(payload[f])

        if "price" in payload:
            updates.append("price = :price")
            p = float(payload["price"])
            params["price"] = p
            params["price_bin"] = "< 1 Crore" if p < 10000000 else ("1-2 Crore" if p < 20000000 else "2+ Crore")
            updates.append("price_bin = :price_bin")

        if "area_marla" in payload:
            updates.append("area_marla = :area_marla")
            params["area_marla"] = float(payload["area_marla"])
        if "bedrooms" in payload:
            updates.append("bedrooms = :bedrooms")
            params["bedrooms"] = int(payload["bedrooms"])
        if "baths" in payload:
            updates.append("baths = :baths")
            params["baths"] = int(payload["baths"])

        if updates:
            sql = f"UPDATE properties SET {', '.join(updates)} WHERE property_id = :pid"
            conn.execute(text(sql), params)

    return {"ok": True, "message": "Property updated successfully", "property_id": property_id}


@app.delete("/api/properties/{property_id}")
async def delete_property(property_id: str):
    """Admin: Remove a property from the database."""
    engine = get_engine()
    with engine.begin() as conn:
        res = conn.execute(
            text("DELETE FROM properties WHERE property_id = :pid"),
            {"pid": property_id},
        )
    return {"ok": True, "message": f"Deleted property {property_id}"}


# ===========================================================================
# 4. CRM Schedules, Appointments & Leads
# ===========================================================================

@app.get("/api/crm/appointments")
async def list_appointments():
    """Admin: Retrieve all appointment schedules."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM crm_appointments ORDER BY created_at DESC")
        ).mappings().all()
    return {"ok": True, "appointments": [dict(r) for r in rows]}


@app.post("/api/crm/appointments")
async def create_appointment(payload: dict[str, Any]):
    """Book a new property visit / appointment, create calendar event, and send confirmation email."""
    client_name = payload.get("client_name", "Valued Client").strip()
    client_phone = payload.get("client_phone", "Not Provided").strip()
    client_email = payload.get("client_email", "").strip()
    property_id = payload.get("property_id", "PROP-General").strip()
    property_title = payload.get("property_title", "Site Visit").strip()
    agent_name = payload.get("agent_name", "Ahmed Raza").strip()
    date_str = payload.get("date_str", "Tomorrow").strip()
    time_str = payload.get("time_str", "3:00 PM").strip()
    notes = payload.get("notes", "Booked via RealEstate Hub Web Portal").strip()
    if client_email and "Client Email:" not in notes:
        notes = f"{notes} | Client Email: {client_email}"

    # 1. Create calendar event with Google Calendar & iCal links
    cal_event = {}
    try:
        cal_event = create_calendar_event(
            client_name=client_name,
            phone=client_phone,
            employee=agent_name,
            property_title=property_title,
            property_id=property_id,
            date_str=date_str,
            time_str=time_str,
            notes=notes,
        )
    except Exception as e:
        logger.warning("Calendar event creation fallback: %s", e)
        cal_event = {"event_id": "evt_fallback", "google_calendar_link": "https://calendar.google.com"}

    calendar_link = payload.get("calendar_link") or cal_event.get("google_calendar_link", "")

    # 2. Upsert CRM lead with client email and requirements for auditability
    lead_id = payload.get("lead_id")
    try:
        lead_id = upsert_lead(
            client_name=client_name,
            phone=client_phone,
            email=client_email,
            property_type="House",
            stage="Meeting Scheduled",
            preferences={
                "property_id": property_id,
                "property_title": property_title,
                "date_str": date_str,
                "time_str": time_str,
                "source": "Schedule Private Tour Modal",
                "client_email": client_email,
            },
            lead_id=lead_id if lead_id and not lead_id.startswith("lead_fallback") else None,
        )
    except Exception as e:
        logger.warning("Lead upsert fallback during appointment creation: %s", e)
        lead_id = lead_id or f"lead_{uuid.uuid4().hex[:8]}"

    # 3. Log appointment in CRM
    aid = log_appointment(
        lead_id=lead_id,
        client_name=client_name,
        client_phone=client_phone,
        property_id=property_id,
        property_title=property_title,
        agent_name=agent_name,
        date_str=date_str,
        time_str=time_str,
        status=payload.get("status", "scheduled"),
        calendar_event_id=cal_event.get("event_id", ""),
        calendar_link=calendar_link,
        notes=notes,
    )

    # 4. Dispatch confirmation email to client and assigned agent
    email_result = {}
    try:
        email_result = send_appointment_email(
            employee_name=agent_name,
            client_name=client_name,
            client_phone=client_phone,
            property_title=property_title,
            property_id=property_id,
            date_str=date_str,
            time_str=time_str,
            requirements=f"Private Tour scheduled for {property_title}",
            notes=notes,
            calendar_link=calendar_link,
            event_type="booking",
            appointment_id=aid,
            client_email=client_email,
        )
    except Exception as e:
        logger.warning("Appointment email dispatch fallback: %s", e)

    return {
        "ok": True,
        "appointment_id": aid,
        "lead_id": lead_id,
        "calendar_link": calendar_link,
        "email_sent": bool(email_result.get("email_id")),
        "smtp_delivered": email_result.get("smtp_delivered", False),
        "client_email": client_email,
        "message": f"Appointment {aid} scheduled successfully. Confirmation sent to {client_email}" if client_email else f"Appointment {aid} scheduled successfully",
    }


@app.post("/api/crm/appointments/{appointment_id}/reschedule")
async def reschedule_appointment(appointment_id: str, payload: dict[str, Any]):
    """Admin/User: Reschedule appointment."""
    new_date = payload.get("date_str") or payload.get("new_date_str", "Tomorrow")
    new_time = payload.get("time_str") or payload.get("new_time_str", "5:00 PM")
    notes = payload.get("notes") or payload.get("reason", "Rescheduled via web portal")
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    engine = get_engine()
    with engine.begin() as conn:
        res = conn.execute(
            text("""
                UPDATE crm_appointments 
                SET date_str = :d, time_str = :t, status = 'rescheduled', 
                    notes = :notes, updated_at = :up 
                WHERE appointment_id = :aid
            """),
            {"d": new_date, "t": new_time, "notes": notes, "up": now_iso, "aid": appointment_id},
        )
    return {"ok": True, "message": "Appointment rescheduled successfully"}


@app.post("/api/crm/appointments/{appointment_id}/cancel")
async def cancel_appointment(appointment_id: str, payload: dict[str, Any]):
    """Admin/User: Cancel appointment."""
    reason = payload.get("reason", "Cancelled by client request")
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("""
                UPDATE crm_appointments 
                SET status = 'cancelled', notes = :reason, updated_at = :up 
                WHERE appointment_id = :aid
            """),
            {"reason": reason, "up": now_iso, "aid": appointment_id},
        )
    return {"ok": True, "message": "Appointment cancelled successfully"}


@app.get("/api/crm/leads")
async def list_leads():
    """Admin: Retrieve all CRM client leads."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM crm_leads ORDER BY created_at DESC")
        ).mappings().all()
    return {"ok": True, "leads": [dict(r) for r in rows]}


@app.get("/api/crm/stats")
async def get_crm_stats():
    """Aggregate CRM and inventory statistics."""
    engine = get_engine()
    with engine.connect() as conn:
        total_properties = conn.execute(text("SELECT count(*) FROM properties")).scalar() or 0
        total_appointments = conn.execute(text("SELECT count(*) FROM crm_appointments")).scalar() or 0
        scheduled_appts = conn.execute(text("SELECT count(*) FROM crm_appointments WHERE LOWER(status) = 'scheduled'")).scalar() or 0
        total_leads = conn.execute(text("SELECT count(*) FROM crm_leads")).scalar() or 0

    return {
        "ok": True,
        "stats": {
            "total_properties": total_properties,
            "total_appointments": total_appointments,
            "scheduled_appointments": scheduled_appts,
            "total_leads": total_leads,
            "active_ai_sessions": len(CALL_SESSIONS),
        },
    }


@app.post("/api/contact")
async def contact_form_submit(payload: dict[str, Any]):
    """Receive contact form submission, log CRM lead, and dispatch email directly to umersahi5p@gmail.com."""
    name = payload.get("name", "").strip()
    email = payload.get("email", "").strip()
    phone = payload.get("phone", "").strip()
    inquiry_type = payload.get("inquiry_type", "Luxury Inquiry").strip()
    city = payload.get("city", "Islamabad").strip()
    budget = payload.get("budget", "Not Specified").strip()
    message = payload.get("message", "").strip()

    if not name or not email or not message:
        return JSONResponse({"ok": False, "error": "Name, email, and message are required."}, status_code=400)

    # 1. Upsert lead in CRM database for auditability and Admin Portal tracking
    try:
        lead_id = upsert_lead(
            client_name=name,
            phone=phone or "Not Provided",
            email=email,
            city=city,
            budget=budget,
            property_type=inquiry_type,
            preferences={
                "inquiry_type": inquiry_type,
                "message": message,
                "source": "Website Contact Form",
                "requirements": f"[{inquiry_type}] in {city} (Budget: {budget}). Message: {message}",
            },
        )
    except Exception as e:
        logger.warning("CRM lead upsert exception: %s", e)
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"

    # 2. Dispatch email to umersahi5p@gmail.com
    email_result = send_direct_contact_email(
        name=name,
        email=email,
        phone=phone,
        inquiry_type=inquiry_type,
        city=city,
        budget=budget,
        message=message,
        target_email="umersahi5p@gmail.com",
    )

    return {
        "ok": True,
        "lead_id": lead_id,
        "email_id": email_result.get("email_id"),
        "smtp_delivered": email_result.get("smtp_delivered", False),
        "target_email": "umersahi5p@gmail.com",
        "message": "Your inquiry has been successfully dispatched to umersahi5p@gmail.com.",
    }


# ===========================================================================
# 5. Interactive LangGraph Chat Agent
# ===========================================================================

@app.post("/api/chat")
async def chat_endpoint(payload: dict[str, Any]):
    """Execute turn in Day 5 LangGraph agent and return response + recommended properties."""
    message = payload.get("message", "").strip()
    session_id = payload.get("session_id") or f"web-{uuid.uuid4().hex[:12]}"

    if not message:
        return JSONResponse({"ok": False, "error": "Message cannot be empty."}, status_code=400)

    if session_id not in CALL_SESSIONS:
        CALL_SESSIONS[session_id] = create_initial_state(session_id=session_id)

    state = CALL_SESSIONS[session_id]

    try:
        updated_state = await asyncio.to_thread(
            run_agent_turn,
            user_message=message,
            current_state=state,
            session_id=session_id,
        )
        CALL_SESSIONS[session_id] = updated_state
        reply = updated_state.get("final_response", "Assalam-o-Alaikum! Main aap ki property dhoondne mein madad kar sakta hoon.")
        intent = updated_state.get("intent", "recommendation")
        prefs = updated_state.get("property_preferences", {})

        # Only return recommended property cards if the agent actually made a recommendation
        # (NOT during clarification questions, booking info gathering, or greetings)
        recommended_props = []
        if updated_state.get("clarification_needed", False):
            recommended_props = []
        elif updated_state.get("recommended_properties") and intent in ("recommendation", "booking"):
            recommended_props = updated_state.get("recommended_properties", [])[:3]
        elif intent == "recommendation":
            city = prefs.get("city") or "Lahore"
            budget = updated_state.get("budget") or 200_000_000.0
            prop_type = prefs.get("property_type")
            marla = prefs.get("area_marla")
            purpose = prefs.get("purpose", "For Sale")
            locality = prefs.get("locality")

            matching_result = search_properties_core(
                city=city,
                budget_max=budget,
                area_marla=marla,
                property_type=prop_type,
                purpose=purpose,
                locality_contains=locality,
                top_n=3,
            )
            recommended_props = matching_result.get("properties", []) if matching_result.get("success") else []

        return {
            "ok": True,
            "session_id": session_id,
            "reply": reply,
            "intent": intent,
            "preferences": prefs,
            "recommended_properties": recommended_props,
        }
    except Exception as e:
        logger.exception("Chat processing error: %s", e)
        return {
            "ok": True,
            "session_id": session_id,
            "reply": "Ji, main aap ki property search aur site visit booking mein madad kar sakta hoon. Aap kis city mein property dekh rahe hain?",
            "intent": "general",
            "recommended_properties": [],
        }


# ===========================================================================
# 6. Vapi Voice Endpoints (Webhook & Assistant Config)
# ===========================================================================

def sync_vapi_assistant_language(target_language: str = "ur") -> dict[str, Any]:
    """Sync the Vapi Assistant language and transcriber settings on Vapi Cloud."""
    assistant_id = os.getenv("VAPI_ASSISTANT_ID", "").strip()
    private_key = os.getenv("VAPI_PRIVATE_KEY", "").strip()
    if not assistant_id or not private_key:
        return {"ok": False, "message": "VAPI_ASSISTANT_ID or VAPI_PRIVATE_KEY not configured."}

    patch_payload = {
        "language": target_language,
        "transcriber": {
            "provider": "deepgram",
            "model": VAPI_TRANSCRIBER_MODEL,
            "language": target_language,
            "smartFormat": True,
        },
    }
    req = urllib.request.Request(
        f"https://api.vapi.ai/assistant/{assistant_id}",
        data=json.dumps(patch_payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {private_key}",
            "Content-Type": "application/json",
            "User-Agent": "realestate-hub-vapi/1.0",
        },
        method="PATCH",
    )
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            logger.info("Vapi assistant %s language verified as '%s'.", assistant_id, target_language)
            return {
                "ok": True,
                "assistant_id": assistant_id,
                "language": target_language,
                "transcriber": data.get("transcriber"),
            }
    except Exception as e:
        logger.warning("Could not auto-sync Vapi assistant language: %s", e)
        return {"ok": False, "error": str(e)}


@app.on_event("startup")
async def on_startup():
    """Verify and synchronize Vapi assistant language on server startup."""
    try:
        asyncio.create_task(asyncio.to_thread(sync_vapi_assistant_language, VAPI_TRANSCRIBER_LANGUAGE))
    except Exception as e:
        logger.warning("Startup language sync warning: %s", e)


@app.post("/vapi/sync-language")
@app.get("/vapi/sync-language")
async def vapi_sync_language(lang: str = Query("ur")):
    """Admin / API endpoint to sync language to 'ur' on Vapi Cloud."""
    result = await asyncio.to_thread(sync_vapi_assistant_language, lang)
    return result


@app.get("/vapi/assistant-config")
async def vapi_assistant_config():
    """Inline assistant configuration for Vapi."""
    url = get_backend_public_url()
    if not url:
        return JSONResponse(
            {"error": "BACKEND_PUBLIC_URL is not set and no ngrok tunnel detected."},
            status_code=500,
        )
    assistant_id = os.getenv("VAPI_ASSISTANT_ID", "").strip()
    public_key = os.getenv("VAPI_PUBLIC_KEY", "").strip()
    return {
        "assistantId": assistant_id,
        "id": assistant_id,
        "publicKey": public_key,
        "name": VAPI_ASSISTANT_NAME,
        "language": VAPI_TRANSCRIBER_LANGUAGE,
        "firstMessage": FIRST_MESSAGE,
        "model": {
            "provider": "custom-llm",
            "url": f"{url}/vapi/llm",
            "model": os.getenv("GEMINI_LLM_MODEL", "gemini-3.5-flash-lite"),
            "messages": [
                {
                    "role": "system",
                    "content": "RealEstate Hub LangGraph AI Agent. You communicate in Urdu / Roman Urdu (UrduLish) to assist clients with property search and bookings in Pakistan."
                }
            ],
        },
        "transcriber": {
            "provider": "deepgram",
            "model": VAPI_TRANSCRIBER_MODEL,
            "language": VAPI_TRANSCRIBER_LANGUAGE,
            "smartFormat": True,
            "keyterm": ["DHA", "Bahria Town", "Gulberg", "Islamabad", "Lahore", "crore", "lakh", "Marla", "Kanal", "flat", "ghar"],
        },
        "voice": {
            "provider": VAPI_VOICE_PROVIDER,
            "voiceId": VAPI_VOICE_ID,
        },
    }


def _openai_chunk(model: str, content: str | None = None, finish_reason: str | None = None, cid: str = "", include_role: bool = False) -> dict:
    delta: dict[str, Any] = {}
    if include_role:
        delta["role"] = "assistant"
    if content is not None:
        delta["content"] = content
    return {
        "id": cid,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }


async def _stream_langgraph_response(user_text: str, call_id: str, model: str):
    """Stream LangGraph turn chunks directly to Vapi."""
    cid = f"chatcmpl-{uuid.uuid4().hex[:20]}"
    yield f"data: {json.dumps(_openai_chunk(model, None, None, cid, include_role=True))}\n\n"

    if call_id not in CALL_SESSIONS:
        CALL_SESSIONS[call_id] = create_initial_state(session_id=call_id)
    state = CALL_SESSIONS[call_id]

    try:
        updated_state = await asyncio.to_thread(
            run_agent_turn,
            user_message=user_text,
            current_state=state,
            session_id=call_id,
        )
        CALL_SESSIONS[call_id] = updated_state
        answer = updated_state.get("final_response", "Ji, main aap ki kya madad kar sakta hoon?")
    except Exception as e:
        logger.exception("Error during LangGraph voice turn: %s", e)
        answer = "Maaf kijiye ga, system mein rabta nahi ho saka. Baraye meherbani dobara bataiye."

    words = answer.split(" ")
    step = 4
    for i in range(0, len(words), step):
        piece = " ".join(words[i:i + step])
        if i + step < len(words):
            piece += " "
        yield f"data: {json.dumps(_openai_chunk(model, piece, None, cid))}\n\n"
        await asyncio.sleep(0.02)

    yield f"data: {json.dumps(_openai_chunk(model, None, 'stop', cid))}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/vapi/llm/chat/completions")
@app.post("/vapi/llm")
@app.post("/chat/completions")
@app.post("/vapi/llm/chat/completions/chat/completions")
async def chat_completions(req: Request):
    """OpenAI-compatible Custom LLM endpoint invoked by Vapi voice calls."""
    body = await req.json()
    model = body.get("model", os.getenv("GEMINI_LLM_MODEL", "gemini-3.5-flash-lite"))
    messages = body.get("messages", [])
    call_id = body.get("call", {}).get("id") or str(uuid.uuid4())

    user_text = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_text = m.get("content", "")
            break

    if not user_text.strip():
        user_text = "Assalam-o-Alaikum"

    return StreamingResponse(
        _stream_langgraph_response(user_text=user_text, call_id=call_id, model=model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
