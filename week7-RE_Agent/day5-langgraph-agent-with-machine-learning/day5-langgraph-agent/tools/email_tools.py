"""Task 3: Email Automation Tool.

Automatically sends structured HTML & plain-text notifications to assigned
RealEstate Hub employees/agents for bookings, reschedules, and cancellations.
Matches exact template from LangChain architecture.
"""
from __future__ import annotations

import datetime
import json
import os
import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional
from langchain_core.tools import tool

from config import STORAGE_DIR

EMAIL_DIR = STORAGE_DIR / "emails"
EMAIL_DIR.mkdir(parents=True, exist_ok=True)

AGENT_EMAIL_ROSTER = {
    "Ahmed Raza": "ahmed.raza@realestatehub.pk",
    "Sana Malik": "sana.malik@realestatehub.pk",
    "Bilal Chaudhry": "bilal.chaudhry@realestatehub.pk",
    "Ayesha Farooq": "ayesha.farooq@realestatehub.pk",
    "Usman Tariq": "usman.tariq@realestatehub.pk",
    "Hina Shaikh": "hina.shaikh@realestatehub.pk",
    "Faisal Mehmood": "faisal.mehmood@realestatehub.pk",
    "Mahnoor Iqbal": "mahnoor.iqbal@realestatehub.pk",
}
DEFAULT_SENDER = os.getenv("NOTIFICATION_SENDER", "appointments@realestatehub.pk")


def get_agent_email(agent_name: str, ignore_override: bool = False) -> str:
    """Resolve employee email address from agent roster or test override."""
    override = os.getenv("EMPLOYEE_NOTIFICATION_EMAIL", "").strip()
    if override and not ignore_override:
        return override
    clean = agent_name.strip()
    if clean in AGENT_EMAIL_ROSTER:
        return AGENT_EMAIL_ROSTER[clean]
    slug = clean.lower().replace(" ", ".")
    return f"{slug}@realestatehub.pk"


