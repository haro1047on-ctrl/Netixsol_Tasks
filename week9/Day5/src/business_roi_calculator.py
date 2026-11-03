"""City Care Clinics - Healthcare Operational ROI & Impact Model.

Week 9 Capstone Project: Multi-Agent AI Clinic Assistant for Healthcare
Day 5: Evaluation, Red-Teaming, Deployment & Client Handover
Calculates quantifiable operational and financial impact across 5 clinic branches (Lahore & Islamabad):
1. Front-Desk Receptionist Labor Savings (Hours saved/month)
2. No-Show Rate Reduction via Automated WhatsApp Outreach
3. Physician Pre-Encounter Consultation Time Recovery
4. Net Financial ROI (PKR per month)
"""
from __future__ import annotations

import os
import sys
from typing import Any, Dict
from pydantic import BaseModel, Field


class ClinicNetworkProfile(BaseModel):
    total_branches: int = 5
    total_doctors: int = 30
    daily_inquiries: int = 450
    daily_consultations: int = 400
    average_consultation_fee_pkr: int = 2500
    receptionist_hourly_rate_pkr: int = 600
    baseline_no_show_rate: float = 0.28
    ai_assisted_no_show_rate: float = 0.09
    baseline_inquiry_duration_mins: float = 8.5
    ai_inquiry_duration_mins: float = 1.5
    doctor_minutes_saved_per_soap: float = 5.0


class ROIEvaluationReport(BaseModel):
    network_profile: ClinicNetworkProfile
    monthly_front_desk_hours_saved: float
    monthly_front_desk_cost_savings_pkr: float
    monthly_recovered_consultations: int
    monthly_recovered_revenue_pkr: float
    monthly_doctor_hours_saved: float
    net_monthly_economic_value_pkr: float
    operational_efficiency_gain_pct: float


class BusinessROICalculator:
    """Calculates operational and economic returns for City Care Clinics leadership."""

    def __init__(self, profile: Optional[ClinicNetworkProfile] = None):
        self.profile = profile or ClinicNetworkProfile()

    def calculate_impact(self) -> ROIEvaluationReport:
        p = self.profile
        working_days_per_month = 26

        # 1. Front Desk Hours Saved
        mins_saved_per_inquiry = p.baseline_inquiry_duration_mins - p.ai_inquiry_duration_mins
        daily_hours_saved = (p.daily_inquiries * mins_saved_per_inquiry) / 60.0
        monthly_hours_saved = daily_hours_saved * working_days_per_month
        monthly_receptionist_savings_pkr = monthly_hours_saved * p.receptionist_hourly_rate_pkr

        # 2. No-Show Reduction & Recovered Consultations
        no_show_delta = p.baseline_no_show_rate - p.ai_assisted_no_show_rate  # 0.28 - 0.09 = 0.19
        daily_recovered_visits = int(p.daily_consultations * no_show_delta)
        monthly_recovered_visits = daily_recovered_visits * working_days_per_month
        monthly_recovered_revenue_pkr = monthly_recovered_visits * p.average_consultation_fee_pkr

        # 3. Doctor Consultation Time Saved via Pre-Visit SOAP Briefs
        daily_doc_mins_saved = p.daily_consultations * p.doctor_minutes_saved_per_soap
        monthly_doc_hours_saved = (daily_doc_mins_saved / 60.0) * working_days_per_month

        # 4. Total Net Economic Value (Monthly)
        total_economic_value_pkr = monthly_receptionist_savings_pkr + monthly_recovered_revenue_pkr
        efficiency_gain = (mins_saved_per_inquiry / p.baseline_inquiry_duration_mins) * 100.0

        return ROIEvaluationReport(
            network_profile=p,
            monthly_front_desk_hours_saved=round(monthly_hours_saved, 1),
            monthly_front_desk_cost_savings_pkr=round(monthly_receptionist_savings_pkr, 2),
            monthly_recovered_consultations=monthly_recovered_visits,
            monthly_recovered_revenue_pkr=round(monthly_recovered_revenue_pkr, 2),
            monthly_doctor_hours_saved=round(monthly_doc_hours_saved, 1),
            net_monthly_economic_value_pkr=round(total_economic_value_pkr, 2),
            operational_efficiency_gain_pct=round(efficiency_gain, 1)
        )
