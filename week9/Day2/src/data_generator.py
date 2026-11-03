"""City Care Clinics - Synthetic Patient & Clinic Data Generator.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Generates 500+ realistic synthetic Pakistani patients, 30 doctors across 6 specialties
and 5 branches, appointments, allergies, conditions, and FHIR lab observations.
Uses Faker and Synthea clinical distributions.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from faker import Faker

from db_models import (
    AllergyIntoleranceModel,
    AppointmentModel,
    ClinicBranchModel,
    ConditionModel,
    MedicationRequestModel,
    ObservationModel,
    PatientModel,
    PractitionerModel,
    get_db_engine,
    init_db,
)

fake = Faker()

# Seed for reproducible clinical evaluation
random.seed(42)
fake.seed_instance(42)

# 1. 5 Clinic Branches in Lahore & Islamabad
CLINIC_BRANCHES = [
    {
        "id": "BR_LHR_GULBERG",
        "name": "City Care Clinics — Gulberg Branch",
        "city": "Lahore",
        "address": "14-C Main Boulevard, Gulberg III, Lahore",
        "phone": "042-35789011",
        "emergency_hospital_nearby": "Services Hospital (Jail Road, Lahore)"
    },
    {
        "id": "BR_LHR_DHA",
        "name": "City Care Clinics — DHA Branch",
        "city": "Lahore",
        "address": "Sector Y, Commercial Phase 3, DHA Lahore",
        "phone": "042-35891234",
        "emergency_hospital_nearby": "National Hospital DHA (L-Block, Lahore)"
    },
    {
        "id": "BR_LHR_JOHAR",
        "name": "City Care Clinics — Johar Town Branch",
        "city": "Lahore",
        "address": "Plot 24, Civic Centre, Johar Town, Lahore",
        "phone": "042-35314567",
        "emergency_hospital_nearby": "Doctors Hospital & Medical Center (Canal Bank)"
    },
    {
        "id": "BR_ISB_F8",
        "name": "City Care Clinics — F-8 Markaz Branch",
        "city": "Islamabad",
        "address": "Executive Heights, F-8 Markaz, Islamabad",
        "phone": "051-2856711",
        "emergency_hospital_nearby": "Pakistan Institute of Medical Sciences (PIMS)"
    },
    {
        "id": "BR_ISB_BLUE_AREA",
        "name": "City Care Clinics — Blue Area Branch",
        "city": "Islamabad",
        "address": "72-West, Jinnah Avenue, Blue Area, Islamabad",
        "phone": "051-2278900",
        "emergency_hospital_nearby": "Shifa International Hospital (H-8/4, Islamabad)"
    }
]

# 2. 30 Doctors across 6 specialties
DOCTOR_CONFIGS = [
    # General Medicine (6 doctors)
    {"name": "Dr. Tariq Mahmood", "spec": "General Medicine", "qual": "MBBS, FCPS (Medicine)", "branch": "BR_LHR_GULBERG", "fee": 2000, "hours": "17:00-21:00"},
    {"name": "Dr. Ayesha Khan", "spec": "General Medicine", "qual": "MBBS, MRCP (UK)", "branch": "BR_LHR_DHA", "fee": 2500, "hours": "16:00-20:00"},
    {"name": "Dr. Muhammad Usman", "spec": "General Medicine", "qual": "MBBS, FCPS (Medicine)", "branch": "BR_LHR_JOHAR", "fee": 2000, "hours": "18:00-22:00"},
    {"name": "Dr. Salman Akram", "spec": "General Medicine", "qual": "MBBS, MCPS", "branch": "BR_ISB_F8", "fee": 2200, "hours": "15:00-19:00"},
    {"name": "Dr. Hina Rizvi", "spec": "General Medicine", "qual": "MBBS, FCPS (Internal Med)", "branch": "BR_ISB_BLUE_AREA", "fee": 2500, "hours": "17:00-21:00"},
    {"name": "Dr. Kamran Qureshi", "spec": "General Medicine", "qual": "MBBS, MD", "branch": "BR_LHR_GULBERG", "fee": 2200, "hours": "10:00-14:00"},

    # Paediatrics (5 doctors)
    {"name": "Dr. Fatima Zahra", "spec": "Paediatrics", "qual": "MBBS, FCPS (Paediatrics)", "branch": "BR_LHR_JOHAR", "fee": 2500, "hours": "16:00-20:00"},
    {"name": "Dr. Bilal Aslam", "spec": "Paediatrics", "qual": "MBBS, DCH, MRCPCH (UK)", "branch": "BR_LHR_DHA", "fee": 3000, "hours": "17:00-21:00"},
    {"name": "Dr. Sadia Munir", "spec": "Paediatrics", "qual": "MBBS, FCPS", "branch": "BR_LHR_GULBERG", "fee": 2200, "hours": "11:00-15:00"},
    {"name": "Dr. Imran Haider", "spec": "Paediatrics", "qual": "MBBS, MD (Paeds)", "branch": "BR_ISB_F8", "fee": 2500, "hours": "16:00-20:00"},
    {"name": "Dr. Nida Farooq", "spec": "Paediatrics", "qual": "MBBS, FCPS", "branch": "BR_ISB_BLUE_AREA", "fee": 2800, "hours": "17:00-21:00"},

    # Gynaecology & Obstetrics (5 doctors)
    {"name": "Dr. Noreen Tariq", "spec": "Gynaecology", "qual": "MBBS, FCPS (Obs & Gynae)", "branch": "BR_ISB_F8", "fee": 3000, "hours": "16:00-20:00"},
    {"name": "Dr. Saira Bano", "spec": "Gynaecology", "qual": "MBBS, MRCOG (UK)", "branch": "BR_LHR_DHA", "fee": 3500, "hours": "17:00-21:00"},
    {"name": "Dr. Uzma Khalid", "spec": "Gynaecology", "qual": "MBBS, FCPS", "branch": "BR_LHR_GULBERG", "fee": 2800, "hours": "10:00-14:00"},
    {"name": "Dr. Rabia Masood", "spec": "Gynaecology", "qual": "MBBS, MCPS, FCPS", "branch": "BR_LHR_JOHAR", "fee": 2500, "hours": "18:00-22:00"},
    {"name": "Dr. Bushra Jabeen", "spec": "Gynaecology", "qual": "MBBS, FCPS", "branch": "BR_ISB_BLUE_AREA", "fee": 3000, "hours": "15:00-19:00"},

    # Cardiology (5 doctors)
    {"name": "Dr. Zafar Iqbal", "spec": "Cardiology", "qual": "MBBS, FCPS (Cardiology)", "branch": "BR_LHR_GULBERG", "fee": 3500, "hours": "17:00-21:00"},
    {"name": "Dr. Asif Nawaz", "spec": "Cardiology", "qual": "MBBS, MRCP, FRCP (Cardio)", "branch": "BR_ISB_BLUE_AREA", "fee": 4000, "hours": "16:00-20:00"},
    {"name": "Dr. Fawad Ahmad", "spec": "Cardiology", "qual": "MBBS, FCPS", "branch": "BR_LHR_DHA", "fee": 3500, "hours": "18:00-22:00"},
    {"name": "Dr. Maria Latif", "spec": "Cardiology", "qual": "MBBS, Dip Cardio, FCPS", "branch": "BR_ISB_F8", "fee": 3200, "hours": "11:00-15:00"},
    {"name": "Dr. Haroon Rasheed", "spec": "Cardiology", "qual": "MBBS, FCPS", "branch": "BR_LHR_JOHAR", "fee": 3000, "hours": "17:00-21:00"},

    # Dermatology (5 doctors)
    {"name": "Dr. Zainab Arshad", "spec": "Dermatology", "qual": "MBBS, MCPS, FCPS (Derm)", "branch": "BR_LHR_DHA", "fee": 2500, "hours": "16:00-20:00"},
    {"name": "Dr. Omer Saeed", "spec": "Dermatology", "qual": "MBBS, Dip Derm (UK)", "branch": "BR_LHR_GULBERG", "fee": 2200, "hours": "17:00-21:00"},
    {"name": "Dr. Samina Tahir", "spec": "Dermatology", "qual": "MBBS, FCPS", "branch": "BR_ISB_F8", "fee": 2500, "hours": "15:00-19:00"},
    {"name": "Dr. Hamza Shah", "spec": "Dermatology", "qual": "MBBS, MSc Dermatology", "branch": "BR_ISB_BLUE_AREA", "fee": 2800, "hours": "18:00-22:00"},
    {"name": "Dr. Mahnoor Ali", "spec": "Dermatology", "qual": "MBBS, FCPS", "branch": "BR_LHR_JOHAR", "fee": 2200, "hours": "10:00-14:00"},

    # ENT (4 doctors)
    {"name": "Dr. Mansoor Ahmed", "spec": "ENT", "qual": "MBBS, FCPS (Oto-Rhino-Laryngology)", "branch": "BR_LHR_GULBERG", "fee": 2200, "hours": "17:00-21:00"},
    {"name": "Dr. Tahira Perveen", "spec": "ENT", "qual": "MBBS, DLO, FCPS", "branch": "BR_LHR_JOHAR", "fee": 2000, "hours": "16:00-20:00"},
    {"name": "Dr. Qasim Raza", "spec": "ENT", "qual": "MBBS, FRCS (ENT)", "branch": "BR_ISB_F8", "fee": 2800, "hours": "18:00-22:00"},
    {"name": "Dr. Farhan Siddiqui", "spec": "ENT", "qual": "MBBS, FCPS", "branch": "BR_ISB_BLUE_AREA", "fee": 2500, "hours": "15:00-19:00"}
]

# Pakistani Common First & Last Names
PAKISTANI_MALE_FIRST = [
    "Muhammad", "Ahmed", "Ali", "Usman", "Hamza", "Bilal", "Zubair", "Tariq",
    "Fahad", "Imran", "Kashif", "Waqas", "Babar", "Haroon", "Saad", "Shoaib"
]
PAKISTANI_FEMALE_FIRST = [
    "Fatima", "Ayesha", "Zainab", "Maryam", "Sana", "Hira", "Sadia", "Noor",
    "Amna", "Mahnoor", "Rabia", "Anum", "Khadija", "Sidra", "Iqra", "Bushra"
]
PAKISTANI_LAST = [
    "Khan", "Ali", "Ahmed", "Malik", "Chaudhry", "Bhatti", "Sheikh", "Qureshi",
    "Raza", "Hussain", "Shah", "Siddiqui", "Mehmood", "Mirza", "Ansari", "Abbasi"
]

COMMON_ALLERGIES = [
    "Penicillin", "Amoxicillin", "Sulfa Drugs", "Aspirin", "Ibuprofen (NSAIDs)",
    "Ciprofloxacin", "Cephalosporins", "Pollen / Dust", "None Reported"
]

COMMON_CONDITIONS = [
    {"code": "E11.9", "display": "Type 2 Diabetes Mellitus"},
    {"code": "I10", "display": "Essential (Primary) Hypertension"},
    {"code": "J45.909", "display": "Bronchial Asthma"},
    {"code": "I25.10", "display": "Ischemic Heart Disease (Atherosclerotic)"},
    {"code": "K27.9", "display": "Peptic Ulcer Disease"},
    {"code": "L20.9", "display": "Atopic Dermatitis (Eczema)"},
    {"code": "E03.9", "display": "Hypothyroidism"},
    {"code": "E78.5", "display": "Hyperlipidemia / Dyslipidemia"},
    {"code": "H66.90", "display": "Otitis Media (Middle Ear Infection)"}
]

COMMON_MEDS = [
    {"brand": "Panadol 500mg", "generic": "Paracetamol", "dose": 500.0, "freq": "TDS"},
    {"brand": "Glucophage 500mg", "generic": "Metformin", "dose": 500.0, "freq": "BD"},
    {"brand": "Concor 2.5mg", "generic": "Bisoprolol", "dose": 2.5, "freq": "OD"},
    {"brand": "Lipiget 20mg", "generic": "Atorvastatin", "dose": 20.0, "freq": "OD"},
    {"brand": "Augmentin 625mg", "generic": "Amoxicillin / Clavulanate", "dose": 625.0, "freq": "BD"},
    {"brand": "Risek 20mg", "generic": "Omeprazole", "dose": 20.0, "freq": "OD"},
    {"brand": "Disprin 300mg", "generic": "Aspirin", "dose": 300.0, "freq": "SOS"},
    {"brand": "Ventolin Inhaler", "generic": "Salbutamol", "dose": 0.1, "freq": "PRN"}
]


def generate_synthetic_data(num_patients: int = 500, session=None) -> Dict[str, int]:
    """Generates complete FHIR dataset and loads into the database session."""
    if session is None:
        engine = get_db_engine()
        session_factory = init_db(engine)
        session = session_factory()

    print(f"Generating synthetic clinical dataset ({num_patients} patients, 30 doctors, 5 branches)...")

    # 1. Insert Clinic Branches
    for br in CLINIC_BRANCHES:
        if not session.query(ClinicBranchModel).filter_by(id=br["id"]).first():
            branch_obj = ClinicBranchModel(**br)
            session.add(branch_obj)
    session.commit()

    # 2. Insert 30 Doctors
    doctor_objs: List[PractitionerModel] = []
    for idx, doc_data in enumerate(DOCTOR_CONFIGS, 1):
        doc_id = f"DOC_{idx:03d}"
        if not session.query(PractitionerModel).filter_by(id=doc_id).first():
            doc = PractitionerModel(
                id=doc_id,
                name=doc_data["name"],
                specialty=doc_data["spec"],
                branch_id=doc_data["branch"],
                pmdc_number=f"{random.randint(10000, 99999)}-P",
                qualification=doc_data["qual"],
                experience_years=random.randint(6, 28),
                consultation_fee_pkr=doc_data["fee"],
                languages_spoken="Urdu, English, Punjabi",
                available_days="Mon-Sat",
                shift_hours=doc_data["hours"]
            )
            session.add(doc)
            doctor_objs.append(doc)
        else:
            doctor_objs.append(session.query(PractitionerModel).filter_by(id=doc_id).first())
    session.commit()

    # 3. Generate 500+ Patients
    created_patients = 0
    created_appointments = 0
    created_observations = 0

    cities = ["Lahore", "Islamabad", "Rawalpindi"]
    branches = [b["id"] for b in CLINIC_BRANCHES]

    for p_idx in range(1, num_patients + 1):
        patient_id = f"PT_{p_idx:04d}"
        if session.query(PatientModel).filter_by(id=patient_id).first():
            continue

        gender = random.choice(["MALE", "FEMALE"])
        if gender == "MALE":
            name = f"{random.choice(PAKISTANI_MALE_FIRST)} {random.choice(PAKISTANI_LAST)}"
        else:
            name = f"{random.choice(PAKISTANI_FEMALE_FIRST)} {random.choice(PAKISTANI_LAST)}"

        # Age distribution: 15% pediatric (<14), 70% adult (15-60), 15% elderly (>60)
        age_roll = random.random()
        if age_roll < 0.15:
            age = random.randint(0, 13)
            is_pediatric = True
        elif age_roll < 0.85:
            age = random.randint(14, 59)
            is_pediatric = False
        else:
            age = random.randint(60, 84)
            is_pediatric = False

        birth_year = datetime.now().year - age
        birth_date = f"{birth_year}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"

        # Pakistani Mobile: 0300-0349
        phone = f"03{random.randint(0,4)}{random.randint(0,9)}-{random.randint(1000000, 9999999)}"
        # Pakistani CNIC: 35201-1234567-1
        cnic = f"{random.randint(31000, 39999)}-{random.randint(1000000, 9999999)}-{1 if gender == 'MALE' else 2}"
        city = random.choice(cities)
        address = f"House #{random.randint(1, 150)}, Street #{random.randint(1, 20)}, {random.choice(['Phase 5 DHA', 'Gulberg III', 'F-8/2', 'Johar Town', 'Model Town'])}, {city}"

        patient = PatientModel(
            id=patient_id,
            full_name=name,
            gender=gender,
            birth_date=birth_date,
            age=age,
            is_pediatric=is_pediatric,
            phone=phone,
            cnic=cnic,
            address=address,
            city=city,
            emergency_contact=f"0300-{random.randint(1000000, 9999999)}"
        )
        session.add(patient)

        # 3a. Patient Allergies (30% probability of allergy)
        if random.random() < 0.30:
            allergy_substance = random.choice(COMMON_ALLERGIES[:7])
            allergy = AllergyIntoleranceModel(
                id=f"ALG_{p_idx:04d}",
                patient_id=patient_id,
                substance=allergy_substance,
                clinical_status="active",
                criticality="high" if "Penicillin" in allergy_substance or "NSAID" in allergy_substance else "moderate",
                manifestation="Urticaria / Bronchospasm"
            )
            session.add(allergy)

        # 3b. Patient Chronic Conditions (40% probability)
        if random.random() < 0.40 and not is_pediatric:
            num_conds = random.randint(1, 2)
            selected_conds = random.sample(COMMON_CONDITIONS, num_conds)
            for c_idx, c_data in enumerate(selected_conds):
                cond = ConditionModel(
                    id=f"COND_{p_idx:04d}_{c_idx}",
                    patient_id=patient_id,
                    code=c_data["code"],
                    display_name=c_data["display"],
                    clinical_status="active",
                    severity="moderate"
                )
                session.add(cond)

        # 3c. Current Active Medications (35% probability)
        if random.random() < 0.35:
            med_data = random.choice(COMMON_MEDS)
            med = MedicationRequestModel(
                id=f"RX_{p_idx:04d}",
                patient_id=patient_id,
                medication_name=med_data["brand"],
                generic_name=med_data["generic"],
                dose_mg=med_data["dose"],
                frequency=med_data["freq"],
                status="active"
            )
            session.add(med)

        # 3d. Past and Upcoming Appointments (1-3 appointments)
        num_appts = random.randint(1, 3)
        for a_idx in range(num_appts):
            chosen_doc = random.choice(doctor_objs)
            day_offset = random.randint(-45, 14)
            appt_date = (datetime.now(timezone.utc) + timedelta(days=day_offset)).strftime("%Y-%m-%d 18:00")
            status = "fulfilled" if day_offset < 0 else "booked"

            appt = AppointmentModel(
                id=f"APT_{p_idx:04d}_{a_idx}",
                patient_id=patient_id,
                practitioner_id=chosen_doc.id,
                branch_id=chosen_doc.branch_id,
                specialty=chosen_doc.specialty,
                slot_datetime=appt_date,
                status=status,
                token_number=random.randint(1, 25),
                chief_complaint=random.choice([
                    "Fever & dry cough", "Routine diabetes follow-up", "Blood pressure check",
                    "Skin rash on forearms", "Sore throat & ear pain", "Child wellness vaccination"
                ])
            )
            session.add(appt)
            created_appointments += 1

        # 3e. Lab Observations (Observations for 60% of patients)
        if random.random() < 0.60:
            obs_type = random.choice(["HbA1c", "CBC", "Lipid", "LFT", "RFT"])
            obs_date = (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d")

            if obs_type == "HbA1c":
                val = round(random.uniform(5.2, 10.5), 1)
                interp = "NORMAL" if val < 5.7 else ("HIGH" if val < 8.0 else "CRITICAL")
                obs = ObservationModel(
                    id=f"OBS_{p_idx:04d}_HBA1C",
                    patient_id=patient_id,
                    test_category="HbA1c",
                    code="4548-4",
                    display_name="Glycated Hemoglobin (HbA1c)",
                    value_numeric=val,
                    unit="%",
                    reference_low=4.0,
                    reference_high=5.6,
                    interpretation=interp,
                    effective_datetime=obs_date
                )
                session.add(obs)
                created_observations += 1

            elif obs_type == "CBC":
                hb_val = round(random.uniform(9.0, 16.5), 1)
                hb_interp = "LOW" if hb_val < 11.5 else ("HIGH" if hb_val > 15.5 else "NORMAL")
                obs = ObservationModel(
                    id=f"OBS_{p_idx:04d}_HB",
                    patient_id=patient_id,
                    test_category="CBC",
                    code="718-7",
                    display_name="Hemoglobin (Hb)",
                    value_numeric=hb_val,
                    unit="g/dL",
                    reference_low=12.0,
                    reference_high=15.5,
                    interpretation=hb_interp,
                    effective_datetime=obs_date
                )
                session.add(obs)
                created_observations += 1

            elif obs_type == "Lipid":
                chol_val = round(random.uniform(140.0, 270.0), 0)
                interp = "NORMAL" if chol_val < 200 else "HIGH"
                obs = ObservationModel(
                    id=f"OBS_{p_idx:04d}_CHOL",
                    patient_id=patient_id,
                    test_category="Lipid",
                    code="2093-3",
                    display_name="Total Cholesterol",
                    value_numeric=chol_val,
                    unit="mg/dL",
                    reference_low=120.0,
                    reference_high=200.0,
                    interpretation=interp,
                    effective_datetime=obs_date
                )
                session.add(obs)
                created_observations += 1

        created_patients += 1
        if p_idx % 100 == 0:
            session.commit()
            print(f"  ... committed {p_idx} patients to database.")

    session.commit()

    total_patients = session.query(PatientModel).count()
    total_doctors = session.query(PractitionerModel).count()
    total_branches = session.query(ClinicBranchModel).count()
    total_appts = session.query(AppointmentModel).count()
    total_obs = session.query(ObservationModel).count()

    print(f"\n[DATA GENERATION COMPLETE]")
    print(f"  • Patients:      {total_patients}")
    print(f"  • Doctors:       {total_doctors}")
    print(f"  • Branches:      {total_branches}")
    print(f"  • Appointments:  {total_appts}")
    print(f"  • Observations:  {total_obs}")

    return {
        "patients": total_patients,
        "doctors": total_doctors,
        "branches": total_branches,
        "appointments": total_appts,
        "observations": total_obs
    }


if __name__ == "__main__":
    generate_synthetic_data(500)
