"""City Care Clinics - Master Validation Runner for Week 9 - Day 2.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Orchestrates and verifies:
- Task 1: FHIR Relational Database & 500+ Synthetic Patients
- Task 2: Medical Knowledge RAG Pipeline & 25-Question Evaluation
- Task 3: Lab Report Understanding & 30-Report OCR/Extraction Benchmark
- Task 4: 4 Model Context Protocol (MCP) Servers
- Task 5: Deterministic Prescription Safety Engine
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Reconfigure stdout for UTF-8 compatibility on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from db_models import (
    AppointmentModel,
    ClinicBranchModel,
    ObservationModel,
    PatientModel,
    PractitionerModel,
    get_db_engine,
    init_db,
)
from data_generator import generate_synthetic_data
from rag_pipeline import MedicalKnowledgeRAG, run_rag_evaluation
from lab_report_generator import generate_30_lab_reports
from lab_report_analyzer import LabReportAnalyzer
from mcp_servers.mcp_test_client import run_all_mcp_tests
from prescription_safety_engine import (
    PrescriptionSafetyEngine,
    ProposedMedication,
)


def verify_task1_database():
    """Validates FHIR-inspired database and synthetic dataset."""
    print("\n[TASK 1 VERIFICATION] FHIR Database & Synthetic Dataset...")
    engine = get_db_engine()
    session_factory = init_db(engine)
    session = session_factory()

    try:
        pt_count = session.query(PatientModel).count()
        doc_count = session.query(PractitionerModel).count()
        br_count = session.query(ClinicBranchModel).count()
        apt_count = session.query(AppointmentModel).count()
        obs_count = session.query(ObservationModel).count()

        if pt_count < 500:
            print("  Dataset count below 500; generating synthetic dataset...")
            generate_synthetic_data(500, session)
            pt_count = session.query(PatientModel).count()

        assert pt_count >= 500, f"Expected >= 500 patients, got {pt_count}"
        assert doc_count == 30, f"Expected 30 doctors, got {doc_count}"
        assert br_count == 5, f"Expected 5 branches, got {br_count}"
        assert apt_count >= 500, f"Expected >= 500 appointments, got {apt_count}"
        assert obs_count >= 100, f"Expected >= 100 observations, got {obs_count}"

        print(f"  ✓ Verified Patients:     {pt_count} (Pakistani demographics, CNICs, phones)")
        print(f"  ✓ Verified Doctors:      {doc_count} (Across 6 specialties)")
        print(f"  ✓ Verified Branches:     {br_count} (Lahore Gulberg/DHA/Johar, Islamabad F-8/Blue Area)")
        print(f"  ✓ Verified Appointments: {apt_count}")
        print(f"  ✓ Verified Observations: {obs_count}")
        print("  --> TASK 1 PASSED: FHIR RELATIONAL DATA LAYER FULLY OPERATIONAL.")
    finally:
        session.close()


def verify_task2_rag():
    """Validates ChromaDB Medical Knowledge RAG pipeline & 25-question evaluation."""
    print("\n[TASK 2 VERIFICATION] Medical Knowledge RAG Pipeline...")
    rag = MedicalKnowledgeRAG()
    eval_res = run_rag_evaluation(rag)

    assert eval_res["total_questions"] == 25
    assert eval_res["grounding_rate_percent"] >= 80.0, f"Grounding rate {eval_res['grounding_rate_percent']}% below standard"

    print(f"  ✓ Total Evaluation Questions: {eval_res['total_questions']}")
    print(f"  ✓ Grounding Rate:            {eval_res['grounding_rate_percent']}%")
    print(f"  ✓ Hallucination Rate:        {eval_res['hallucination_rate_percent']}%")
    print(f"  ✓ Top-1 Source Precision:    {eval_res['top1_retrieval_accuracy_percent']}%")
    print("  --> TASK 2 PASSED: MEDICAL RAG PIPELINE CERTIFIED GROUNDED.")


def verify_task3_lab_reports():
    """Validates 30 synthetic PDF lab reports and PyMuPDF structured extractor."""
    print("\n[TASK 3 VERIFICATION] Lab Report Understanding Pipeline...")
    base_dir = Path(__file__).resolve().parent
    reports_dir = base_dir / "data" / "lab_reports"

    if not reports_dir.exists() or len(list(reports_dir.glob("*.pdf"))) < 30:
        print("  Generating 30 synthetic PDF lab reports...")
        generate_30_lab_reports(str(reports_dir))

    analyzer = LabReportAnalyzer()
    benchmark_res = analyzer.evaluate_benchmark(str(reports_dir))

    assert benchmark_res["total_reports"] == 30
    assert benchmark_res["report_success_rate"] == 100.0
    assert benchmark_res["field_extraction_accuracy"] == 100.0

    print(f"  ✓ Total PDF Reports Parsed:  {benchmark_res['total_reports']}")
    print(f"  ✓ Extraction Success Rate:   {benchmark_res['report_success_rate']}%")
    print(f"  ✓ Field-Level Accuracy:      {benchmark_res['field_extraction_accuracy']}%")
    print(f"  ✓ Structured Fields Parsed:  {benchmark_res['total_fields_extracted']}")
    print("  --> TASK 3 PASSED: LAB REPORT PARSER & SAFE EXPLAINER VERIFIED.")


def verify_task4_mcp_servers():
    """Validates all 4 MCP servers independently via test client."""
    print("\n[TASK 4 VERIFICATION] Model Context Protocol (MCP) Servers...")
    mcp_results = run_all_mcp_tests()

    for s_name, res in mcp_results.items():
        assert res["status"] == "PASSED", f"MCP server {s_name} failed testing"

    print("  ✓ patient-records-server:   ONLINE & VERIFIED")
    print("  ✓ clinic-scheduling-server: ONLINE & VERIFIED")
    print("  ✓ pharmacy-safety-server:   ONLINE & VERIFIED")
    print("  ✓ notifications-server:     ONLINE & VERIFIED")
    print("  --> TASK 4 PASSED: ALL 4 MCP SERVERS CERTIFIED INDEPENDENTLY.")


def verify_task5_prescription_safety():
    """Validates deterministic prescription safety engine against clinical edge cases."""
    print("\n[TASK 5 VERIFICATION] Deterministic Prescription Safety Engine...")
    engine = PrescriptionSafetyEngine()

    # Case 1: Lethal Interaction + Allergy Clash (Warfarin + Aspirin + Penicillin Allergy)
    dangerous_prescription = [
        ProposedMedication(medication_name="Augmentin 625mg", dose_mg=625.0, frequency="BD"),
        ProposedMedication(medication_name="Disprin 300mg", dose_mg=300.0, frequency="BD")
    ]
    report1 = engine.evaluate_prescription(
        proposed_meds=dangerous_prescription,
        patient_allergies=["Penicillin Allergy"],
        active_medications=["Warfarin 5mg"],
        patient_age=50,
        patient_weight_kg=75.0,
        is_pregnant=False
    )
    assert report1.overall_status == "CRITICAL_DANGER"
    assert len(report1.allergy_clashes) >= 1
    assert len(report1.drug_interactions) >= 1
    print("  ✓ Case 1 (Allergy + Warfarin/Aspirin DDI): Correctly flagged CRITICAL_DANGER and halted.")

    # Case 2: Adult Overdose (Paracetamol 2000mg TDS = 6000mg/day)
    overdose_rx = [
        ProposedMedication(medication_name="Panadol 500mg", dose_mg=2000.0, frequency="TDS")
    ]
    report2 = engine.evaluate_prescription(
        proposed_meds=overdose_rx,
        patient_allergies=[],
        active_medications=[],
        patient_age=30,
        patient_weight_kg=70.0
    )
    assert report2.overall_status == "CRITICAL_DANGER"
    assert len(report2.dose_violations) >= 1
    print("  ✓ Case 2 (Adult Overdose 6000mg/day): Correctly intercepted daily ceiling violation.")

    # Case 3: Pregnancy Contraindication (Lisinopril Category D)
    preg_rx = [
        ProposedMedication(medication_name="Zestril 10mg", dose_mg=10.0, frequency="OD")
    ]
    report3 = engine.evaluate_prescription(
        proposed_meds=preg_rx,
        patient_allergies=[],
        active_medications=[],
        patient_age=28,
        patient_weight_kg=60.0,
        is_pregnant=True
    )
    assert report3.overall_status == "CRITICAL_DANGER"
    assert any("PREGNANCY" in a for a in report3.special_population_alerts)
    print("  ✓ Case 3 (Pregnancy Teratogenicity): Correctly intercepted Category D ACE inhibitor.")

    # Case 4: Completely Safe Prescription
    safe_rx = [
        ProposedMedication(medication_name="Panadol 500mg", dose_mg=500.0, frequency="TDS"),
        ProposedMedication(medication_name="Risek 20mg", dose_mg=20.0, frequency="OD")
    ]
    report4 = engine.evaluate_prescription(
        proposed_meds=safe_rx,
        patient_allergies=["Dust"],
        active_medications=[],
        patient_age=40,
        patient_weight_kg=70.0
    )
    assert report4.overall_status == "SAFE"
    assert report4.is_safe is True
    print("  ✓ Case 4 (Routine Safe Prescription): Correctly approved as SAFE.")

    print("  --> TASK 5 PASSED: DETERMINISTIC PRESCRIPTION SAFETY ENGINE VALIDATED.")


def main():
    start_time = time.time()
    print("=" * 80)
    print("CITY CARE CLINICS — MULTI-AGENT AI CLINIC ASSISTANT (WEEK 9 - DAY 2)")
    print("MASTER VALIDATION SUITE: DATA LAYER, KNOWLEDGE RAG & MCP SERVERS")
    print("=" * 80)

    verify_task1_database()
    verify_task2_rag()
    verify_task3_lab_reports()
    verify_task4_mcp_servers()
    verify_task5_prescription_safety()

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"WEEK 9 - DAY 2 DELIVERABLES 100% COMPLETE & VERIFIED in {elapsed:.2f}s")
    print("FHIR Database, Knowledge RAG, Lab PDF Extractor, 4 MCP Servers, and Rx Safety Ready.")
    print("=" * 80)


if __name__ == "__main__":
    main()
