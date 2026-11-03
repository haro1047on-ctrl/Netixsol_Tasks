"""City Care Clinics - Master Idempotent Database & System Seeder.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Populates the database with:
1. 5 Clinic Branches in Lahore and Islamabad.
2. 30 Specialist Doctors across 6 medical specialties.
3. Doctor weekly schedules and shift templates.
4. 100+ Synthetic patients with FHIR allergies, chronic conditions, and lab observations.
5. Default administrative and clinical user accounts with bcrypt hashed passwords.
Safe and idempotent: Can be executed repeatedly without duplicating records or corrupting state.
"""
from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, time, timezone
from pathlib import Path

# Dynamic path configuration
SCRIPT_DIR = Path(__file__).resolve().parent
DAY2_SRC = SCRIPT_DIR.parent
WEEK9_DIR = DAY2_SRC.parent.parent
DAY5_SRC = WEEK9_DIR / "Day5" / "src"

for p in [str(DAY2_SRC), str(DAY5_SRC), str(WEEK9_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from db_models import (
    AllergyIntoleranceModel,
    AppointmentModel,
    ClinicBranchModel,
    ConditionModel,
    DoctorScheduleModel,
    MedicationRequestModel,
    ObservationModel,
    PatientModel,
    PractitionerModel,
    UserModel,
    get_db_engine,
    init_db,
)
from services.auth_service import AuthService
from data_generator import CLINIC_BRANCHES, DOCTOR_CONFIGS, generate_synthetic_data

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("citycare.seeder")


def seed_database(patient_count: int = 100) -> dict:
    """Executes idempotent database seeding."""
    logger.info("Initializing FHIR database schema...")
    engine = get_db_engine()
    session_factory = init_db(engine)
    session = session_factory()

    summary = {}

    try:
        # 1. Seed Clinic Branches
        existing_branches = session.query(ClinicBranchModel).count()
        if existing_branches == 0:
            logger.info("Seeding 5 clinic branches...")
            for b_data in CLINIC_BRANCHES:
                branch = ClinicBranchModel(**b_data)
                session.add(branch)
            session.commit()
            logger.info("  ✓ 5 branches seeded successfully.")
        else:
            logger.info(f"  ✓ Branches already populated ({existing_branches} found).")
        summary["branches"] = session.query(ClinicBranchModel).count()

        # 2. Seed Specialist Doctors
        existing_doctors = session.query(PractitionerModel).count()
        if existing_doctors == 0:
            logger.info("Seeding 30 specialist doctors...")
            for idx, doc_data in enumerate(DOCTOR_CONFIGS, 1):
                doc_id = f"DOC_{idx:03d}"
                doc = PractitionerModel(
                    id=doc_id,
                    name=doc_data["name"],
                    specialty=doc_data["spec"],
                    branch_id=doc_data["branch"],
                    pmdc_number=f"{10000 + idx}-P",
                    qualification=doc_data["qual"],
                    experience_years=10,
                    consultation_fee_pkr=doc_data["fee"],
                    languages_spoken="Urdu, English, Punjabi",
                    available_days="Mon-Sat",
                    shift_hours=doc_data["hours"]
                )
                session.add(doc)
            session.commit()
            logger.info("  ✓ 30 doctors seeded successfully.")
        else:
            logger.info(f"  ✓ Doctors already populated ({existing_doctors} found).")
        summary["doctors"] = session.query(PractitionerModel).count()

        # 3. Seed Doctor Schedules
        existing_schedules = session.query(DoctorScheduleModel).count()
        if existing_schedules == 0:
            logger.info("Seeding doctor weekly schedules...")
            doctors = session.query(PractitionerModel).all()
            days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            for doc in doctors:
                for day_idx, day_name in enumerate(days_of_week):
                    sched = DoctorScheduleModel(
                        id=f"SCHED_{doc.id}_D{day_idx}",
                        practitioner_id=doc.id,
                        day_of_week=day_name,
                        shift_start="09:00",
                        shift_end="17:00",
                        slot_duration_minutes=30,
                        is_active=True
                    )
                    session.add(sched)
            session.commit()
            logger.info("  ✓ Doctor schedules generated.")
        else:
            logger.info(f"  ✓ Doctor schedules already populated ({existing_schedules} found).")
        summary["schedules"] = session.query(DoctorScheduleModel).count()

        # 4. Seed Patients & Clinical Records
        existing_patients = session.query(PatientModel).count()
        if existing_patients < 50:
            logger.info(f"Seeding synthetic patients ({patient_count} target)...")
            generate_synthetic_data(num_patients=patient_count)
            logger.info("  ✓ Synthetic patients and observations generated.")
        else:
            logger.info(f"  ✓ Patients already populated ({existing_patients} found).")
        summary["patients"] = session.query(PatientModel).count()
        summary["observations"] = session.query(ObservationModel).count()
        summary["appointments"] = session.query(AppointmentModel).count()

        # 5. Seed Default User Credentials
        logger.info("Seeding default authentication accounts...")
        auth_service = AuthService(session_factory=session_factory)
        seeded_users = auth_service.seed_default_users(session)
        summary["users"] = session.query(UserModel).count()
        summary["newly_seeded_users"] = len(seeded_users)
        logger.info(f"  ✓ Default accounts verified. Total users: {summary['users']}.")

        print("\n" + "="*60)
        print("   CITY CARE CLINICS — SEED SUMMARY")
        print("="*60)
        print(f"  • Clinic Branches:      {summary['branches']}")
        print(f"  • Doctors / Staff:      {summary['doctors']}")
        print(f"  • Doctor Schedules:     {summary['schedules']}")
        print(f"  • Patient Records:      {summary['patients']}")
        print(f"  • Lab Observations:     {summary['observations']}")
        print(f"  • Appointments:         {summary['appointments']}")
        print(f"  • User Accounts:        {summary['users']}")
        print("="*60)
        print("   DEFAULT DEMO CREDENTIALS:")
        print("   1. Doctor: doctor.tariq  / DoctorPassword123!")
        print("   2. Admin:  admin         / AdminPassword123!")
        print("   3. Patient: patient.test / PatientPassword123!")
        print("="*60 + "\n")

        return summary

    except Exception as e:
        session.rollback()
        logger.error(f"Seeding failed: {e}", exc_info=True)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
