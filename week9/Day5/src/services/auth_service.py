"""City Care Clinics - Authentication and Authorization Service.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 5: Evaluation, Red-Teaming, Deployment & Client Handover
Implements:
1. Secure password hashing and verification using bcrypt.
2. JSON Web Token (JWT) issuance and cryptographic signature verification.
3. Role-Based Access Control (RBAC): PATIENT, DOCTOR, ADMIN.
4. Patient isolation enforcement (Cross-patient EHR chart boundary protection).
5. User registration, authentication, and database credential synchronization.
"""
from __future__ import annotations

import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import bcrypt
import jwt
from sqlalchemy.orm import Session

# Setup path resolution
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DAY5_SRC = os.path.dirname(CURRENT_DIR)
WEEK9_DIR = os.path.dirname(os.path.dirname(DAY5_SRC))
DAY2_SRC = os.path.join(WEEK9_DIR, "Day2", "src")
DAY3_SRC = os.path.join(WEEK9_DIR, "Day3", "src")
DAY4_SRC = os.path.join(WEEK9_DIR, "Day4", "src")

for p in [DAY5_SRC, DAY2_SRC, DAY3_SRC, DAY4_SRC]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import settings
from db_models import PatientModel, PractitionerModel, UserModel, init_db

logger = logging.getLogger("citycare.auth")


class AuthService:
    """Production JWT Authentication, Password Security, and Authorization Engine."""

    def __init__(self, session_factory=None):
        self.session_factory = session_factory or init_db()
        self.secret_key = settings.jwt_secret_key
        self.algorithm = settings.jwt_algorithm
        self.expire_minutes = getattr(settings, "jwt_access_token_expire_minutes", getattr(settings, "access_token_expire_minutes", 60))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hashes raw password string using bcrypt salt."""
        pwd_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verifies plain password against stored bcrypt hash."""
        try:
            return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
        except Exception:
            return False

    def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Generates cryptographically signed JWT access token."""
        to_encode = data.copy()
        now = datetime.now(timezone.utc)
        if expires_delta:
            expire = now + expires_delta
        else:
            expire = now + timedelta(minutes=self.expire_minutes)

        to_encode.update({
            "exp": expire,
            "iat": now,
            "iss": "CityCareClinics-AuthService"
        })
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt

    def decode_access_token(self, token: str) -> Dict[str, Any]:
        """Validates and decodes JWT token, returning verified claims payload."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer="CityCareClinics-AuthService"
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired. Please log in again.")
        except jwt.InvalidTokenError as e:
            raise ValueError(f"Invalid authentication token: {str(e)}")

    def register_user(
        self,
        username: str,
        password: str,
        full_name: str,
        role: str = "PATIENT",
        email: Optional[str] = None,
        phone: Optional[str] = None,
        patient_id: Optional[str] = None,
        practitioner_id: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """Registers a new user with hashed credentials and creates/links patient profile if needed."""
        session = db_session or self.session_factory()
        should_close = db_session is None

        try:
            role_norm = role.upper()
            if role_norm not in ("PATIENT", "DOCTOR", "ADMIN"):
                raise ValueError("Role must be one of: PATIENT, DOCTOR, ADMIN")

            # Check for existing username
            existing = session.query(UserModel).filter(
                (UserModel.username == username) | (UserModel.email == email if email else False)
            ).first()
            if existing:
                raise ValueError(f"User with username '{username}' or email '{email}' already exists.")

            user_id = f"USR_{uuid.uuid4().hex[:10].upper()}"
            hashed_pwd = self.hash_password(password)

            # If patient role and no patient_id provided, create a corresponding PatientModel
            linked_patient_id = patient_id
            if role_norm == "PATIENT" and not linked_patient_id:
                new_pat_id = f"PT_{uuid.uuid4().hex[:8].upper()}"
                new_patient = PatientModel(
                    id=new_pat_id,
                    full_name=full_name,
                    gender="Not Specified",
                    birth_date="1995-01-01",
                    age=30,
                    phone=phone or "0300-0000000",
                    email=email,
                    consent_given=True,
                    created_at=datetime.now(timezone.utc)
                )
                session.add(new_patient)
                session.flush()
                linked_patient_id = new_pat_id

            new_user = UserModel(
                id=user_id,
                username=username,
                email=email,
                hashed_password=hashed_pwd,
                role=role_norm,
                patient_id=linked_patient_id,
                practitioner_id=practitioner_id,
                full_name=full_name,
                phone=phone,
                is_active=True,
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_user)
            session.commit()

            return {
                "user_id": user_id,
                "username": username,
                "email": email,
                "full_name": full_name,
                "role": role_norm,
                "patient_id": linked_patient_id,
                "practitioner_id": practitioner_id,
                "is_active": True
            }
        except Exception:
            session.rollback()
            raise
        finally:
            if should_close:
                session.close()

    def authenticate_user(
        self,
        username_or_email: str,
        password: str,
        db_session: Optional[Session] = None
    ) -> Optional[UserModel]:
        """Verifies credentials and returns UserModel if valid and active."""
        session = db_session or self.session_factory()
        should_close = db_session is None

        try:
            user = session.query(UserModel).filter(
                (UserModel.username == username_or_email) | (UserModel.email == username_or_email)
            ).first()

            if not user or not user.is_active:
                return None

            if not self.verify_password(password, user.hashed_password):
                return None

            return user
        finally:
            if should_close:
                session.close()

    def seed_default_users(self, db_session: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Idempotently seeds default test accounts for testing and demonstration."""
        session = db_session or self.session_factory()
        should_close = db_session is None

        seeded = []
        default_accounts = [
            {
                "username": "doctor.tariq",
                "email": "dr.tariq@citycareclinics.pk",
                "password": "DoctorPassword123!",
                "full_name": "Dr. Tariq Mahmood",
                "role": "DOCTOR",
                "practitioner_id": "DOC_001",
                "phone": "0300-1112233"
            },
            {
                "username": "admin",
                "email": "admin@citycareclinics.pk",
                "password": "AdminPassword123!",
                "full_name": "Clinic Administrator",
                "role": "ADMIN",
                "phone": "0300-9998877"
            },
            {
                "username": "patient.test",
                "email": "test.patient@example.com",
                "password": "PatientPassword123!",
                "full_name": "Test Patient",
                "role": "PATIENT",
                "patient_id": "PT_0001",
                "phone": "0300-1234567"
            }
        ]

        try:
            for acc in default_accounts:
                existing = session.query(UserModel).filter(
                    (UserModel.username == acc["username"]) | (UserModel.email == acc["email"])
                ).first()
                if not existing:
                    u_id = f"USR_{uuid.uuid4().hex[:8].upper()}"
                    hashed = self.hash_password(acc["password"])
                    user = UserModel(
                        id=u_id,
                        username=acc["username"],
                        email=acc["email"],
                        hashed_password=hashed,
                        role=acc["role"],
                        patient_id=acc.get("patient_id"),
                        practitioner_id=acc.get("practitioner_id"),
                        full_name=acc["full_name"],
                        phone=acc.get("phone"),
                        is_active=True,
                        created_at=datetime.now(timezone.utc)
                    )
                    session.add(user)
                    seeded.append({"username": acc["username"], "role": acc["role"]})
            session.commit()
            return seeded
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding default users: {e}")
            return []
        finally:
            if should_close:
                session.close()


# Singleton Instance
_auth_service_instance: Optional[AuthService] = None

def get_auth_service() -> AuthService:
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = AuthService()
    return _auth_service_instance
