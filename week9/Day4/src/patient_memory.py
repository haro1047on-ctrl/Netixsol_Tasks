"""City Care Clinics - Patient Memory Management System.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 4: Orchestration, Memory & Human-in-the-Loop
Implements:
1. Short-Term Conversation Memory (database-backed thread & message buffer across restarts)
2. Long-Term Patient Memory Across Visits (Preferences, Past Encounters, Preferred Doctor & Branch)
3. Privacy Guardrails (Strict minimization: stores only clinical continuity keys, no financial/PII leakage)
4. Returning Patient Recognition & Culturally Empathetic UrduLish Welcoming
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Windows console UTF-8 safety
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
WEEK9_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
for p in [SRC_DIR, DAY2_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from db_models import (
    AppointmentModel,
    ConversationMessageModel,
    ConversationThreadModel,
    PatientModel,
    PatientPreferenceModel,
    PractitionerModel,
    VisitModel,
    get_db_engine,
    init_db,
)


class VisitMemoryItem(BaseModel):
    """Summarized record of a past clinic encounter."""
    visit_date: str
    doctor_name: str
    specialty: str
    branch_name: str
    chief_complaint: str
    outcome_summary: str


class PatientLongTermProfile(BaseModel):
    """Privacy-preserving longitudinal profile of a returning patient."""
    patient_id: str
    patient_name: str
    preferred_language: str = Field(default="UrduLish", description="UrduLish, Urdu, Punjabi, English")
    preferred_doctor_id: Optional[str] = None
    preferred_doctor_name: Optional[str] = None
    preferred_branch: Optional[str] = None
    known_allergies: List[str] = Field(default_factory=list)
    chronic_conditions: List[str] = Field(default_factory=list)
    recent_visits: List[VisitMemoryItem] = Field(default_factory=list)
    special_notes: Optional[str] = None
    last_updated: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# CONVERSATION STORE (SHORT-TERM THREAD MEMORY IN DATABASE)
# =============================================================================

class ConversationStore:
    """Database-backed short-term dialogue storage surviving server restarts."""

    def __init__(self, db_engine=None):
        self.engine = db_engine or get_db_engine()
        self.session_factory = init_db(self.engine)

    def get_or_create_thread(self, thread_id: str, patient_id: Optional[str] = None, channel: str = "web_chat") -> str:
        """Ensures conversation thread exists in persistent storage."""
        session = self.session_factory()
        try:
            thread = session.query(ConversationThreadModel).filter_by(id=thread_id).first()
            if not thread:
                thread = ConversationThreadModel(
                    id=thread_id,
                    patient_id=patient_id,
                    channel=channel,
                    is_active=True,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(thread)
                session.commit()
            return thread_id
        finally:
            session.close()

    def append_message(
        self,
        thread_id: str,
        sender_role: str,
        content: str,
        intent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Appends a turn to the persistent conversation transcript."""
        self.get_or_create_thread(thread_id)
        session = self.session_factory()
        try:
            msg_id = f"MSG_{uuid.uuid4().hex[:12]}"
            msg = ConversationMessageModel(
                id=msg_id,
                thread_id=thread_id,
                sender_role=sender_role,
                content=content,
                intent=intent,
                metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
                timestamp_utc=datetime.now(timezone.utc)
            )
            session.add(msg)
            # Update thread updated_at
            thread = session.query(ConversationThreadModel).filter_by(id=thread_id).first()
            if thread:
                thread.updated_at = datetime.now(timezone.utc)
            session.commit()
            return msg_id
        finally:
            session.close()

    def get_thread_history(self, thread_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieves chronological dialogue turns for session restoration."""
        session = self.session_factory()
        try:
            msgs = session.query(ConversationMessageModel).filter_by(thread_id=thread_id).order_by(
                ConversationMessageModel.timestamp_utc.asc()
            ).limit(limit).all()

            return [
                {
                    "message_id": m.id,
                    "role": m.sender_role,
                    "content": m.content,
                    "intent": m.intent,
                    "timestamp": m.timestamp_utc.isoformat() if m.timestamp_utc else None
                }
                for m in msgs
            ]
        finally:
            session.close()


# =============================================================================
# MEMORY STORE (LONG-TERM PREFERENCES & ENCOUNTER MEMORY)
# =============================================================================

class MemoryStore:
    """Persistent storage engine for patient longitudinal memory backed by database."""

    def __init__(self, storage_path: Optional[str] = None, db_engine=None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_path = os.path.join(base_dir, "data", "patient_long_term_memory.json")
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self._cache: Dict[str, PatientLongTermProfile] = {}
        self.engine = db_engine or get_db_engine()
        self.session_factory = init_db(self.engine)
        self._load()

    def _load(self) -> None:
        """Loads serialized long-term profiles into memory from JSON and seeds default if empty."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    for pid, pdata in raw_data.items():
                        self._cache[pid] = PatientLongTermProfile(**pdata)
            except Exception:
                self._cache = {}
        else:
            self._seed_default_memories()

    def _save(self) -> None:
        """Persists cache to disk."""
        serialized = {pid: prof.model_dump() for pid, prof in self._cache.items()}
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(serialized, f, indent=2, ensure_ascii=False)

    def _seed_default_memories(self) -> None:
        """Seeds realistic historical patient memories for testing returning patient flows."""
        seed_profiles = [
            PatientLongTermProfile(
                patient_id="PT_0001",
                patient_name="Ali Khan",
                preferred_language="UrduLish",
                preferred_doctor_id="DOC_001",
                preferred_doctor_name="Dr. Tariq Mahmood",
                preferred_branch="City Care Clinics — DHA Branch",
                known_allergies=["Sulfa Drugs"],
                chronic_conditions=["Mild Seasonal Asthma"],
                recent_visits=[
                    VisitMemoryItem(
                        visit_date="2026-08-14",
                        doctor_name="Dr. Tariq Mahmood",
                        specialty="General Medicine",
                        branch_name="City Care Clinics — DHA Branch",
                        chief_complaint="Chest congestion and dry cough",
                        outcome_summary="Prescribed inhaler and oral bronchodilator; symptoms resolved."
                    )
                ],
                special_notes="Prefers evening slots after 6:00 PM."
            ),
            PatientLongTermProfile(
                patient_id="PT_0002",
                patient_name="Ahmed Raza",
                preferred_language="UrduLish",
                preferred_doctor_id="DOC_008",
                preferred_doctor_name="Dr. Bilal Aslam",
                preferred_branch="City Care Clinics — DHA Branch",
                known_allergies=[],
                chronic_conditions=["Pediatric recurrent otitis"],
                recent_visits=[
                    VisitMemoryItem(
                        visit_date="2026-09-02",
                        doctor_name="Dr. Bilal Aslam",
                        specialty="Paediatrics",
                        branch_name="City Care Clinics — DHA Branch",
                        chief_complaint="Bachay ko kaan mein dard aur bukhar",
                        outcome_summary="Treated for acute otitis media; follow-up showed clear eardrum."
                    )
                ],
                special_notes="Parent brings child (age 5); prefers Dr. Bilal for gentle care."
            ),
            PatientLongTermProfile(
                patient_id="PT_0005",
                patient_name="Shoaib Bhatti",
                preferred_language="UrduLish",
                preferred_doctor_id="DOC_001",
                preferred_doctor_name="Dr. Tariq Mahmood",
                preferred_branch="City Care Clinics — Gulberg Branch",
                known_allergies=[],
                chronic_conditions=["Ischemic Heart Disease", "Hypertension"],
                recent_visits=[
                    VisitMemoryItem(
                        visit_date="2026-07-20",
                        doctor_name="Dr. Tariq Mahmood",
                        specialty="General Medicine",
                        branch_name="City Care Clinics — Gulberg Branch",
                        chief_complaint="Routine cardiovascular checkup and BP review",
                        outcome_summary="BP stable at 130/84; lipid profile ordered."
                    )
                ],
                special_notes="Requires ramp access / ground floor consultation."
            )
        ]
        for sp in seed_profiles:
            self._cache[sp.patient_id] = sp
        self._save()

    def get_patient_memory(self, patient_id: str) -> Optional[PatientLongTermProfile]:
        """Retrieves privacy-sanitized patient profile from DB or cache."""
        # 1. Check local cache first
        if patient_id in self._cache:
            return self._cache[patient_id]

        # 2. Check Database
        session = self.session_factory()
        try:
            pt = session.query(PatientModel).filter_by(id=patient_id).first()
            if not pt:
                return None

            pref = session.query(PatientPreferenceModel).filter_by(patient_id=patient_id).first()
            preferred_doc_name = None
            preferred_branch_name = None

            if pref:
                if pref.preferred_doctor:
                    preferred_doc_name = pref.preferred_doctor.name
                if pref.preferred_branch:
                    preferred_branch_name = pref.preferred_branch.name

            # Query recent appointments as visit memory
            recent_appts = session.query(AppointmentModel).filter_by(
                patient_id=patient_id
            ).order_by(AppointmentModel.created_at.desc()).limit(3).all()

            recent_visits = []
            for a in recent_appts:
                recent_visits.append(VisitMemoryItem(
                    visit_date=a.slot_datetime.split(" ")[0] if " " in a.slot_datetime else a.slot_datetime,
                    doctor_name=a.practitioner.name if a.practitioner else "Consulting Doctor",
                    specialty=a.specialty,
                    branch_name=a.branch.name if a.branch else "Clinic",
                    chief_complaint=a.chief_complaint or "Consultation",
                    outcome_summary=f"Encounter recorded ({a.status})"
                ))

            profile = PatientLongTermProfile(
                patient_id=pt.id,
                patient_name=pt.full_name,
                preferred_language=pref.preferred_language if pref else "UrduLish",
                preferred_doctor_id=pref.preferred_doctor_id if pref else None,
                preferred_doctor_name=preferred_doc_name,
                preferred_branch=preferred_branch_name,
                known_allergies=[a.substance for a in pt.allergies],
                chronic_conditions=[c.display_name for c in pt.conditions],
                recent_visits=recent_visits,
                special_notes=pref.special_notes if pref else None
            )
            self._cache[patient_id] = profile
            return profile
        finally:
            session.close()

    def update_patient_memory(
        self,
        patient_id: str,
        patient_name: str,
        preferred_doctor_id: Optional[str] = None,
        preferred_doctor_name: Optional[str] = None,
        preferred_branch: Optional[str] = None,
        new_visit: Optional[VisitMemoryItem] = None,
        allergies: Optional[List[str]] = None
    ) -> PatientLongTermProfile:
        """Updates or creates a patient long-term memory record across cache and database."""
        profile = self._cache.get(patient_id)
        if profile is None:
            profile = PatientLongTermProfile(
                patient_id=patient_id,
                patient_name=patient_name
            )

        if preferred_doctor_id:
            profile.preferred_doctor_id = preferred_doctor_id
        if preferred_doctor_name:
            profile.preferred_doctor_name = preferred_doctor_name
        if preferred_branch:
            profile.preferred_branch = preferred_branch
        if allergies:
            profile.known_allergies = list(set(profile.known_allergies + allergies))
        if new_visit:
            # Keep at most last 3 visits for strict privacy and context efficiency
            profile.recent_visits = [new_visit] + profile.recent_visits[:2]

        profile.last_updated = datetime.now(timezone.utc).isoformat()
        self._cache[patient_id] = profile
        self._save()

        # Sync with database
        session = self.session_factory()
        try:
            pref = session.query(PatientPreferenceModel).filter_by(patient_id=patient_id).first()
            if not pref:
                pref = PatientPreferenceModel(
                    id=f"PREF_{uuid.uuid4().hex[:8].upper()}",
                    patient_id=patient_id
                )
                session.add(pref)
            if preferred_doctor_id:
                pref.preferred_doctor_id = preferred_doctor_id
            pref.last_updated = datetime.now(timezone.utc)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

        return profile


class MemoryManager:
    """Coordinates session-level short-term buffer and long-term memory retrieval."""

    def __init__(self, memory_store: Optional[MemoryStore] = None, conversation_store: Optional[ConversationStore] = None):
        self.store = memory_store or MemoryStore()
        self.conversation_store = conversation_store or ConversationStore()

    def initialize_session(self, patient_id: Optional[str], patient_name: Optional[str] = None) -> Dict[str, Any]:
        """Initializes memory for an encounter session."""
        if not patient_id:
            return {
                "is_returning_patient": False,
                "profile": None,
                "welcome_greeting": "Assalam-o-Alaikum! City Care Clinics mein khush-aamdeed. Main Sitara hoon, clinic ki AI Assistant. Aaj main aapki kya madad kar sakti hoon?"
            }

        profile = self.store.get_patient_memory(patient_id)
        if not profile:
            name_display = patient_name or "Janab"
            return {
                "is_returning_patient": False,
                "profile": None,
                "welcome_greeting": f"Assalam-o-Alaikum {name_display}! City Care Clinics mein khush-aamdeed. Main Sitara hoon. Aaj main aapki kya madad kar sakti hoon?"
            }

        # Returning patient recognized!
        doctor_mention = profile.preferred_doctor_name or "apne specialist doctor"
        branch_mention = profile.preferred_branch or "clinic"

        # Requirement Example:
        # "Assalam-o-Alaikum Ahmed sahib! Pichli dafa aap Dr. Bilal ko dikhaye thay. Kya isi doctor ke saath appointment chahiye?"
        greeting = (
            f"Assalam-o-Alaikum {profile.patient_name} sahib! "
            f"Pichli dafa aap {doctor_mention} ko dikhaye thay. "
            f"Kya isi doctor ke saath appointment chahiye, ya kisi nayi takleef ke baray mein baat karni hai?"
        )

        return {
            "is_returning_patient": True,
            "profile": profile.model_dump(),
            "welcome_greeting": greeting
        }
