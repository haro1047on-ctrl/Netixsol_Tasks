"""City Care Clinics - Human-in-the-Loop (HITL) Doctor Oversight Manager.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 4: Orchestration, Memory & Human-in-the-Loop
Enforces strict medical guardrails:
AI never sends medical guidance to patients without physician sign-off.
Triggers mandatory doctor review interrupts for:
1. Any laboratory diagnostic explanation sent to a patient
2. Any prescription-related dosage or medication instruction
3. Any clinical triage decision with low confidence (< 0.85)

Persists pending and reviewed approval requests in DoctorApprovalRequestModel database.
Supports physician actions:
- APPROVE: Dispatches draft message without alteration.
- EDIT & APPROVE: Physician modifies the clinical text before dispatch.
- REJECT: Blocks outbound dispatch and routes patient for urgent in-person checkup.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

# Setup paths
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
WEEK9_DIR = os.path.dirname(os.path.dirname(SRC_DIR))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
for p in [SRC_DIR, DAY2_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from db_models import DoctorApprovalRequestModel, init_db

logger = logging.getLogger("citycare.hitl")


class HITLApprovalRequest(BaseModel):
    """Pending doctor review item."""
    request_id: str = Field(default_factory=lambda: f"HITL_{uuid.uuid4().hex[:8].upper()}")
    thread_id: str
    patient_id: str
    patient_name: str
    category: str = Field(description="LAB_RESULT_EXPLANATION, PRESCRIPTION_MESSAGE, or LOW_CONFIDENCE_TRIAGE")
    reason_for_interrupt: str
    draft_message_for_patient: str
    clinical_context: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="PENDING", description="PENDING, APPROVED, EDITED, or REJECTED")
    reviewing_doctor: Optional[str] = None
    doctor_edited_message: Optional[str] = None
    doctor_clinical_notes: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reviewed_at: Optional[str] = None


class HITLManager:
    """Production Human-in-the-Loop coordinator backed by PostgreSQL/SQLite DoctorApprovalRequestModel."""

    def __init__(self, storage_path: Optional[str] = None, session_factory=None):
        if storage_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_path = os.path.join(base_dir, "data", "hitl_pending_approvals.json")
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        self.session_factory = session_factory or init_db()
        self._requests: Dict[str, HITLApprovalRequest] = {}
        self._load_from_db()

    def _load_from_db(self) -> None:
        """Hydrates in-memory map from DoctorApprovalRequestModel database table."""
        session = self.session_factory()
        try:
            records = session.query(DoctorApprovalRequestModel).all()
            for r in records:
                ctx = {}
                if r.clinical_context_json:
                    try:
                        ctx = json.loads(r.clinical_context_json)
                    except Exception:
                        pass
                patient_name = r.patient.full_name if r.patient else "Valued Patient"
                req = HITLApprovalRequest(
                    request_id=r.id,
                    thread_id=r.thread_id or "",
                    patient_id=r.patient_id,
                    patient_name=patient_name,
                    category=r.category,
                    reason_for_interrupt=r.reason_for_interrupt,
                    draft_message_for_patient=r.draft_message_for_patient,
                    clinical_context=ctx,
                    status=r.status,
                    reviewing_doctor=r.reviewing_doctor_name,
                    doctor_edited_message=r.doctor_edited_message,
                    doctor_clinical_notes=r.doctor_clinical_notes,
                    created_at=r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat(),
                    reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None
                )
                self._requests[req.request_id] = req
        except Exception as e:
            logger.warning(f"Failed to load HITL approvals from DB, falling back to JSON file: {e}")
            self._load_from_json()
        finally:
            session.close()

    def _load_from_json(self) -> None:
        """Loads serialized approvals from file backup if database unpopulated."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        req = HITLApprovalRequest(**item)
                        self._requests[req.request_id] = req
            except Exception:
                self._requests = {}

    def _sync_to_json(self) -> None:
        """Persists backup JSON file."""
        try:
            data = [r.model_dump() for r in self._requests.values()]
            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"JSON backup write skipped: {e}")

    def evaluate_hitl_trigger(
        self,
        triage_confidence: Optional[float] = None,
        is_explaining_lab: bool = False,
        is_prescribing_meds: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """Evaluates whether an outgoing action requires mandatory physician sign-off."""
        if is_explaining_lab:
            return True, "LAB_RESULT_EXPLANATION"
        if is_prescribing_meds:
            return True, "PRESCRIPTION_MESSAGE"
        if triage_confidence is not None and triage_confidence < 0.85:
            return True, "LOW_CONFIDENCE_TRIAGE"
        return False, None

    def create_request(
        self,
        thread_id: str,
        patient_id: str,
        patient_name: str,
        category: str,
        reason: str,
        draft_message: str,
        clinical_context: Optional[Dict[str, Any]] = None
    ) -> HITLApprovalRequest:
        """Queues a new pending approval for attending physician review persistently."""
        req = HITLApprovalRequest(
            thread_id=thread_id,
            patient_id=patient_id,
            patient_name=patient_name,
            category=category,
            reason_for_interrupt=reason,
            draft_message_for_patient=draft_message,
            clinical_context=clinical_context or {}
        )
        self._requests[req.request_id] = req

        # Persist to DoctorApprovalRequestModel
        session = self.session_factory()
        try:
            db_rec = DoctorApprovalRequestModel(
                id=req.request_id,
                thread_id=thread_id,
                patient_id=patient_id,
                category=category,
                reason_for_interrupt=reason,
                draft_message_for_patient=draft_message,
                clinical_context_json=json.dumps(clinical_context or {}, ensure_ascii=False),
                status="PENDING",
                created_at=datetime.now(timezone.utc)
            )
            session.add(db_rec)
            session.commit()
        except Exception as e:
            logger.error(f"Error persisting DoctorApprovalRequestModel: {e}")
            session.rollback()
        finally:
            session.close()

        self._sync_to_json()
        return req

    def get_request(self, request_id: str) -> Optional[HITLApprovalRequest]:
        """Fetches a specific request by ID."""
        if request_id in self._requests:
            return self._requests[request_id]

        # Query DB directly
        session = self.session_factory()
        try:
            db_rec = session.query(DoctorApprovalRequestModel).filter_by(id=request_id).first()
            if db_rec:
                ctx = {}
                if db_rec.clinical_context_json:
                    try:
                        ctx = json.loads(db_rec.clinical_context_json)
                    except Exception:
                        pass
                p_name = db_rec.patient.full_name if db_rec.patient else "Valued Patient"
                req = HITLApprovalRequest(
                    request_id=db_rec.id,
                    thread_id=db_rec.thread_id or "",
                    patient_id=db_rec.patient_id,
                    patient_name=p_name,
                    category=db_rec.category,
                    reason_for_interrupt=db_rec.reason_for_interrupt,
                    draft_message_for_patient=db_rec.draft_message_for_patient,
                    clinical_context=ctx,
                    status=db_rec.status,
                    reviewing_doctor=db_rec.reviewing_doctor_name,
                    doctor_edited_message=db_rec.doctor_edited_message,
                    doctor_clinical_notes=db_rec.doctor_clinical_notes,
                    created_at=db_rec.created_at.isoformat() if db_rec.created_at else datetime.now(timezone.utc).isoformat(),
                    reviewed_at=db_rec.reviewed_at.isoformat() if db_rec.reviewed_at else None
                )
                self._requests[req.request_id] = req
                return req
            return None
        finally:
            session.close()

    def list_pending(self) -> List[HITLApprovalRequest]:
        """Lists all items awaiting doctor review from persistent DB."""
        session = self.session_factory()
        try:
            db_pending = session.query(DoctorApprovalRequestModel).filter_by(status="PENDING").order_by(DoctorApprovalRequestModel.created_at.desc()).all()
            results = []
            for r in db_pending:
                ctx = {}
                if r.clinical_context_json:
                    try:
                        ctx = json.loads(r.clinical_context_json)
                    except Exception:
                        pass
                p_name = r.patient.full_name if r.patient else "Valued Patient"
                results.append(HITLApprovalRequest(
                    request_id=r.id,
                    thread_id=r.thread_id or "",
                    patient_id=r.patient_id,
                    patient_name=p_name,
                    category=r.category,
                    reason_for_interrupt=r.reason_for_interrupt,
                    draft_message_for_patient=r.draft_message_for_patient,
                    clinical_context=ctx,
                    status=r.status,
                    reviewing_doctor=r.reviewing_doctor_name,
                    doctor_edited_message=r.doctor_edited_message,
                    doctor_clinical_notes=r.doctor_clinical_notes,
                    created_at=r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat(),
                    reviewed_at=r.reviewed_at.isoformat() if r.reviewed_at else None
                ))
            return results
        except Exception:
            return [r for r in self._requests.values() if r.status == "PENDING"]
        finally:
            session.close()

    def approve_request(self, request_id: str, doctor_name: str = "Dr. Tariq Mahmood") -> HITLApprovalRequest:
        """Doctor approves the draft message without modification."""
        req = self.get_request(request_id)
        if not req:
            raise ValueError(f"Approval request '{request_id}' not found.")
        now_utc = datetime.now(timezone.utc)
        req.status = "APPROVED"
        req.reviewing_doctor = doctor_name
        req.reviewed_at = now_utc.isoformat()

        session = self.session_factory()
        try:
            rec = session.query(DoctorApprovalRequestModel).filter_by(id=request_id).first()
            if rec:
                rec.status = "APPROVED"
                rec.reviewing_doctor_name = doctor_name
                rec.reviewed_at = now_utc
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update approval in DB: {e}")
            session.rollback()
        finally:
            session.close()

        self._sync_to_json()
        return req

    def edit_and_approve(
        self,
        request_id: str,
        doctor_name: str,
        edited_message: str,
        clinical_notes: Optional[str] = None
    ) -> HITLApprovalRequest:
        """Doctor edits the draft clinical message before approving dispatch."""
        req = self.get_request(request_id)
        if not req:
            raise ValueError(f"Approval request '{request_id}' not found.")
        now_utc = datetime.now(timezone.utc)
        req.status = "EDITED"
        req.reviewing_doctor = doctor_name
        req.doctor_edited_message = edited_message
        req.doctor_clinical_notes = clinical_notes
        req.reviewed_at = now_utc.isoformat()

        session = self.session_factory()
        try:
            rec = session.query(DoctorApprovalRequestModel).filter_by(id=request_id).first()
            if rec:
                rec.status = "EDITED"
                rec.reviewing_doctor_name = doctor_name
                rec.doctor_edited_message = edited_message
                rec.doctor_clinical_notes = clinical_notes
                rec.reviewed_at = now_utc
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update edited approval in DB: {e}")
            session.rollback()
        finally:
            session.close()

        self._sync_to_json()
        return req

    def reject_request(
        self,
        request_id: str,
        doctor_name: str,
        rejection_reason: str
    ) -> HITLApprovalRequest:
        """Doctor rejects the automated draft and mandates alternate clinical course."""
        req = self.get_request(request_id)
        if not req:
            raise ValueError(f"Approval request '{request_id}' not found.")
        now_utc = datetime.now(timezone.utc)
        req.status = "REJECTED"
        req.reviewing_doctor = doctor_name
        req.doctor_clinical_notes = rejection_reason
        req.reviewed_at = now_utc.isoformat()

        session = self.session_factory()
        try:
            rec = session.query(DoctorApprovalRequestModel).filter_by(id=request_id).first()
            if rec:
                rec.status = "REJECTED"
                rec.reviewing_doctor_name = doctor_name
                rec.doctor_clinical_notes = rejection_reason
                rec.reviewed_at = now_utc
                session.commit()
        except Exception as e:
            logger.error(f"Failed to update rejected approval in DB: {e}")
            session.rollback()
        finally:
            session.close()

        self._sync_to_json()
        return req


# Singleton Instance
_hitl_instance: Optional[HITLManager] = None

def get_hitl_manager() -> HITLManager:
    global _hitl_instance
    if _hitl_instance is None:
        _hitl_instance = HITLManager()
    return _hitl_instance
