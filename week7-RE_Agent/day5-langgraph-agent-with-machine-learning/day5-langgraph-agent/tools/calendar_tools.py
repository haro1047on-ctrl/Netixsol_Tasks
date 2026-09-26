"""Task 3: Google Calendar & iCal Tool.

Provides seamless calendar event generation, Google Calendar web links,
iCal (.ics) exports, event updates, and cancellations.
"""
from __future__ import annotations

import datetime
import json
import os
import urllib.parse
import uuid
from typing import Any, Dict, Optional
from langchain_core.tools import tool

from config import STORAGE_DIR

CALENDAR_DIR = STORAGE_DIR / "calendar"
CALENDAR_DIR.mkdir(parents=True, exist_ok=True)


def _generate_gcal_link(title: str, details: str, location: str, start_dt: datetime.datetime, duration_mins: int = 45) -> str:
    """Generate one-click direct Google Calendar event creation URL."""
    end_dt = start_dt + datetime.timedelta(minutes=duration_mins)
    fmt = "%Y%m%dT%H%M%SZ"
    params = {
        "action": "TEMPLATE",
        "text": title,
        "details": details,
        "location": location,
        "dates": f"{start_dt.strftime(fmt)}/{end_dt.strftime(fmt)}",
    }
    return f"https://calendar.google.com/calendar/render?{urllib.parse.urlencode(params)}"


def _generate_ics(event_id: str, title: str, details: str, location: str, start_dt: datetime.datetime, duration_mins: int = 45) -> str:
    """Generate standard iCalendar (.ics) RFC 5545 data."""
    end_dt = start_dt + datetime.timedelta(minutes=duration_mins)
    fmt = "%Y%m%dT%H%M%SZ"
    now_fmt = datetime.datetime.now(datetime.timezone.utc).strftime(fmt)
    clean_details = details.replace("\n", "\\n")
    return (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//RealEstate Hub//LangGraph Agent//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        "METHOD:REQUEST\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{event_id}@realestatehub.pk\r\n"
        f"DTSTAMP:{now_fmt}\r\n"
        f"DTSTART:{start_dt.strftime(fmt)}\r\n"
        f"DTEND:{end_dt.strftime(fmt)}\r\n"
        f"SUMMARY:{title}\r\n"
        f"DESCRIPTION:{clean_details}\r\n"
        f"LOCATION:{location}\r\n"
        "STATUS:CONFIRMED\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )


def _parse_datetime(date_str: str, time_str: str) -> datetime.datetime:
    """Parse date and time strings into UTC datetime."""
    now = datetime.datetime.now(datetime.timezone.utc)
    target_date = now.date()

    d_clean = date_str.lower().strip()
    if "kal" in d_clean or "tomorrow" in d_clean or "کل" in d_clean:
        target_date = (now + datetime.timedelta(days=1)).date()
    elif "parso" in d_clean or "day after" in d_clean or "پرسوں" in d_clean:
        target_date = (now + datetime.timedelta(days=2)).date()
    else:
        for fmt in (
            "%Y-%m-%d",
            "%a, %b %d, %Y",
            "%A, %B %d, %Y",
            "%a, %d %b %Y",
            "%b %d, %Y",
            "%B %d, %Y",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%Y/%m/%d",
            "%B %d",
            "%b %d",
        ):
            try:
                p = datetime.datetime.strptime(date_str.strip(), fmt)
                if p.year == 1900:
                    p = p.replace(year=now.year)
                target_date = p.date()
                break
            except ValueError:
                continue

    hour, minute = 15, 0
    t_clean = time_str.lower().strip()
    if "shaam" in t_clean or "pm" in t_clean or "evening" in t_clean:
        hour = 17
    elif "subah" in t_clean or "am" in t_clean or "morning" in t_clean:
        hour = 11

    import re
    m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|baje)?", t_clean)
    if m:
        num = int(m.group(1))
        min_p = int(m.group(2)) if m.group(2) else 0
        ampm = m.group(3) or ""
        if ampm == "pm" and num < 12:
            num += 12
        elif ampm == "am" and num == 12:
            num = 0
        if 0 <= num <= 23:
            hour = num
        if 0 <= min_p <= 59:
            minute = min_p

    return datetime.datetime(target_date.year, target_date.month, target_date.day, hour, minute, 0, tzinfo=datetime.timezone.utc)


