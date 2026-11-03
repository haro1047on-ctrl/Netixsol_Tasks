"""City Care Clinics - Synthetic Lab Report PDF Generator.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Generates 30 synthetic diagnostic lab report PDFs (CBC, LFT, Lipid Profile, HbA1c, RFT)
using ReportLab with realistic Pakistani patient names, quantitative metrics, and reference intervals.
"""
from __future__ import annotations

import os
import random
from datetime import datetime, timedelta
from typing import Dict, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# Test Panel Templates with Reference Intervals
PANEL_DEFINITIONS: Dict[str, List[Dict[str, Any]]] = {
    "COMPLETE_BLOOD_COUNT": [
        {"test": "Hemoglobin (Hb)", "unit": "g/dL", "low": 12.0, "high": 16.5, "range_str": "12.0 - 16.5"},
        {"test": "White Blood Cell (WBC)", "unit": "x10^3/uL", "low": 4.0, "high": 11.0, "range_str": "4.0 - 11.0"},
        {"test": "Platelet Count", "unit": "x10^3/uL", "low": 150.0, "high": 450.0, "range_str": "150 - 450"},
        {"test": "Red Blood Cell (RBC)", "unit": "x10^6/uL", "low": 4.2, "high": 5.8, "range_str": "4.2 - 5.8"},
        {"test": "Hematocrit (PCV)", "unit": "%", "low": 36.0, "high": 50.0, "range_str": "36.0 - 50.0"}
    ],
    "LIPID_PROFILE": [
        {"test": "Total Cholesterol", "unit": "mg/dL", "low": 125.0, "high": 200.0, "range_str": "< 200"},
        {"test": "Triglycerides", "unit": "mg/dL", "low": 50.0, "high": 150.0, "range_str": "< 150"},
        {"test": "HDL Cholesterol", "unit": "mg/dL", "low": 40.0, "high": 60.0, "range_str": "> 40.0"},
        {"test": "LDL Cholesterol", "unit": "mg/dL", "low": 60.0, "high": 100.0, "range_str": "< 100"}
    ],
    "LIVER_FUNCTION_TEST": [
        {"test": "Bilirubin Total", "unit": "mg/dL", "low": 0.2, "high": 1.2, "range_str": "0.2 - 1.2"},
        {"test": "ALT (SGPT)", "unit": "U/L", "low": 7.0, "high": 45.0, "range_str": "7.0 - 45.0"},
        {"test": "AST (SGOT)", "unit": "U/L", "low": 8.0, "high": 40.0, "range_str": "8.0 - 40.0"},
        {"test": "Alkaline Phosphatase (ALP)", "unit": "U/L", "low": 44.0, "high": 147.0, "range_str": "44 - 147"}
    ],
    "RENAL_FUNCTION_TEST": [
        {"test": "Serum Creatinine", "unit": "mg/dL", "low": 0.6, "high": 1.2, "range_str": "0.6 - 1.2"},
        {"test": "Blood Urea Nitrogen (BUN)", "unit": "mg/dL", "low": 7.0, "high": 20.0, "range_str": "7.0 - 20.0"},
        {"test": "Uric Acid", "unit": "mg/dL", "low": 3.5, "high": 7.2, "range_str": "3.5 - 7.2"}
    ],
    "HBA1C_TEST": [
        {"test": "Glycated Hemoglobin (HbA1c)", "unit": "%", "low": 4.0, "high": 5.6, "range_str": "4.0 - 5.6"}
    ]
}

SAMPLE_PATIENTS = [
    ("Muhammad Usman", "32", "Male", "0300-1234567"),
    ("Fatima Zahra", "28", "Female", "0321-9876543"),
    ("Tariq Mahmood", "54", "Male", "0333-5551234"),
    ("Ayesha Siddiqua", "46", "Female", "0312-8889999"),
    ("Hamza Bilal", "19", "Male", "0301-4447777"),
    ("Zainab Bibi", "62", "Female", "0345-6663333")
]


def generate_30_lab_reports(output_dir: str = None) -> List[str]:
    """Generates 30 synthetic PDF lab reports across diagnostic panels."""
    if not output_dir:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, "data", "lab_reports")

    os.makedirs(output_dir, exist_ok=True)
    pdf_paths: List[str] = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#0D47A1"), alignment=1)
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#333333"))

    panels = list(PANEL_DEFINITIONS.keys())

    for idx in range(1, 31):
        panel_key = panels[(idx - 1) % len(panels)]
        patient = SAMPLE_PATIENTS[(idx - 1) % len(SAMPLE_PATIENTS)]
        report_id = f"LAB_REP_{idx:03d}"
        file_path = os.path.join(output_dir, f"{report_id}.pdf")

        doc = SimpleDocTemplate(file_path, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        story = []

        # Header
        story.append(Paragraph("CITY CARE CLINICS & DIAGNOSTIC LABORATORIES", title_style))
        story.append(Paragraph("Lahore — Islamabad Clinical Pathology Network | ISO 15189 Certified", meta_style))
        story.append(Spacer(1, 12))

        # Patient Info Box
        coll_date = (datetime.now() - timedelta(days=idx)).strftime("%Y-%m-%d %H:%M")
        pt_info_data = [
            [f"Patient Name: {patient[0]}", f"Age/Gender: {patient[1]} Y / {patient[2]}", f"Report ID: {report_id}"],
            [f"Phone: {patient[3]}", f"Collection Date: {coll_date}", f"Panel: {panel_key.replace('_', ' ')}"]
        ]
        pt_table = Table(pt_info_data, colWidths=[200, 180, 160])
        pt_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0F4F8")),
            ('TEXTCOLOR', (0,0), (-1,-1), colors.black),
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('TOPPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(pt_table)
        story.append(Spacer(1, 14))

        # Test Results Table
        table_rows = [["Investigation / Parameter", "Observed Value", "Unit", "Reference Interval", "Flag"]]
        tests = PANEL_DEFINITIONS[panel_key]

        for t in tests:
            # Inject abnormal values in ~35% of test rows for realistic clinical distribution
            is_abnormal = random.random() < 0.35
            low_val = t["low"]
            high_val = t["high"]

            if is_abnormal:
                if random.choice([True, False]):
                    val = round(high_val * random.uniform(1.15, 1.6), 2 if high_val < 10 else 1)
                    flag = "HIGH"
                else:
                    val = round(low_val * random.uniform(0.5, 0.85), 2 if low_val < 10 else 1)
                    flag = "LOW"
            else:
                val = round(random.uniform(low_val, high_val), 2 if high_val < 10 else 1)
                flag = "NORMAL"

            table_rows.append([t["test"], str(val), t["unit"], t["range_str"], flag])

        res_table = Table(table_rows, colWidths=[200, 100, 80, 110, 50])
        res_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0D47A1")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 9),
            ('ALIGN', (1,0), (-1,-1), 'CENTER'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CCCCCC")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F9F9F9")]),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('TOPPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(res_table)
        story.append(Spacer(1, 20))

        # Footer Notice
        disclaimer = (
            "NOTICE: This laboratory diagnostic report is generated for authorized clinical review. "
            "Interpretation must be performed in correlation with clinical history by a licensed physician. "
            "Out-of-range values require clinical correlation and follow-up consultation."
        )
        story.append(Paragraph(disclaimer, ParagraphStyle("Disc", parent=styles["Italic"], fontSize=7, textColor=colors.HexColor("#777777"))))

        doc.build(story)
        pdf_paths.append(file_path)

    print(f"Successfully generated 30 synthetic PDF lab reports in {output_dir}")
    return pdf_paths


if __name__ == "__main__":
    generate_30_lab_reports()
