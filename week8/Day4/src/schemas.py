"""Pydantic Request & Response Schemas with Strict Validation & OOD Checks (Week 8 - Day 4).

Covers:
- Property Valuation inputs & outputs
- Lead Scoring inputs & outputs
- SHAP Explainability requests & responses
- Model Info & Health schemas
- Batch CSV payload schemas
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


VALID_CITIES = ["Lahore", "Islamabad", "Karachi", "Rawalpindi", "Faisalabad", "Peshawar"]
VALID_PROPERTY_TYPES = [
    "House", "Flat", "Upper Portion", "Lower Portion", "Farmhouse", "Penthouse"
]
VALID_LEAD_SOURCES = ["WhatsApp", "Call", "Website", "Facebook"]
VALID_PURPOSES = ["Buy", "Rent", "Invest"]


class PropertyValuationRequest(BaseModel):
    """Input payload for property price prediction."""
    city: str = Field(..., description="Metropolitan city (e.g. Lahore, Islamabad, Karachi)")
    area_society: str = Field(..., description="Residential society or sector (e.g. DHA Phase 5, F-7)")
    property_type: str = Field(default="House", description="Type of property (House, Flat, etc.)")
    plot_size_marla: float = Field(..., gt=0.0, description="Plot size in Marla (1 Kanal = 20 Marla)")
    bedrooms: int = Field(default=4, ge=1, le=15, description="Number of dedicated bedrooms")
    bathrooms: Optional[int] = Field(default=None, ge=1, le=15, description="Number of washrooms")
    age_years: float = Field(default=2.0, ge=0.0, le=50.0, description="Age of construction in years")
    floors: Optional[float] = Field(default=2.0, ge=1.0, le=6.0, description="Total vertical storeys")
    is_corner: Literal["Yes", "No"] = Field(default="No", description="Corner plot flag")
    is_park_facing: Literal["Yes", "No"] = Field(default="No", description="Direct park-facing flag")
    amenities: Optional[str] = Field(
        default="Gated Security, Dedicated Parking",
        description="Comma-separated amenities (Generator, Solar, etc.)"
    )
    distance_to_main_road_km: Optional[float] = Field(default=0.8, ge=0.0, le=30.0)
    distance_to_school_km: Optional[float] = Field(default=1.2, ge=0.0, le=30.0)
    distance_to_hospital_km: Optional[float] = Field(default=2.0, ge=0.0, le=30.0)
    covered_area_sqft: Optional[float] = Field(default=None, gt=0.0, description="Optional covered area in sq ft")
    listed_price_pkr: Optional[float] = Field(
        default=None, gt=0.0, description="Asking/listed price in PKR to generate market verdict"
    )

    @field_validator("city")
    @classmethod
    def validate_city(cls, v: str) -> str:
        clean_v = v.strip().title()
        matched = [c for c in VALID_CITIES if c.lower() == clean_v.lower()]
        if not matched:
            raise ValueError(
                f"Unknown city '{v}'. Supported cities are: {', '.join(VALID_CITIES)}"
            )
        return matched[0]

    @field_validator("plot_size_marla")
    @classmethod
    def validate_plot_size(cls, v: float) -> float:
        if v < 1.0 or v > 80.0:
            raise ValueError(
                f"Out-of-Distribution: Plot size {v} Marla is outside the valid range [1.0, 80.0 Marla] (up to 4 Kanal)."
            )
        return v

    @field_validator("property_type")
    @classmethod
    def validate_property_type(cls, v: str) -> str:
        clean_v = v.strip().title()
        if clean_v not in VALID_PROPERTY_TYPES:
            raise ValueError(
                f"Invalid property type '{v}'. Allowed types: {', '.join(VALID_PROPERTY_TYPES)}"
            )
        return clean_v


class PropertyValuationResponse(BaseModel):
    """Output payload for property valuation prediction."""
    predicted_price_pkr: float
    predicted_price_formatted: str
    lower_range_pkr: float
    lower_range_formatted: str
    upper_range_pkr: float
    upper_range_formatted: str
    listed_price_pkr: Optional[float] = None
    listed_price_formatted: Optional[str] = None
    verdict: str
    variance_pct: float
    english_summary: str
    urdulish_summary: str
    disclaimer: str
    model_version: str


class LeadScoringRequest(BaseModel):
    """Input payload for inbound lead conversion scoring."""
    lead_source: str = Field(default="WhatsApp", description="Acquisition channel")
    budget_pkr: float = Field(..., gt=0.0, description="Customer stated budget in PKR")
    preferred_city: str = Field(default="Lahore", description="Target metropolitan city")
    purpose: str = Field(default="Buy", description="Purpose: Buy, Rent, or Invest")
    number_of_calls: int = Field(default=1, ge=0, le=50, description="Total calls placed")
    avg_call_duration_mins: float = Field(default=2.0, ge=0.0, le=180.0, description="Average call duration in mins")
    response_time_hours: float = Field(default=1.0, ge=0.0, le=168.0, description="Response latency in hours")
    visit_booked: Literal["Yes", "No"] = Field(default="No", description="Whether on-site visit is scheduled")
    days_since_first_contact: int = Field(default=1, ge=0, le=365, description="Lead age in days")
    objection_raised: Optional[str] = Field(default="None", description="Primary friction point noted by agent")

    @field_validator("lead_source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        clean_v = v.strip()
        matched = [s for s in VALID_LEAD_SOURCES if s.lower() == clean_v.lower()]
        if not matched:
            raise ValueError(
                f"Unknown lead source '{v}'. Supported channels: {', '.join(VALID_LEAD_SOURCES)}"
            )
        return matched[0]

    @field_validator("purpose")
    @classmethod
    def validate_purpose(cls, v: str) -> str:
        clean_v = v.strip().title()
        if clean_v not in VALID_PURPOSES:
            raise ValueError(
                f"Invalid purpose '{v}'. Must be one of: {', '.join(VALID_PURPOSES)}"
            )
        return clean_v

    @field_validator("preferred_city")
    @classmethod
    def validate_city(cls, v: str) -> str:
        clean_v = v.strip().title()
        matched = [c for c in VALID_CITIES if c.lower() == clean_v.lower()]
        if not matched:
            raise ValueError(
                f"Unknown city '{v}'. Supported cities are: {', '.join(VALID_CITIES)}"
            )
        return matched[0]


class LeadScoringResponse(BaseModel):
    """Output payload for lead scoring and triage."""
    conversion_probability: float
    probability_percentage: str
    priority_tier: str
    priority_badge: str
    operational_sla: str
    recommended_action: str
    customer_persona: str
    persona_description: str
    explanation_en: str
    explanation_ur: str
    model_version: str


class PropertyExplainRequest(PropertyValuationRequest):
    """Request for property SHAP explainability."""
    top_n: int = Field(default=3, ge=1, le=8, description="Number of top driving factors")


class LeadExplainRequest(LeadScoringRequest):
    """Request for lead scoring SHAP explainability."""
    top_n: int = Field(default=3, ge=1, le=8, description="Number of top driving factors")


class SHAPFeatureImpact(BaseModel):
    feature_name: str
    impact_direction: Literal["Increases", "Decreases"]
    shap_value: float
    friendly_name_en: str
    friendly_name_ur: str


class ExplainResponse(BaseModel):
    """Output payload for SHAP attribution and plain-language reasoning."""
    target_type: Literal["property_price", "lead_conversion"]
    predicted_value: str
    plain_language_en: str
    plain_language_ur: str
    top_positive_features: List[SHAPFeatureImpact]
    top_negative_features: List[SHAPFeatureImpact]
    model_version: str


class HealthResponse(BaseModel):
    """Healthcheck payload."""
    status: str
    timestamp: str
    version: str
    loaded_models: List[str]
    system_status: str


class ModelDetail(BaseModel):
    model_name: str
    version: str
    algorithm: str
    trained_date: str
    key_metrics: Dict[str, Any]
    input_feature_count: int


class ModelInfoResponse(BaseModel):
    """Metadata response for all production models."""
    platform: str
    environment: str
    models: List[ModelDetail]
