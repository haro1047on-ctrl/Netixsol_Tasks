"""City Care Clinics - Doctor Oversight & Human-in-the-Loop Dashboard.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 4: Orchestration, Memory & Human-in-the-Loop
Interactive Web Dashboard for Attending Physicians:
1. Reviews pending AI clinical drafts (Lab results, Prescriptions, Low-confidence triage)
2. One-click Approve, Edit & Approve, or Reject & Escalate actions
3. Longitudinal patient chart inspector & Pre-Visit SOAP clinical brief preview
4. Audit trail of all clinical decisions
"""
from __future__ import annotations

import os
import sys
import streamlit as st

# Windows console UTF-8 safety
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
WEEK9_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
DAY5_SRC = os.path.join(WEEK9_DIR, "Day5", "src")
for p in [SRC_DIR, DAY2_SRC, DAY5_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from hitl_manager import HITLManager
from patient_memory import MemoryStore


def main():
    st.set_page_config(
        page_title="City Care Clinics — Doctor Oversight Portal",
        page_icon="🩺",
        layout="wide"
    )

    st.title("🩺 City Care Clinics — Physician Oversight & HITL Portal")
    st.caption("Human-in-the-Loop Clinical Verification & Pre-Encounter Intelligence")

    hitl_mgr = HITLManager()
    memory_store = MemoryStore()

    # Sidebar: Active Physician Profile
    with st.sidebar:
        st.header("👨‍⚕️ Attending Physician")
        doctor_name = st.selectbox(
            "Logged In As:",
            [
                "Dr. Tariq Mahmood (General Medicine)",
                "Dr. Bilal Aslam (Paediatrics)",
                "Dr. Ayesha Malik (CMO)",
                "Dr. Fatima Zahra (Gynaecology)",
                "Dr. Qasim Raza (ENT)"
            ]
        )
        st.info("Medical Safety Invariant:\nNo AI-generated lab interpretation, prescription order, or low-confidence triage may reach a patient without explicit physician authorization.")
        st.divider()
        if st.button("🔄 Refresh Pending Queue"):
            st.rerun()

    # Main Tabs
    tab_pending, tab_history, tab_patients = st.tabs([
        "⚠️ Pending Approvals Queue",
        "📋 Decision Audit History",
        "👤 Patient Longitudinal Memory"
    ])

    # -------------------------------------------------------------------------
    # TAB 1: PENDING APPROVALS QUEUE
    # -------------------------------------------------------------------------
    with tab_pending:
        pending_list = hitl_mgr.list_pending()
        st.subheader(f"Items Awaiting Physician Review ({len(pending_list)})")

        if not pending_list:
            st.success("✅ All pending clinical messages have been reviewed. Zero backlog.")
        else:
            for item in pending_list:
                with st.expander(f"🔴 [{item.category}] {item.patient_name} ({item.patient_id}) — {item.reason_for_interrupt}", expanded=True):
                    col_info, col_actions = st.columns([2, 1])

                    with col_info:
                        st.markdown(f"**Request ID:** `{item.request_id}` | **Thread:** `{item.thread_id}`")
                        st.markdown(f"**Interrupt Reason:** *{item.reason_for_interrupt}*")
                        st.markdown("**Proposed AI Draft Message (For Patient):**")
                        st.code(item.draft_message_for_patient, language="text")

                        if item.clinical_context:
                            st.caption(f"Clinical Context: {item.clinical_context}")

                    with col_actions:
                        st.write("### Clinical Action")

                        # Option A: Approve As Is
                        if st.button("✅ Approve As Is", key=f"app_{item.request_id}"):
                            hitl_mgr.approve_request(item.request_id, doctor_name=doctor_name)
                            st.success("Draft approved! Dispatching to patient.")
                            st.rerun()

                        # Option B: Edit and Approve
                        with st.popover("✏️ Edit Message & Approve"):
                            st.write("Modify the message before patient dispatch:")
                            edited_text = st.text_area(
                                "Physician Edit:",
                                value=item.draft_message_for_patient,
                                key=f"edit_txt_{item.request_id}"
                            )
                            notes = st.text_input("Internal Clinical Note:", key=f"notes_{item.request_id}")
                            if st.button("Submit Modified Message", key=f"submit_edit_{item.request_id}"):
                                hitl_mgr.edit_and_approve(
                                    item.request_id,
                                    doctor_name=doctor_name,
                                    edited_message=edited_text,
                                    clinical_notes=notes
                                )
                                st.success("Modified message approved and logged!")
                                st.rerun()

                        # Option C: Reject & Route to Clinic
                        with st.popover("🚫 Reject & Block"):
                            reject_reason = st.text_input(
                                "Rejection Rationale:",
                                value="Patient must present for immediate physical examination.",
                                key=f"rej_txt_{item.request_id}"
                            )
                            if st.button("Confirm Rejection", key=f"btn_rej_{item.request_id}"):
                                hitl_mgr.reject_request(
                                    item.request_id,
                                    doctor_name=doctor_name,
                                    rejection_reason=reject_reason
                                )
                                st.warning("Automated draft blocked. Patient routed for in-person review.")
                                st.rerun()

    # -------------------------------------------------------------------------
    # TAB 2: DECISION AUDIT HISTORY
    # -------------------------------------------------------------------------
    with tab_history:
        st.subheader("Completed Physician Review Audit Trail")
        all_requests = list(hitl_mgr._requests.values())
        reviewed = [r for r in all_requests if r.status != "PENDING"]

        if not reviewed:
            st.info("No reviewed items yet.")
        else:
            for r in reversed(reviewed):
                status_color = "🟢" if r.status == "APPROVED" else ("🟡" if r.status == "EDITED" else "🔴")
                st.markdown(
                    f"{status_color} **{r.patient_name}** | Status: **{r.status}** | Reviewer: **{r.reviewing_doctor}** | Date: `{r.reviewed_at}`\n\n"
                    f"- Category: `{r.category}`\n"
                    f"- Original Draft: *{r.draft_message_for_patient[:100]}...*\n"
                    + (f"- Doctor Edited: **{r.doctor_edited_message}**\n" if r.doctor_edited_message else "")
                    + (f"- Doctor Notes: *{r.doctor_clinical_notes}*\n" if r.doctor_clinical_notes else "")
                )
                st.divider()

    # -------------------------------------------------------------------------
    # TAB 3: PATIENT LONGITUDINAL MEMORY
    # -------------------------------------------------------------------------
    with tab_patients:
        st.subheader("Longitudinal Privacy-Preserving Patient Profiles")
        profiles = list(memory_store._cache.values())
        for prof in profiles:
            with st.expander(f"👤 {prof.patient_name} ({prof.patient_id}) — Preferred Doctor: {prof.preferred_doctor_name or 'None'}"):
                st.write(f"**Preferred Branch:** {prof.preferred_branch}")
                st.write(f"**Preferred Language:** {prof.preferred_language}")
                st.write(f"**Known Allergies:** {', '.join(prof.known_allergies) or 'NKDA'}")
                st.write(f"**Chronic Conditions:** {', '.join(prof.chronic_conditions) or 'None'}")
                st.write(f"**Special Accommodations:** {prof.special_notes or 'None'}")

                st.markdown("#### Past Clinic Encounters (Last 3):")
                for v in prof.recent_visits:
                    st.markdown(f"- **{v.visit_date}** with {v.doctor_name} ({v.specialty}): *{v.chief_complaint}* &rarr; {v.outcome_summary}")


if __name__ == "__main__":
    main()
