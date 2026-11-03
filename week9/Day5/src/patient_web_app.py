"""City Care Clinics - Patient Conversational Web Portal.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 5: Evaluation, Red-Teaming, Deployment & Client Handover
Interactive Streamlit Patient Experience:
1. Natural UrduLish dialogue with Sitara (Intake & Triage Agent)
2. Live Urgency Stratification (Emergency alert banner, Urgent same-day, Routine outpatient)
3. Verified Doctor Booking & Digital Token Reservation Display
4. Care Continuity & Longitudinal Memory Lookup (CNIC / Phone)
"""
from __future__ import annotations

import os
import sys
import uuid
from typing import Optional
import streamlit as st

# Windows console UTF-8 safety
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
WEEK9_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
DAY1_SRC = os.path.join(WEEK9_DIR, "Day1", "src")
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
DAY3_SRC = os.path.join(WEEK9_DIR, "Day3", "src")
DAY4_SRC = os.path.join(WEEK9_DIR, "Day4", "src")
for p in [SRC_DIR, DAY4_SRC, DAY3_SRC, DAY2_SRC, DAY1_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from supervisor_graph import ClinicSupervisorOrchestrator
from patient_service import get_patient_service
from services.auth_service import get_auth_service


def main():
    st.set_page_config(
        page_title="City Care Clinics — Patient Portal",
        page_icon="🏥",
        layout="centered"
    )

    st.title("🏥 City Care Clinics — Sehat & Appointment Portal")
    st.caption("Lahore & Islamabad Outpatient Clinics Network • UrduLish AI Assistant")

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"WEB_SESSION_{uuid.uuid4().hex[:8]}"
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Assalam-o-Alaikum! City Care Clinics mein khush-aamdeed. Main Sitara hoon, clinic ki AI Assistant. Aaj main aapki kya madad kar sakti hoon? Aap bukhar, dard, ya appointment ke baray mein pooch sakte hain."
            }
        ]
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = ClinicSupervisorOrchestrator()
    if "patient_id" not in st.session_state:
        st.session_state.patient_id = None
    if "patient_name" not in st.session_state:
        st.session_state.patient_name = "Valued Patient"
    if "patient_phone" not in st.session_state:
        st.session_state.patient_phone = None
    if "patient_email" not in st.session_state:
        st.session_state.patient_email = os.getenv("TEST_EMAIL_RECIPIENT", "")

    patient_svc = get_patient_service()
    auth_svc = get_auth_service()

    # Sidebar: Real Patient Identity & Registration
    with st.sidebar:
        st.header("👤 Patient Identity")
        mode = st.radio("Access Mode:", ["Returning Patient (Lookup)", "Register New Patient", "Guest Mode"])

        if mode == "Returning Patient (Lookup)":
            lookup_key = st.text_input("Enter Phone, CNIC, or Patient ID:", placeholder="e.g. 0300-1234567 or PT_0001")
            if st.button("🔍 Find My Chart"):
                if lookup_key:
                    chart = patient_svc.get_patient_chart(lookup_key.strip())
                    if chart and chart.get("status") != "NOT_FOUND":
                        demo = chart.get("demographics", {})
                        st.session_state.patient_id = demo.get("patient_id")
                        st.session_state.patient_name = demo.get("name")
                        st.session_state.patient_phone = demo.get("phone")
                        if demo.get("email"):
                            st.session_state.patient_email = demo.get("email")
                        st.success(f"Welcome back, **{demo.get('name')}**!")
                    else:
                        st.warning("Patient not found. You can register as a new patient below.")
                else:
                    st.info("Please enter your Phone or CNIC.")

        elif mode == "Register New Patient":
            with st.form("new_patient_reg"):
                reg_name = st.text_input("Full Name *", placeholder="e.g. Fatima Ali")
                reg_phone = st.text_input("Phone Number *", placeholder="0300-1234567")
                reg_email = st.text_input("Email (for appointment receipt)", placeholder="e.g. patient@example.com")
                reg_cnic = st.text_input("CNIC (Optional)", placeholder="35202-1234567-1")
                reg_age = st.number_input("Age *", min_value=1, max_value=120, value=25)
                reg_gender = st.selectbox("Gender *", ["Female", "Male", "Other"])
                reg_city = st.selectbox("City *", ["Lahore", "Islamabad"])
                submit_reg = st.form_submit_button("Register Patient")

                if submit_reg and reg_name and reg_phone:
                    try:
                        res = patient_svc.register_patient({
                            "full_name": reg_name,
                            "phone": reg_phone,
                            "email": reg_email or None,
                            "cnic": reg_cnic or None,
                            "age": int(reg_age),
                            "gender": reg_gender,
                            "city": reg_city
                        })
                        st.session_state.patient_id = res["patient_id"]
                        st.session_state.patient_name = reg_name
                        st.session_state.patient_phone = reg_phone
                        if reg_email:
                            st.session_state.patient_email = reg_email.strip()
                        st.success(f"Registered! Your Patient ID is `{res['patient_id']}`")
                    except Exception as e:
                        st.error(f"Registration error: {e}")

        else:
            # Guest Mode
            st.session_state.patient_id = None
            st.session_state.patient_name = "Guest Patient"

        st.info(f"Active Identity: **{st.session_state.patient_name}** (`{st.session_state.patient_id or 'GUEST'}`)")

        # Notification Email
        st.markdown("#### 📧 Confirmation Email")
        email_inp = st.text_input(
            "Send appointment receipt to:",
            value=st.session_state.patient_email,
            placeholder="e.g. name@example.com",
            help="Your appointment token and calendar details will be emailed here."
        )
        if email_inp:
            st.session_state.patient_email = email_inp.strip()

        st.divider()
        st.markdown("### 🚨 Emergency Contacts")
        st.error("**Rescue 1122** — 24/7 Ambulance\n\nLahore: Services / Mayo ER\nIslamabad: PIMS / Shifa ER")

        if st.button("🔄 Clear Chat & Reset Session"):
            st.session_state.messages = []
            st.session_state.thread_id = f"WEB_SESSION_{uuid.hex[:8] if hasattr(uuid, 'hex') else uuid.uuid4().hex[:8]}"
            st.rerun()

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # User Input
    if user_prompt := st.chat_input("Apni takleef ya appointment ke baray mein yahan likhein..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.write(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Sitara soch rahi hai..."):
                final_state = st.session_state.orchestrator.run_turn(
                    thread_id=st.session_state.thread_id,
                    user_message=user_prompt,
                    patient_id=st.session_state.patient_id,
                    patient_name=st.session_state.patient_name,
                    patient_phone=st.session_state.patient_phone,
                    patient_email=st.session_state.patient_email,
                    channel="web_chat"
                )
                assistant_reply = final_state.get("final_patient_response", "Shukriya! Aapki maloomat darj kar li gayi hain.")
                st.write(assistant_reply)
                st.session_state.messages.append({"role": "assistant", "content": assistant_reply})

                # Visual Feedback Banners for Clinical Decisions
                if final_state.get("is_emergency"):
                    st.error("🚨 **EMERGENCY MEDICAL PROTOCOL ACTIVATED** — Barah-e-karam foran Rescue 1122 par call karein ya qareebi Emergency Room tashreef le jayein!")
                elif final_state.get("urgency_tier") == "URGENT":
                    st.warning("⚠️ **Urgent Assessment:** Same-day clinical consultation recommended.")
                elif final_state.get("urgency_tier") == "ROUTINE":
                    st.info("ℹ️ **Routine Assessment:** Standard outpatient consultation scheduled.")

                booking = final_state.get("appointment_booking")
                if booking and booking.get("status") == "CONFIRMED":
                    st.success(
                        f"🎟️ **Appointment Confirmed!**\n\n"
                        f"- **Doctor:** {booking.get('doctor_name')} ({booking.get('specialty')})\n"
                        f"- **Slot:** {booking.get('slot_datetime')}\n"
                        f"- **Token Number:** #{booking.get('token_number')}\n"
                        f"- **Branch:** {booking.get('branch')}\n"
                        f"- **Fee:** PKR {booking.get('fee_pkr'):,}"
                    )
                    if st.session_state.patient_email:
                        st.info(f"📧 Appointment confirmation email sent to **{st.session_state.patient_email}**.")

                if final_state.get("hitl_required") and final_state.get("hitl_status") == "PENDING":
                    st.warning("🩺 **Physician Review Pending:** Aapka clinical mashwara attending doctor ke review ke liye submit kar diya gaya hai.")


if __name__ == "__main__":
    main()