def _build_html_email(
    subject: str,
    headline: str,
    action_color: str,
    employee_name: str,
    client_name: str,
    client_phone: str,
    property_title: str,
    property_id: str,
    date_str: str,
    time_str: str,
    requirements: str,
    notes: str,
    calendar_link: str = "",
    appointment_id: str = "",
) -> str:
    """Generate professional responsive HTML email template matching LangChain original."""
    appt_badge = f"""
      <div style="background: #e0f2fe; border: 2px dashed #0284c7; border-radius: 8px; padding: 14px 18px; margin-bottom: 20px; text-align: center;">
        <div style="font-size: 12px; font-weight: 700; text-transform: uppercase; color: #0369a1; letter-spacing: 0.5px;">Your Unique Appointment ID</div>
        <div style="font-size: 24px; font-weight: 800; color: #0284c7; margin: 6px 0; letter-spacing: 1px;">{appointment_id}</div>
        <div style="font-size: 13px; color: #075985;">Save this ID to reschedule or cancel your visit anytime via phone call or web.</div>
      </div>
    """ if appointment_id else ""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f8; margin: 0; padding: 20px; color: #1e293b; }}
    .card {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }}
    .header {{ background: {action_color}; color: #ffffff; padding: 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; }}
    .header p {{ margin: 6px 0 0 0; opacity: 0.9; font-size: 14px; }}
    .content {{ padding: 28px; }}
    .section {{ margin-bottom: 20px; }}
    .section-title {{ font-size: 13px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 8px; letter-spacing: 0.5px; }}
    .info-grid {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; }}
    .info-row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px dashed #e2e8f0; font-size: 14px; }}
    .info-row:last-child {{ border-bottom: none; }}
    .info-label {{ color: #64748b; font-weight: 500; }}
    .info-value {{ color: #0f172a; font-weight: 600; text-align: right; }}
    .btn-container {{ text-align: center; margin-top: 24px; }}
    .btn {{ display: inline-block; background: #0284c7; color: #ffffff !important; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; }}
    .footer {{ background: #f1f5f9; padding: 16px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>{headline}</h1>
      <p>RealEstate Hub Voice Assistant Automation</p>
    </div>
    <div class="content">
      {appt_badge}
      <p style="font-size: 15px; margin-top: 0;">Hello <strong>{client_name or employee_name}</strong>,</p>
      <p style="font-size: 14px; color: #475569;">Property visit details recorded via the RealEstate Hub Voice AI Agent:</p>
      
      <div class="section">
        <div class="section-title">📅 Meeting Schedule</div>
        <div class="info-grid">
          {f'''<div class="info-row"><span class="info-label">Appointment ID:</span><span class="info-value" style="color:#0284c7;">{appointment_id}</span></div>''' if appointment_id else ''}
          <div class="info-row"><span class="info-label">Date:</span><span class="info-value">{date_str}</span></div>
          <div class="info-row"><span class="info-label">Time:</span><span class="info-value">{time_str}</span></div>
          <div class="info-row"><span class="info-label">Assigned Agent:</span><span class="info-value">{employee_name}</span></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">🏡 Property Details</div>
        <div class="info-grid">
          <div class="info-row"><span class="info-label">Property:</span><span class="info-value">{property_title}</span></div>
          <div class="info-row"><span class="info-label">Listing ID:</span><span class="info-value">{property_id}</span></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">👤 Client Details & Requirements</div>
        <div class="info-grid">
          <div class="info-row"><span class="info-label">Client Name:</span><span class="info-value">{client_name}</span></div>
          <div class="info-row"><span class="info-label">Phone:</span><span class="info-value">{client_phone}</span></div>
          <div class="info-row"><span class="info-label">Requirements:</span><span class="info-value">{requirements or 'Looking for property'}</span></div>
          <div class="info-row"><span class="info-label">Call Notes:</span><span class="info-value">{notes or 'Voice Agent Qualified Lead'}</span></div>
        </div>
      </div>

      {f'''<div class="btn-container">
        <a href="{calendar_link}" class="btn" target="_blank">➕ Add to Google Calendar</a>
      </div>''' if calendar_link else ''}
    </div>
    <div class="footer">
      RealEstate Hub Automated Business Dispatcher &bull; Confirmed via Voice AI
    </div>
  </div>
</body>
</html>"""


def send_appointment_email(
    employee_name: str,
    client_name: str,
    client_phone: str,
    property_title: str,
    property_id: str,
    date_str: str,
    time_str: str,
    requirements: str = "",
    notes: str = "",
    calendar_link: str = "",
    event_type: str = "booking",
    appointment_id: str = "",
    client_email: str = "",
) -> Dict[str, Any]:
    """Send appointment notification email to assigned employee/agent and client with Appointment ID."""
    recipient_email = get_agent_email(employee_name)
    email_id = f"eml_{uuid.uuid4().hex[:12]}"
    sent_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    id_tag = f"[{appointment_id}] " if appointment_id else ""

    if event_type == "reschedule":
        subject = f"{id_tag}[RESCHEDULED] Visit for {property_title} with {client_name}"
        headline = "🗓️ Appointment Rescheduled"
        action_color = "#d97706"  # Amber
    elif event_type == "cancellation":
        subject = f"{id_tag}[CANCELLED] Visit for {property_title} with {client_name}"
        headline = "❌ Appointment Cancelled"
        action_color = "#dc2626"  # Red
    else:
        subject = f"{id_tag}[NEW VISIT] {property_title} on {date_str} with {client_name}"
        headline = "✨ New Property Visit Scheduled"
        action_color = "#0f766e"  # Teal

    html_content = _build_html_email(
        subject=subject,
        headline=headline,
        action_color=action_color,
        employee_name=employee_name,
        client_name=client_name,
        client_phone=client_phone,
        property_title=property_title,
        property_id=property_id,
        date_str=date_str,
        time_str=time_str,
        requirements=requirements,
        notes=notes,
        calendar_link=calendar_link,
        appointment_id=appointment_id,
    )

    plain_text = (
        f"{headline}\n"
        f"===================================\n"
        f"Appointment ID: {appointment_id or 'N/A'} (Save this ID to reschedule or cancel your visit)\n"
        f"Employee: {employee_name} ({recipient_email})\n"
        f"Client: {client_name} (Phone: {client_phone})\n"
        f"Property: {property_title} ({property_id})\n"
        f"Date & Time: {date_str} at {time_str}\n"
        f"Requirements: {requirements}\n"
        f"Notes: {notes}\n"
        f"Calendar Link: {calendar_link}\n"
    )

    # Attempt live SMTP if configured in .env
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_delivered = False
    smtp_error = None

    target_recipients = [recipient_email]
    customer_email = client_email or os.getenv("CLIENT_NOTIFICATION_EMAIL", "").strip()
    if customer_email and customer_email not in target_recipients:
        target_recipients.append(customer_email)

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = DEFAULT_SENDER
            msg["To"] = ", ".join(target_recipients)
            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=4.0) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(DEFAULT_SENDER, target_recipients, msg.as_string())
            smtp_delivered = True
        except Exception as e:
            smtp_error = str(e)

    record = {
        "email_id": email_id,
        "appointment_id": appointment_id,
        "event_type": event_type,
        "recipient": recipient_email,
        "customer_email": customer_email,
        "employee_name": employee_name,
        "client_name": client_name,
        "client_phone": client_phone,
        "property_title": property_title,
        "property_id": property_id,
        "date_str": date_str,
        "time_str": time_str,
        "subject": subject,
        "plain_text": plain_text,
        "sent_at": sent_at,
        "smtp_delivered": smtp_delivered,
        "smtp_error": smtp_error,
    }

    try:
        (EMAIL_DIR / f"{email_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        (EMAIL_DIR / f"{email_id}.html").write_text(html_content, encoding="utf-8")
    except Exception:
        pass

    return record


@tool("email_tool")
def email_tool(
    employee_name: str,
    client_name: str,
    client_phone: str,
    property_title: str,
    property_id: str,
    date_str: str,
    time_str: str,
    requirements: str = "",
    notes: str = "",
    calendar_link: str = "",
    event_type: str = "booking",
) -> str:
    """Tool for sending automated email alerts to assigned real estate agents."""
    res = send_appointment_email(
        employee_name=employee_name,
        client_name=client_name,
        client_phone=client_phone,
        property_title=property_title,
        property_id=property_id,
        date_str=date_str,
        time_str=time_str,
        requirements=requirements,
        notes=notes,
        calendar_link=calendar_link,
        event_type=event_type,
    )
    return json.dumps(res, indent=2)


def send_direct_contact_email(
    name: str,
    email: str,
    phone: str,
    inquiry_type: str = "General Inquiry",
    city: str = "Islamabad",
    budget: str = "Not Specified",
    message: str = "",
    target_email: str = "umersahi5p@gmail.com",
) -> dict[str, Any]:
    """Send a VIP luxury client inquiry directly to umersahi5p@gmail.com via SMTP."""
    email_id = f"contact_{uuid.uuid4().hex[:10]}"
    sent_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    subject = f"[RealEstate Hub Inquiry] {inquiry_type} - {name} ({city})"

    plain_text = (
        f"RealEstate Hub - New Client Inquiry\n"
        f"====================================\n"
        f"Client Name: {name}\n"
        f"Client Email: {email}\n"
        f"Client Phone/WhatsApp: {phone}\n"
        f"Inquiry Type: {inquiry_type}\n"
        f"Preferred City: {city}\n"
        f"Estimated Budget: {budget}\n\n"
        f"Message / Requirements:\n{message}\n\n"
        f"Timestamp: {sent_at}\n"
        f"Direct Recipient: {target_email}\n"
    )

    clean_wa_phone = "".join(c for c in phone if c.isdigit())
    if not clean_wa_phone.startswith("92") and len(clean_wa_phone) == 11 and clean_wa_phone.startswith("0"):
        clean_wa_phone = "92" + clean_wa_phone[1:]

    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{subject}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #070b14; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #e2e8f0;">
  <div style="max-width: 600px; margin: 30px auto; background-color: #0d1527; border: 1px solid rgba(245, 180, 100, 0.35); border-radius: 18px; overflow: hidden; box-shadow: 0 20px 50px rgba(0, 0, 0, 0.7);">
    <div style="background: linear-gradient(90deg, #f5b464, #f59e0b, #d97706); height: 5px;"></div>
    
    <div style="padding: 28px 32px; background-color: #090e1c; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
      <table style="width: 100%;">
        <tr>
          <td>
            <div style="font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: -0.5px;">RealEstate Hub Pakistan</div>
            <div style="font-size: 11px; color: #f5b464; letter-spacing: 2px; text-transform: uppercase; margin-top: 2px;">New VIP Client Inquiry</div>
          </td>
          <td style="text-align: right;">
            <span style="display: inline-block; padding: 5px 12px; font-size: 11px; font-weight: 600; color: #f5b464; background-color: rgba(245, 180, 100, 0.15); border: 1px solid rgba(245, 180, 100, 0.3); border-radius: 20px;">
              Direct Priority
            </span>
          </td>
        </tr>
      </table>
    </div>

    <div style="padding: 32px;">
      <h2 style="font-size: 17px; font-weight: 600; color: #ffffff; margin-top: 0; margin-bottom: 20px;">
        Inquiry Details: <span style="color: #f5b464;">{inquiry_type}</span>
      </h2>

      <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px; font-size: 13px;">
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
          <td style="padding: 10px 0; color: #94a3b8; width: 140px;">Client Name</td>
          <td style="padding: 10px 0; color: #ffffff; font-weight: 600;">{name}</td>
        </tr>
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
          <td style="padding: 10px 0; color: #94a3b8;">Email</td>
          <td style="padding: 10px 0; color: #f5b464;"><a href="mailto:{email}" style="color: #f5b464; text-decoration: none;">{email}</a></td>
        </tr>
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
          <td style="padding: 10px 0; color: #94a3b8;">Phone / WhatsApp</td>
          <td style="padding: 10px 0; color: #38bdf8;"><a href="tel:{phone}" style="color: #38bdf8; text-decoration: none;">{phone}</a></td>
        </tr>
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
          <td style="padding: 10px 0; color: #94a3b8;">Preferred City</td>
          <td style="padding: 10px 0; color: #ffffff;">{city}</td>
        </tr>
        <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.06);">
          <td style="padding: 10px 0; color: #94a3b8;">Budget Range</td>
          <td style="padding: 10px 0; color: #10b981; font-weight: 600;">{budget}</td>
        </tr>
      </table>

      <div style="margin-top: 20px; background-color: #080d19; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 18px;">
        <div style="font-size: 11px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Client Message:</div>
        <div style="font-size: 13px; line-height: 1.6; color: #f1f5f9; white-space: pre-wrap;">{message}</div>
      </div>

      <div style="margin-top: 28px; text-align: center;">
        <a href="mailto:{email}?subject=Regarding your inquiry on RealEstate Hub" style="display: inline-block; padding: 12px 26px; background: linear-gradient(90deg, #f5b464, #d97706); color: #020617; font-weight: 700; font-size: 13px; text-decoration: none; border-radius: 30px; margin-right: 10px;">Reply to Client</a>
        <a href="https://wa.me/{clean_wa_phone}" style="display: inline-block; padding: 12px 24px; background-color: rgba(255, 255, 255, 0.08); color: #ffffff; font-weight: 600; font-size: 13px; text-decoration: none; border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 30px;">Chat on WhatsApp</a>
      </div>
    </div>

    <div style="padding: 18px 32px; background-color: #060912; border-top: 1px solid rgba(255, 255, 255, 0.06); text-align: center; font-size: 11px; color: #64748b;">
      Dispatched to: <strong>{target_email}</strong> • RealEstate Hub VIP Concierge
    </div>
  </div>
</body>
</html>"""

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "umersahi5p@gmail.com")
    smtp_pass = os.getenv("SMTP_PASS", "yswo idoh wmvl mzeb")
    smtp_delivered = False
    smtp_error = None

    if smtp_host and smtp_user and smtp_pass:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"RealEstate Hub Concierge <{smtp_user}>"
            msg["To"] = target_email
            msg["Reply-To"] = email
            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=6.0) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [target_email], msg.as_string())
            smtp_delivered = True
        except Exception as e:
            smtp_error = str(e)

    record = {
        "email_id": email_id,
        "type": "contact_inquiry",
        "name": name,
        "email": email,
        "phone": phone,
        "inquiry_type": inquiry_type,
        "city": city,
        "budget": budget,
        "message": message,
        "recipient": target_email,
        "sent_at": sent_at,
        "smtp_delivered": smtp_delivered,
        "smtp_error": smtp_error,
    }

    try:
        (EMAIL_DIR / f"{email_id}.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        (EMAIL_DIR / f"{email_id}.html").write_text(html_content, encoding="utf-8")
    except Exception:
        pass

    return record

