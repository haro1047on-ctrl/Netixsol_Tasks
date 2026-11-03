"""Week 8 Day 3: Production Lead Scoring & Consultation Inference Engine.

Integrates:
1. Feature preprocessor & pipeline transformation
2. Best tuned LightGBM/CatBoost classification model
3. Priority Tier Assignment:
   - 🔥 Hot (call within 1 hour)
   - 🌤 Warm (call within 24 hours)
   - ❄️ Cold (add to automated follow-up drip)
4. Unsupervised Customer Persona classification (K-Means)
5. Local SHAP Attribution and Natural Language Explainability (UrduLish + English)
6. Next Best Action (NBA) guidance for sales agents
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import joblib
import numpy as np
import pandas as pd
import shap

DAY3_DIR = Path(__file__).resolve().parent.parent
WEEK8_DIR = DAY3_DIR.parent
MODELS_DIR = DAY3_DIR / "models"
DAY1_DIR = WEEK8_DIR / "Day1"
DAY1_SRC = DAY1_DIR / "src"

if str(DAY1_SRC) not in sys.path:
    sys.path.insert(0, str(DAY1_SRC))
if str(DAY3_DIR / "src") not in sys.path:
    sys.path.insert(0, str(DAY3_DIR / "src"))

from shap_explainers import (
    generate_lead_plain_language_reasons,
    LEAD_FEATURE_FRIENDLY_NAMES
)

# City median benchmarks for budget-to-market ratio
CITY_MEDIAN_PRICES = {
    "Karachi": 22000000.0,
    "Lahore": 20000000.0,
    "Islamabad": 25000000.0,
    "Rawalpindi": 15000000.0,
    "Faisalabad": 12000000.0,
    "Peshawar": 13000000.0,
}


class LeadScoringEngine:
    """Production Inference Engine for Lead Scoring, Segmentation, and Consultation."""

    def __init__(
        self,
        model_payload_path: Optional[Path] = None,
        personas_payload_path: Optional[Path] = None,
    ):
        if model_payload_path is None:
            model_payload_path = MODELS_DIR / "best_lead_scoring_model.joblib"
        if personas_payload_path is None:
            personas_payload_path = MODELS_DIR / "kmeans_customer_personas.joblib"

        if not model_payload_path.exists():
            raise FileNotFoundError(f"Model payload not found at {model_payload_path}. Run training first.")

        payload = joblib.load(model_payload_path)
        self.model = payload["model"]
        self.preprocessor = payload["preprocessor"]
        self.feature_names = payload["feature_names"]
        self.optimal_threshold = payload.get("optimal_threshold", 0.38)
        self.model_name = payload.get("model_name", "Tuned_Classifier")

        # Initialize SHAP TreeExplainer
        self.explainer = shap.TreeExplainer(self.model)

        # Load K-Means personas
        if personas_payload_path.exists():
            self.persona_artifacts = joblib.load(personas_payload_path)
        else:
            self.persona_artifacts = None

        # Sanitize OneHotEncoder categories_ to prevent NumPy 2.x isnan ufunc crashes
        self._sanitize_preprocessor_categories()

    def _sanitize_preprocessor_categories(self):
        """Sanitizes OneHotEncoder categories_ to prevent NumPy 2.x isnan ufunc crashes on object arrays."""
        if not hasattr(self, "preprocessor"):
            return

        def _clean_encoder(enc):
            if hasattr(enc, "categories_"):
                for i in range(len(enc.categories_)):
                    cat_arr = enc.categories_[i]
                    enc.categories_[i] = np.array(
                        ["None" if (pd.isna(x) or str(x).lower() == "nan") else str(x) for x in cat_arr],
                        dtype=object
                    )

        if hasattr(self.preprocessor, "transformers_"):
            for name, trans, cols in self.preprocessor.transformers_:
                _clean_encoder(trans)
                if hasattr(trans, "named_steps"):
                    for step_name, step in trans.named_steps.items():
                        _clean_encoder(step)

    def _engineer_lead_features(self, lead_data: Dict[str, Any]) -> pd.DataFrame:
        """Applies Week 8 Day 1 domain feature engineering logic to raw incoming lead."""
        d = {k: v for k, v in lead_data.items() if v is not None}

        def _clean_str(val, default):
            if val is None or pd.isna(val) or str(val).strip().lower() in ["nan", "none", "null", ""]:
                return default
            return str(val).strip()

        # Defaults
        calls = int(d.get("number_of_calls") or 1)
        call_dur = float(d.get("avg_call_duration_mins") or 2.0)
        resp_time = float(d.get("response_time_hours") or 1.0)
        days = int(d.get("days_since_first_contact") or 1)
        budget = float(d.get("budget_pkr") or 15000000.0)

        city = _clean_str(d.get("preferred_city"), "Lahore")
        lead_source = _clean_str(d.get("lead_source"), "WhatsApp")
        property_type = _clean_str(d.get("property_type"), "House")
        purpose = _clean_str(d.get("purpose"), "Buy")
        visit_booked = _clean_str(d.get("visit_booked"), "No")
        objection = _clean_str(d.get("objection_raised"), "None")

        # Derived metrics
        lead_engagement = calls * call_dur
        interaction_intensity = round(calls / (days + 1), 3)

        if resp_time < 0.25:
            speed_cat = "Immediate (<15m)"
        elif resp_time <= 1.0:
            speed_cat = "Fast (15-60m)"
        elif resp_time <= 6.0:
            speed_cat = "Standard (1-6h)"
        else:
            speed_cat = "Slow (>6h)"

        severity_map = {
            "None": 0,
            "Waiting for family approval": 1,
            "Location too far": 2,
            "Price too high": 4,
            "Low trust in scheme/NOC": 4
        }
        objection_score = severity_map.get(objection, 1)

        city_benchmark = CITY_MEDIAN_PRICES.get(city, 20000000.0)
        budget_ratio = round(budget / city_benchmark, 2)

        is_high_intent = 1 if (visit_booked == "Yes" and calls >= 2) else 0

        # Construct single-row DataFrame matching training schema
        row = {
            "budget_pkr": float(budget),
            "lead_source": str(lead_source),
            "preferred_city": str(city),
            "property_type": str(property_type),
            "purpose": str(purpose),
            "number_of_calls": int(calls),
            "avg_call_duration_mins": float(call_dur),
            "response_time_hours": float(resp_time),
            "visit_booked": str(visit_booked),
            "days_since_first_contact": int(days),
            "objection_raised": str(objection),
            "lead_engagement_score": float(lead_engagement),
            "response_speed_category": str(speed_cat),
            "interaction_intensity": float(interaction_intensity),
            "objection_severity_score": int(objection_score),
            "budget_to_market_ratio": float(budget_ratio),
            "is_high_intent": int(is_high_intent),
        }
        df_res = pd.DataFrame([row])
        cat_cols = ["lead_source", "preferred_city", "property_type", "purpose", "response_speed_category", "objection_raised", "visit_booked"]
        for col in cat_cols:
            df_res[col] = df_res[col].astype(str)
        return df_res

    def _determine_customer_persona(self, df_engineered: pd.DataFrame) -> Tuple[str, str]:
        """Classifies the customer into an actionable persona using K-Means clustering."""
        if not self.persona_artifacts:
            return "Standard Inquirer", "Standard customer profile."

        kmeans = self.persona_artifacts["kmeans"]
        scaler = self.persona_artifacts["scaler"]
        persona_map = self.persona_artifacts["persona_map"]

        X_cluster = df_engineered[[
            "budget_pkr", "number_of_calls", "avg_call_duration_mins",
            "response_time_hours", "days_since_first_contact",
            "lead_engagement_score", "budget_to_market_ratio"
        ]].copy()

        X_cluster["is_buy"] = (df_engineered["purpose"] == "Buy").astype(int)
        X_cluster["visit_booked_num"] = (df_engineered["visit_booked"] == "Yes").astype(int)
        X_cluster["is_commercial_or_plot"] = df_engineered["property_type"].isin(["Commercial", "Plot"]).astype(int)

        X_scaled = scaler.transform(X_cluster)
        c_id = int(kmeans.predict(X_scaled)[0])
        persona_name = persona_map.get(c_id, "Qualified Buyer")

        descriptions = {
            "High-Net-Worth / Overseas Investor": "High capital, swift digital decision maker, targeting prime commercial/luxury assets.",
            "Serious First-Time Homebuyer": "High engagement, visit booked, seeking residential security and NOC clarity.",
            "Budget Urban Renter": "Price-conscious, fast rental turnaround, high sensitivity to location and monthly lease.",
            "Casual Window Shopper / Speculator": "Browsing stage, high response delay, needs automated nurturing and proof of value."
        }
        return persona_name, descriptions.get(persona_name, "Verified real estate prospect.")

    def score_lead(self, lead_data: Dict[str, Any], explain: bool = True) -> Dict[str, Any]:
        """Performs full end-to-end scoring, explainability, and action recommendation for a single lead."""
        df_eng = self._engineer_lead_features(lead_data)
        X_trans = self.preprocessor.transform(df_eng)

        # Predict probability
        proba = float(self.model.predict_proba(X_trans)[0, 1])

        # Priority Tiers
        if proba >= 0.65:
            tier = "Hot"
            badge = "[HOT]"
            sla = "Call within 1 hour"
            nba = "Assign Senior Closer. Contact immediately to lock property viewing date."
            nba_ur = "Senior agent ko foran assign karein. 1 ghante mein call karke visit finalize karein."
        elif proba >= 0.35:
            tier = "Warm"
            badge = "[WARM]"
            sla = "Call within 24 hours"
            nba = "Send 3 matched property brochures on WhatsApp. Address budget and location concerns."
            nba_ur = "WhatsApp par 3 munasib options bhejein aur budget/location par mashwara dein."
        else:
            tier = "Cold"
            badge = "[COLD]"
            sla = "Add to automated nurture campaign"
            nba = "Enroll in weekly automated newsletter drip. Re-engage after 14 days."
            nba_ur = "Automated WhatsApp drip campaign mein shamil karein. 2 haftay baad dobara rabta karein."

        # Customer Persona
        persona_name, persona_desc = self._determine_customer_persona(df_eng)

        # Local SHAP Explanation (optional for high-throughput scoring)
        if explain:
            shap_vals = self.explainer(X_trans).values[0]
            reasons = generate_lead_plain_language_reasons(
                shap_vals_row=shap_vals,
                feature_names=self.feature_names,
                tier=tier,
                probability=proba,
                top_n=3
            )
        else:
            reasons = {
                "explanation_en": f"Lead categorized as {tier} priority based on engagement signals.",
                "explanation_ur": f"Engagement aur call signals ki bunyad par lead ko {tier} priority di gayi hai.",
                "top_positive_features": [],
                "top_negative_features": []
            }

        client_name = lead_data.get("client_name", "Lead Prospect")

        result = {
            "client_name": client_name,
            "conversion_probability": round(proba, 4),
            "conversion_pct": f"{proba * 100:.1f}%",
            "tier": tier,
            "badge": badge,
            "sla": sla,
            "customer_persona": persona_name,
            "persona_description": persona_desc,
            "next_best_action_en": nba,
            "next_best_action_ur": nba_ur,
            "explanation_en": reasons["explanation_en"],
            "explanation_ur": reasons["explanation_ur"],
            "top_positive_drivers": reasons["top_positive_features"],
            "top_negative_drivers": reasons["top_negative_features"],
            "model_version": self.model_name,
        }

        # Formatted consultation statement
        result["consultation_statement"] = (
            f"{badge} {client_name} (Conversion Probability: {result['conversion_pct']})\n"
            f"- Persona: {persona_name}\n"
            f"- SLA: {sla}\n"
            f"- Reason (UrduLish): {reasons['explanation_ur']}\n"
            f"- Next Best Action: {nba}"
        )

        return result
