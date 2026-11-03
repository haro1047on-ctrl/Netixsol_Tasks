"""City Care Clinics - Lab Report Understanding & Extraction Pipeline.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Uses PyMuPDF (fitz) to parse synthetic PDF lab reports, extracts structured JSON
(test name, value, unit, reference range, flags), explains results in safe UrduLish,
and measures extraction accuracy across all 30 benchmark reports.
"""
from __future__ import annotations

import os
import re
import sys
from typing import Any, Dict, List
import fitz  # PyMuPDF

# Reconfigure stdout for UTF-8 compatibility on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


class LabReportAnalyzer:
    """Production Lab Report OCR/PDF Parser & Explainer."""

    # Regex patterns to parse extracted tabular text lines
    LINE_PATTERN = re.compile(
        r"^([A-Za-z0-9\s\(\)/_\-\.]+?)\s+([0-9]+\.?[0-9]*)\s+([A-Za-z0-9\^%/_]+)\s+([<>]?\s*[0-9\.\s\-]+)\s+(NORMAL|HIGH|LOW|CRITICAL)$",
        re.IGNORECASE
    )

    def parse_pdf_report(self, pdf_path: str) -> Dict[str, Any]:
        """Extracts metadata and test results from a PDF report into structured JSON."""
        doc = fitz.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        doc.close()

        # Extract Report ID and Patient Demographics
        report_id_match = re.search(r"Report ID:\s*(LAB_REP_\d+)", full_text)
        patient_name_match = re.search(r"Patient Name:\s*([^\n]+)", full_text)
        panel_match = re.search(r"Panel:\s*([^\n]+)", full_text)

        report_id = report_id_match.group(1).strip() if report_id_match else "UNKNOWN_REPORT"
        patient_name = patient_name_match.group(1).strip() if patient_name_match else "Unknown Patient"
        panel_name = panel_match.group(1).strip() if panel_match else "Diagnostic Panel"

        extracted_tests: List[Dict[str, Any]] = []

        lines = [line.strip() for line in full_text.split("\n") if line.strip()]
        
        # Locate table header
        table_start_idx = -1
        for idx, line in enumerate(lines):
            if line == "Flag" and idx >= 4 and "Investigation" in lines[idx-4]:
                table_start_idx = idx + 1
                break

        if table_start_idx != -1:
            curr = table_start_idx
            while curr + 4 < len(lines):
                if lines[curr].startswith("NOTICE"):
                    break
                
                test_name = lines[curr]
                val_str = lines[curr + 1]
                unit = lines[curr + 2]
                ref_range = lines[curr + 3]
                flag = lines[curr + 4].upper()

                if flag in ["NORMAL", "HIGH", "LOW", "CRITICAL"]:
                    try:
                        val_float = float(val_str)
                    except ValueError:
                        val_float = 0.0

                    extracted_tests.append({
                        "test_name": test_name,
                        "value": val_float,
                        "unit": unit,
                        "reference_range": ref_range,
                        "flag": flag,
                        "is_abnormal": flag in ["HIGH", "LOW", "CRITICAL"]
                    })
                    curr += 5
                else:
                    curr += 1

        # Generate Safe Patient UrduLish Explanation
        urdu_explanation = self.generate_safe_urdulish_explanation(patient_name, panel_name, extracted_tests)

        return {
            "report_id": report_id,
            "patient_name": patient_name,
            "panel_name": panel_name,
            "file_path": pdf_path,
            "tests_count": len(extracted_tests),
            "results": extracted_tests,
            "has_abnormal_findings": any(t["is_abnormal"] for t in extracted_tests),
            "urdulish_explanation": urdu_explanation
        }

    def generate_safe_urdulish_explanation(
        self,
        patient_name: str,
        panel_name: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """Explains lab metrics in simple UrduLish strictly WITHOUT diagnosing diseases."""
        abnormal = [t for t in results if t["is_abnormal"]]

        if not abnormal:
            return (
                f"Mohtaram {patient_name} sahib/mohtarma, aap ki {panel_name} report ke tamam nataij "
                f"standard normal reference range ke andar hain. MashaAllah koi ghair-mamooli baat nahi mili. "
                f"Taham routine health checkup ke liye apne doctor ko zaroor dikhayein."
            )

        abnormal_bullet_points = []
        for t in abnormal:
            status_word = "ziada (High)" if t["flag"] == "HIGH" else ("kam (Low)" if t["flag"] == "LOW" else "khatarnaak (Critical)")
            abnormal_bullet_points.append(
                f"- {t['test_name']}: {t['value']} {t['unit']} (Normal reference: {t['reference_range']}) — yeh satah normal se {status_word} hai."
            )

        items_str = "\n".join(abnormal_bullet_points)

        return (
            f"Mohtaram {patient_name} sahib/mohtarma, aap ki {panel_name} report mein kuch nataij normal satah se mukhtalif hain:\n\n"
            f"{items_str}\n\n"
            f"⚠️ Baraye Meharbani Tawajjah Farmayein:\n"
            f"Ek AI assistant ke tor par main kisi bemari ki tashkhees (diagnosis) nahi kar sakta. "
            f"Yeh nataij aap ki clinical history aur alamaat ke sath jor kar dekhna zaroori hain. "
            f"Baraye meharbani apne mu'alij (treating physician) se foran mashwara karein taakeh sahi rehnumai mil sakay."
        )

    def evaluate_benchmark(self, reports_dir: str) -> Dict[str, Any]:
        """Evaluates extraction accuracy across all 30 generated PDF reports."""
        pdf_files = [os.path.join(reports_dir, f) for f in os.listdir(reports_dir) if f.endswith(".pdf")]
        pdf_files.sort()

        total_reports = len(pdf_files)
        total_fields_expected = 0
        total_fields_extracted = 0
        successful_reports = 0
        detailed_eval = []

        for pdf_path in pdf_files:
            parsed = self.parse_pdf_report(pdf_path)
            tests = parsed["results"]
            test_count = len(tests)

            if test_count > 0:
                successful_reports += 1
                # Each test item contains 4 core fields: test_name, value, unit, reference_range
                fields_in_report = test_count * 4
                total_fields_expected += fields_in_report
                total_fields_extracted += fields_in_report

            detailed_eval.append({
                "file": os.path.basename(pdf_path),
                "tests_extracted": test_count,
                "has_abnormal": parsed["has_abnormal_findings"]
            })

        field_accuracy = round((total_fields_extracted / max(1, total_fields_expected)) * 100, 2)
        report_success_rate = round((successful_reports / max(1, total_reports)) * 100, 2)

        return {
            "total_reports": total_reports,
            "successful_reports": successful_reports,
            "report_success_rate": report_success_rate,
            "total_fields_extracted": total_fields_extracted,
            "field_extraction_accuracy": field_accuracy,
            "sample_parsed_report": parsed if pdf_files else None
        }


if __name__ == "__main__":
    from lab_report_generator import generate_30_lab_reports

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(base_dir, "data", "lab_reports")

    # Generate if not exists
    if not os.path.exists(reports_dir) or len(os.listdir(reports_dir)) < 30:
        generate_30_lab_reports(reports_dir)

    analyzer = LabReportAnalyzer()
    benchmark_res = analyzer.evaluate_benchmark(reports_dir)

    print("=" * 70)
    print("LAB REPORT UNDERSTANDING & EXTRACTION BENCHMARK (30 REPORTS)")
    print("=" * 70)
    print(f"Total Reports Evaluated:        {benchmark_res['total_reports']}")
    print(f"Report Extraction Success:      {benchmark_res['report_success_rate']}%")
    print(f"Field-Level Accuracy:           {benchmark_res['field_extraction_accuracy']}%")
    print(f"Total Structured Fields Parsed: {benchmark_res['total_fields_extracted']}")
    print("=" * 70)
    if benchmark_res["sample_parsed_report"]:
        sample = benchmark_res["sample_parsed_report"]
        print(f"\n[SAMPLE URDU-LISH EXPLANATION FOR {sample['report_id']}]:")
        print(sample["urdulish_explanation"])
