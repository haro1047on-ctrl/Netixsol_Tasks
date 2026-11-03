"""Enterprise AI Property Valuation & Lead Scoring Dashboard (Week 8 - Day 4 Task 3).

Interactive Streamlit Application featuring:
1. Property Price Prediction Form with Range & Verdict
2. Lead Scoring & Triage Desk with Hot/Warm/Cold badges
3. SHAP Explainability & Rationale Lab
4. Market Insights & EDA Page (Day 1 Charts)
5. Interactive UrduLish AI Sales Assistant Chat Panel
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

# Configure system paths
CURRENT_DIR = Path(__file__).resolve().parent
SRC_DIR = CURRENT_DIR / "src"
WEEK8_DIR = CURRENT_DIR.parent
DAY1_DIR = WEEK8_DIR / "Day1"
DAY2_SRC = WEEK8_DIR / "Day2" / "src"
DAY3_SRC = WEEK8_DIR / "Day3" / "src"
DAY3_REPORTS = WEEK8_DIR / "Day3" / "reports"

for p in [str(SRC_DIR), str(DAY2_SRC), str(DAY3_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from agent import chat_with_assistant, get_market_statistics
from guardrails import LEGAL_DISCLAIMER
from valuation_inference import PropertyValuationEngine, format_pakistani_currency
from lead_inference import LeadScoringEngine

# Page configuration
st.set_page_config(
    page_title="AI Real Estate Intelligence Hub",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background: #F3F4F6;
        padding: 1.2rem;
        border-radius: 10px;
        border-left: 5px solid #2563EB;
        margin-bottom: 1rem;
    }
    .badge-hot {
        background-color: #FEE2E2;
        color: #B91C1C;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        border: 1px solid #FCA5A5;
    }
    .badge-warm {
        background-color: #FEF3C7;
        color: #B45309;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        border: 1px solid #FCD34D;
    }
    .badge-cold {
        background-color: #DBEAFE;
        color: #1D4ED8;
        padding: 4px 10px;
        border-radius: 20px;
        font-weight: 700;
        border: 1px solid #93C5FD;
    }
    .disclaimer-box {
        background: #FFFBEB;
        border: 1px solid #FDE68A;
        padding: 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        color: #92400E;
        margin-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def load_engines():
    p_engine = PropertyValuationEngine()
    l_engine = LeadScoringEngine()
    return p_engine, l_engine


@st.cache_data
def load_sample_leads():
    leads_path = DAY1_DIR / "data" / "processed" / "cleaned_leads.csv"
    if leads_path.exists():
        df = pd.read_csv(leads_path)
        return df.head(150)
    return pd.DataFrame()


@st.cache_data
def get_scored_leads_table(_lead_engine):
    leads_df = load_sample_leads()
    if leads_df.empty or _lead_engine is None:
        return pd.DataFrame()

    scored_records = []
    for idx, row in leads_df.iterrows():
        raw_obj = row.get("objection_raised")
        clean_obj = "None" if (pd.isna(raw_obj) or str(raw_obj).strip().lower() in ["nan", "none", "null", ""]) else str(raw_obj).strip()
        lead_in = {
            "client_name": str(row.get("client_name") or f"Lead-{idx}"),
            "preferred_city": str(row.get("preferred_city") or "Lahore"),
            "budget_pkr": float(row.get("budget_pkr") if pd.notna(row.get("budget_pkr")) else 15000000.0),
            "lead_source": str(row.get("lead_source") or "WhatsApp"),
            "number_of_calls": int(row.get("number_of_calls") if pd.notna(row.get("number_of_calls")) else 2),
            "avg_call_duration_mins": float(row.get("avg_call_duration_mins") if pd.notna(row.get("avg_call_duration_mins")) else 2.5),
            "response_time_hours": float(row.get("response_time_hours") if pd.notna(row.get("response_time_hours")) else 1.0),
            "visit_booked": str(row.get("visit_booked") or "No"),
            "days_since_first_contact": int(row.get("days_since_first_contact") if pd.notna(row.get("days_since_first_contact")) else 1),
            "objection_raised": clean_obj,
        }
        res = _lead_engine.score_lead(lead_in, explain=False)
        scored_records.append({
            "Lead Name": lead_in["client_name"],
            "Priority": res["tier"],
            "Badge": res["badge"],
            "Score": res["conversion_probability"],
            "Probability": res["conversion_pct"],
            "Persona": res["customer_persona"],
            "SLA": res["sla"],
            "City": lead_in["preferred_city"],
            "Budget": format_pakistani_currency(lead_in["budget_pkr"]),
            "Source": lead_in["lead_source"],
            "Visit Booked": lead_in["visit_booked"],
        })
    return pd.DataFrame(scored_records).sort_values(by="Score", ascending=False)


try:
    prop_engine, lead_engine = load_engines()
except Exception as e:
    st.error(f"Error loading models: {e}")
    prop_engine, lead_engine = None, None

# Sidebar Navigation
st.sidebar.image("https://img.icons8.com/color/96/real-estate.png", width=70)
st.sidebar.title("Real Estate Hub")
st.sidebar.caption("Week 8 Capstone Platform • Production ML")

page = st.sidebar.radio(
    "Navigation",
    [
        "🏠 Property Valuation",
        "🔥 Lead Scoring & Triage",
        "🔍 SHAP Explainability",
        "📈 Market Insights (EDA)",
        "💬 UrduLish AI Assistant",
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Active Models:**")
st.sidebar.markdown("• CatBoost Regressor ($R^2=0.988$)")
st.sidebar.markdown("• LightGBM Classifier (PR-AUC 0.562)")
st.sidebar.markdown("• K-Means Personas ($k=4$)")
st.sidebar.markdown("• SHAP TreeExplainers")


# ===========================================================================
# TAB 1: PROPERTY VALUATION
# ===========================================================================
if page == "🏠 Property Valuation":
    st.markdown('<div class="main-title">AI Property Valuation & Fair Market Pricing</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Predict objective market prices in PKR with quantile confidence intervals and automated market verdicts.</div>', unsafe_allow_html=True)

    col_in1, col_in2 = st.columns([1, 1])

    with col_in1:
        st.subheader("Listing Specifications")
        city = st.selectbox("Metropolitan City", ["Lahore", "Islamabad", "Karachi", "Rawalpindi", "Faisalabad"], index=0)
        society = st.text_input("Society / Sector", value="DHA Phase 5")
        ptype = st.selectbox("Property Type", ["House", "Flat", "Upper Portion", "Lower Portion", "Farmhouse", "Penthouse"], index=0)
        plot_size = st.number_input("Plot Size in Marla (1 Kanal = 20 Marla)", min_value=1.0, max_value=80.0, value=10.0, step=1.0)
        bedrooms = st.slider("Bedrooms", min_value=1, max_value=10, value=4)
        bathrooms = st.slider("Bathrooms", min_value=1, max_value=10, value=4)

    with col_in2:
        st.subheader("Attributes & Market Asking Price")
        age_years = st.slider("Property Age (Years)", min_value=0.0, max_value=35.0, value=2.0, step=0.5)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            is_corner = st.selectbox("Corner Plot?", ["No", "Yes"])
        with col_c2:
            is_park = st.selectbox("Park Facing?", ["No", "Yes"])
        amenities = st.multiselect(
            "Amenities Present",
            ["Backup Generator", "Solar System", "Gated Security", "Servant Quarter", "Lawn", "Dedicated Parking"],
            default=["Gated Security", "Dedicated Parking"]
        )
        amenities_str = ", ".join(amenities)
        listed_price = st.number_input("Seller Asking / Listed Price in PKR (Optional, for Verdict)", min_value=0.0, value=48000000.0, step=1000000.0)

    if st.button("Calculate Fair Market Valuation 🚀", type="primary", use_container_width=True):
        if prop_engine:
            prop_data = {
                "city": city,
                "area_society": society,
                "property_type": ptype,
                "plot_size_marla": plot_size,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "age_years": age_years,
                "is_corner": is_corner,
                "is_park_facing": is_park,
                "amenities": amenities_str,
            }
            res = prop_engine.evaluate_property(prop_data, listed_price_pkr=listed_price if listed_price > 0 else None)

            st.markdown("---")
            res_col1, res_col2, res_col3 = st.columns(3)

            with res_col1:
                st.metric("Fair Market Value", res["predicted_price_formatted"])
            with res_col2:
                st.metric("Expected Range (10th - 90th %ile)", f"{res['lower_range_formatted']} – {res['upper_range_formatted']}")
            with res_col3:
                v = res["verdict"]
                if "Underpriced" in v:
                    st.success(f"🏷️ Verdict: {v}")
                elif "Overpriced" in v:
                    st.error(f"🏷️ Verdict: {v} (+{res['variance_pct']}%)")
                else:
                    st.info(f"🏷️ Verdict: {v}")

            st.markdown("### 💬 Sales Agent Consultation Rationale")
            st.info(f"**English:** {res['english_summary']}\n\n**UrduLish:** {res['urdulish_summary']}")
            st.markdown(f'<div class="disclaimer-box">⚠️ {LEGAL_DISCLAIMER}</div>', unsafe_allow_html=True)


# ===========================================================================
# TAB 2: LEAD SCORING & TRIAGE DESK
# ===========================================================================
elif page == "🔥 Lead Scoring & Triage":
    st.markdown('<div class="main-title">Inbound Lead Scoring & Priority Triage Desk</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Prioritize incoming inquiries to identify the hot prospects who convert, backed by ML and personas.</div>', unsafe_allow_html=True)

    if lead_engine:
        scored_df = get_scored_leads_table(lead_engine)
        if not scored_df.empty:
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            hot_count = int(sum(scored_df["Priority"] == "Hot"))
            warm_count = int(sum(scored_df["Priority"] == "Warm"))
            cold_count = int(sum(scored_df["Priority"] == "Cold"))
            top_20_prob = float(scored_df.head(int(len(scored_df) * 0.2))["Score"].mean())

            with col_m1:
                st.metric("Total Inbound Leads", len(scored_df))
            with col_m2:
                st.metric("🔥 Hot Priority (Call in 1h)", hot_count)
            with col_m3:
                st.metric("🌤 Warm Leads (Call in 24h)", warm_count)
            with col_m4:
                st.metric("🎯 Top-20% Mean Conversion", f"{top_20_prob:.1%}")

            st.markdown("### Ranked Lead Pipeline")
            tier_filter = st.multiselect("Filter by Priority Tier", ["Hot", "Warm", "Cold"], default=["Hot", "Warm", "Cold"])
            filtered_df = scored_df[scored_df["Priority"].isin(tier_filter)]
            st.dataframe(filtered_df, use_container_width=True, height=360)

        st.markdown("---")
        st.markdown("### 🎯 Score Single Prospect (Interactive Triage)")
        with st.form("single_lead_form"):
            c_l1, c_l2, c_l3 = st.columns(3)
            with c_l1:
                c_name = st.text_input("Client / Caller Name", "Kamran Tariq")
                c_city = st.selectbox("Preferred City", ["Lahore", "Islamabad", "Karachi", "Rawalpindi", "Faisalabad", "Peshawar"])
                c_budget = st.number_input("Budget (PKR)", value=25000000, step=1000000, min_value=1000000)
            with c_l2:
                c_source = st.selectbox("Lead Source", ["WhatsApp", "Zameen", "Facebook", "Direct Call", "Website"])
                c_calls = st.slider("Number of Inbound/Outbound Calls", 1, 10, 3)
                c_duration = st.slider("Avg Call Duration (minutes)", 0.5, 15.0, 4.5, 0.5)
            with c_l3:
                c_resp_time = st.slider("First Response Latency (hours)", 0.1, 24.0, 0.5, 0.5)
                c_visit = st.selectbox("Visit Booked On-Site?", ["Yes", "No"])
                c_objection = st.selectbox(
                    "Primary Objection Raised",
                    ["None", "Price too high", "Low trust in scheme/NOC", "Location too far", "Waiting for family approval"]
                )

            score_btn = st.form_submit_button("⚡ Score Prospect & Recommend Action")

        if score_btn:
            lead_query = {
                "client_name": c_name,
                "preferred_city": c_city,
                "budget_pkr": float(c_budget),
                "lead_source": c_source,
                "number_of_calls": int(c_calls),
                "avg_call_duration_mins": float(c_duration),
                "response_time_hours": float(c_resp_time),
                "visit_booked": c_visit,
                "days_since_first_contact": 2,
                "objection_raised": c_objection,
            }
            lead_res = lead_engine.score_lead(lead_query, explain=True)

            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.metric("Conversion Probability", lead_res["conversion_pct"])
            with sc2:
                st.metric("Priority Tier & SLA", f"{lead_res['tier']} ({lead_res['sla']})")
            with sc3:
                st.metric("Customer Persona", lead_res["customer_persona"])

            st.markdown("#### 📋 Recommended Next Best Action")
            st.success(f"**English:** {lead_res['next_best_action_en']}\n\n**UrduLish:** {lead_res['next_best_action_ur']}")

            st.markdown("#### 🔍 SHAP Key Decision Drivers")
            st.info(f"**English:** {lead_res['explanation_en']}\n\n**UrduLish:** {lead_res['explanation_ur']}")


# ===========================================================================
# TAB 3: SHAP EXPLAINABILITY
# ===========================================================================
elif page == "🔍 SHAP Explainability":
    st.markdown('<div class="main-title">Explainable AI (XAI) & SHAP Transparency Lab</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Inspect global impact plots and local waterfall drivers in fluent UrduLish and English.</div>', unsafe_allow_html=True)

    shap_tab1, shap_tab2 = st.tabs(["🏡 Property Valuation SHAP", "🎯 Lead Scoring SHAP"])

    with shap_tab1:
        st.subheader("Global & Local Drivers for Property Pricing")
        fig1_path = DAY3_REPORTS / "figures" / "07_property_shap_global_summary.png"
        fig2_path = DAY3_REPORTS / "figures" / "08_property_shap_local_waterfall.png"

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            if fig1_path.exists():
                st.image(str(fig1_path), caption="Figure 07: Global SHAP Feature Importance (Property CatBoost)")
            else:
                st.info("Global summary plot generated during Day 3 runner.")
        with col_p2:
            if fig2_path.exists():
                st.image(str(fig2_path), caption="Figure 08: Local SHAP Waterfall Attribution (Single Property Example)")
            else:
                st.info("Local waterfall plot generated during Day 3 runner.")

        st.markdown("""
        **Key Valuation Insights:**
        - `plot_size_marla` and `area_society_clean` drive over **72% of total price variation**.
        - Brand new builds command an immediate **18% uplift**, while older homes (>15 years) receive structural depreciation deductions.
        """)

    with shap_tab2:
        st.subheader("Global & Local Drivers for Lead Conversion")
        fig3_path = DAY3_REPORTS / "figures" / "05_lead_shap_global_summary.png"
        fig4_path = DAY3_REPORTS / "figures" / "06_lead_shap_local_waterfall.png"

        col_l1, col_l2 = st.columns(2)
        with col_l1:
            if fig3_path.exists():
                st.image(str(fig3_path), caption="Figure 05: Global SHAP Summary (Lead Scoring Classifier)")
        with col_l2:
            if fig4_path.exists():
                st.image(str(fig4_path), caption="Figure 06: Local Waterfall Explaining Hot vs Cold Lead")

        st.markdown("""
        **Key Conversion Insights:**
        - Scheduled on-site visits (`visit_booked`) and call engagement duration are the strongest positive signals for conversion.
        - Unanswered inquiries (>6 hours latency) and unresolved price/trust objections sharply suppress purchase probability.
        """)


# ===========================================================================
# TAB 4: MARKET INSIGHTS & EDA
# ===========================================================================
elif page == "📈 Market Insights (EDA)":
    st.markdown('<div class="main-title">Pakistani Real Estate Market Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Foundational Exploratory Data Analysis & Business Insights from Day 1.</div>', unsafe_allow_html=True)

    fig_dir = DAY1_DIR / "reports" / "figures"

    c1, c2 = st.columns(2)
    with c1:
        f1 = fig_dir / "01_price_distribution_raw_vs_log.png"
        if f1.exists():
            st.image(str(f1), caption="01: Raw vs Log-transformed Property Price Distribution")
            st.caption("💡 Raw prices exhibit heavy skewness; log transformation normalizes variance.")

        f3 = fig_dir / "03_correlation_heatmap.png"
        if f3.exists():
            st.image(str(f3), caption="03: Feature Correlation Heatmap")
            st.caption("💡 Covered area and plot size dominate price; call engagement correlates with conversion.")

        f5 = fig_dir / "05_conversion_rate_by_source_purpose.png"
        if f5.exists():
            st.image(str(f5), caption="05: Conversion Rate by Lead Source & Purpose")
            st.caption("💡 WhatsApp and Inbound Voice inquiries convert at 3x higher rates than Facebook paid ads.")

    with c2:
        f2 = fig_dir / "02_price_per_marla_by_city_society.png"
        if f2.exists():
            st.image(str(f2), caption="02: Price Per Marla across Major Metropolitan Societies")
            st.caption("💡 Sector F-7 (Islamabad) and Clifton (Karachi) command over 50-65 Lac/Marla.")

        f4 = fig_dir / "04_effect_bedrooms_age_corner.png"
        if f4.exists():
            st.image(str(f4), caption="04: Effect of Construction Age, Bedrooms and Corner Plots")
            st.caption("💡 Brand new homes yield an 18% premium; corner+park plots add 16% uplift.")

        f6 = fig_dir / "06_class_imbalance_leads.png"
        if f6.exists():
            st.image(str(f6), caption="06: Class Imbalance Distribution in CRM Leads (25.2% Converted)")
            st.caption("💡 Class imbalance necessitates PR-AUC and cost-weighted loss optimization.")


# ===========================================================================
# TAB 5: URDULISH AI SALES ASSISTANT
# ===========================================================================
elif page == "💬 UrduLish AI Assistant":
    st.markdown('<div class="main-title">UrduLish AI Real Estate Sales Assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Chat with our LangGraph agent in fluent UrduLish or English. All figures are backed by verified ML tools.</div>', unsafe_allow_html=True)

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": (
                    "Assalam-o-Alaikum! Mein aapka AI Real Estate Assistant hoon. "
                    "Aap mujh se kisi bhi property ki fair market value, lead conversion score, "
                    "ya area ke rates ke baray mein pooch sakte hain.\n\n"
                    "Misal ke tor par: *'DHA Phase 6 mein 1 kanal, 5 saal purana ghar, kitne ka jana chahiye?'*"
                )
            }
        ]

    # Quick Prompts
    st.markdown("**Quick Prompts:**")
    quick_cols = st.columns(3)
    with quick_cols[0]:
        if st.button("🏡 DHA Phase 6: 1 Kanal House Price?"):
            st.session_state.messages.append({
                "role": "user",
                "content": "DHA Phase 6 mein 1 kanal, 5 saal purana ghar, kitne ka jana chahiye?"
            })
            with st.spinner("Calculating fair value..."):
                reply = chat_with_assistant("DHA Phase 6 mein 1 kanal, 5 saal purana ghar, kitne ka jana chahiye?")
                st.session_state.messages.append({"role": "assistant", "content": reply})
    with quick_cols[1]:
        if st.button("🔥 Score High-Intent Inbound Lead"):
            st.session_state.messages.append({
                "role": "user",
                "content": "Ek client ne 4 calls ki hain aur site visit book kiya hai, is lead ka score kya hai?"
            })
            with st.spinner("Scoring lead..."):
                reply = chat_with_assistant("Ek client ne 4 calls ki hain aur site visit book kiya hai, is lead ka score kya hai?")
                st.session_state.messages.append({"role": "assistant", "content": reply})
    with quick_cols[2]:
        if st.button("📊 DHA Lahore Marla Rates"):
            st.session_state.messages.append({
                "role": "user",
                "content": "DHA Lahore mein average per marla rate kya chal raha hai?"
            })
            with st.spinner("Pulling market stats..."):
                reply = chat_with_assistant("DHA Lahore mein average per marla rate kya chal raha hai?")
                st.session_state.messages.append({"role": "assistant", "content": reply})

    # Render message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Type your question in UrduLish or English..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Soch raha hoon..."):
                response = chat_with_assistant(prompt, chat_history=st.session_state.messages[:-1])
                st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