def create_calendar_event(
    client_name: str,
    phone: str,
    employee: str,
    property_title: str,
    property_id: str,
    date_str: str,
    time_str: str,
    notes: str = "",
) -> Dict[str, Any]:
    """Create a new calendar visit event with Google Calendar and iCal links."""
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    start_dt = _parse_datetime(date_str, time_str)

    title = f"Property Visit: {property_title or property_id} with {client_name}"
    details = (
        f"RealEstate Hub Scheduled Property Visit\n"
        f"Client: {client_name} ({phone})\n"
        f"Assigned Agent: {employee}\n"
        f"Property: {property_title} ({property_id})\n"
        f"Date: {date_str} at {time_str}\n"
        f"Notes: {notes}\n"
    )
    location = property_title or "RealEstate Hub Site Visit"
    gcal_link = _generate_gcal_link(title, details, location, start_dt)
    ics_data = _generate_ics(event_id, title, details, location, start_dt)

    event_record = {
        "event_id": event_id,
        "client_name": client_name,
        "phone": phone,
        "employee": employee,
        "property_title": property_title,
        "property_id": property_id,
        "date_str": date_str,
        "time_str": time_str,
        "notes": notes,
        "google_calendar_link": gcal_link,
        "status": "confirmed",
        "created_at": created_at,
    }

    # Save to disk
    try:
        (CALENDAR_DIR / f"{event_id}.json").write_text(json.dumps(event_record, indent=2), encoding="utf-8")
        (CALENDAR_DIR / f"{event_id}.ics").write_text(ics_data, encoding="utf-8")
    except Exception:
        pass

    return event_record


def update_calendar_event(
    event_id: str,
    date_str: str,
    time_str: str,
    notes: str = "",
) -> Dict[str, Any]:
    """Reschedule an existing calendar event."""
    file_path = CALENDAR_DIR / f"{event_id}.json"
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    else:
        data = {
            "event_id": event_id,
            "client_name": "Valued Client",
            "phone": "Not Provided",
            "employee": "Ahmed Raza",
            "property_title": "RealEstate Hub Property",
            "property_id": "PROP-General",
            "notes": notes,
        }

    data["date_str"] = date_str
    data["time_str"] = time_str
    data["status"] = "rescheduled"
    if notes:
        data["notes"] = notes

    start_dt = _parse_datetime(date_str, time_str)
    title = f"Rescheduled: Visit for {data.get('property_title', 'Property')} with {data.get('client_name', 'Client')}"
    details = (
        f"RESCHEDULED Property Visit\n"
        f"Client: {data.get('client_name', 'Client')} ({data.get('phone', 'N/A')})\n"
        f"Agent: {data.get('employee', 'Ahmed Raza')}\n"
        f"Property: {data.get('property_title', 'Property')}\n"
        f"New Date: {date_str} at {time_str}\n"
        f"Notes: {data.get('notes', '')}\n"
    )
    gcal_link = _generate_gcal_link(title, details, data.get("property_title", "Site Visit"), start_dt)
    data["google_calendar_link"] = gcal_link

    try:
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        ics_data = _generate_ics(event_id, title, details, data.get("property_title", "Site Visit"), start_dt)
        (CALENDAR_DIR / f"{event_id}.ics").write_text(ics_data, encoding="utf-8")
    except Exception:
        pass

    return data


def cancel_calendar_event(event_id: str, reason: str = "Cancelled by client") -> bool:
    """Cancel a calendar event."""
    file_path = CALENDAR_DIR / f"{event_id}.json"
    if file_path.exists():
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            data["status"] = "cancelled"
            data["cancellation_reason"] = reason
            file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
    return True


@tool
def calendar_tool(
    action: str,  # 'create', 'reschedule', 'cancel'
    client_name: Optional[str] = "Valued Client",
    phone: Optional[str] = "Not Provided",
    employee: Optional[str] = "Ahmed Raza",
    property_title: Optional[str] = "Property Visit",
    property_id: Optional[str] = "PROP-General",
    date_str: Optional[str] = "Tomorrow",
    time_str: Optional[str] = "3:00 PM",
    notes: Optional[str] = "",
    event_id: Optional[str] = None,
) -> str:
    """Manage property visit appointments in Google Calendar and iCal."""
    action_clean = action.lower().strip()
    if action_clean == "create":
        res = create_calendar_event(
            client_name=client_name or "Valued Client",
            phone=phone or "Not Provided",
            employee=employee or "Ahmed Raza",
            property_title=property_title or "Property Visit",
            property_id=property_id or "PROP-General",
            date_str=date_str or "Tomorrow",
            time_str=time_str or "3:00 PM",
            notes=notes or "",
        )
    elif action_clean in ("reschedule", "update"):
        res = update_calendar_event(
            event_id=event_id or f"evt_{uuid.uuid4().hex[:8]}",
            date_str=date_str or "Tomorrow",
            time_str=time_str or "3:00 PM",
            notes=notes or "",
        )
    elif action_clean in ("cancel", "delete"):
        cancel_calendar_event(event_id=event_id or "", reason=notes or "Client requested cancellation")
        res = {"status": "cancelled", "event_id": event_id}
    else:
        res = {"error": f"Unknown calendar action '{action}'"}

    return json.dumps(res, indent=2)
