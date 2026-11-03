"""LangGraph Real Estate AI Sales Assistant with UrduLish Support (Week 8 - Day 4 Task 2).

Integrates 5 Specialized ML & Database Tools:
1. predict_property_price: Fair market regression + quantile interval + verdict
2. score_lead: Imbalanced classification + priority tier + customer persona
3. explain_prediction: SHAP attribution + bilingual natural language rationale
4. find_comparable_properties: Historical benchmark listings from database
5. get_market_statistics: Micro-market average & median price/marla metrics

Strict Anti-Hallucination Policy:
- The LLM never invents prices. Every figure is produced by validated tools.
- Prompt injection defenses intercept jailbreaks before graph invocation.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Sequence, TypedDict

import numpy as np
import pandas as pd
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

SRC_DIR = Path(__file__).resolve().parent
DAY4_DIR = SRC_DIR.parent
WEEK8_DIR = DAY4_DIR.parent
DAY1_DIR = WEEK8_DIR / "Day1"
DAY2_SRC = WEEK8_DIR / "Day2" / "src"
DAY3_SRC = WEEK8_DIR / "Day3" / "src"
DATA_PATH = DAY1_DIR / "data" / "processed" / "cleaned_properties.csv"

for p in [str(SRC_DIR), str(DAY2_SRC), str(DAY3_SRC)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from guardrails import LEGAL_DISCLAIMER, detect_prompt_injection
from valuation_inference import PropertyValuationEngine, format_pakistani_currency
from lead_inference import LeadScoringEngine

# Singleton Engines
_property_engine: Optional[PropertyValuationEngine] = None
_lead_engine: Optional[LeadScoringEngine] = None
_properties_df: Optional[pd.DataFrame] = None


def get_property_engine() -> PropertyValuationEngine:
    global _property_engine
    if _property_engine is None:
        _property_engine = PropertyValuationEngine()
    return _property_engine


def get_lead_engine() -> LeadScoringEngine:
    global _lead_engine
    if _lead_engine is None:
        _lead_engine = LeadScoringEngine()
    return _lead_engine


def get_properties_database() -> pd.DataFrame:
    global _properties_df
    if _properties_df is None:
        if DATA_PATH.exists():
            _properties_df = pd.read_csv(DATA_PATH)
        else:
            _properties_df = pd.DataFrame()
    return _properties_df


# ---------------------------------------------------------------------------
# 5 Specialized Agent Tools
# ---------------------------------------------------------------------------

@tool
def predict_property_price(
    city: str,
    area_society: str,
    plot_size_marla: float,
    bedrooms: int = 4,
    age_years: float = 2.0,
    property_type: str = "House",
    is_corner: str = "No",
    is_park_facing: str = "No",
    listed_price_pkr: Optional[float] = None
) -> str:
    """Predicts the fair market value of a property in Pakistani Rupees (PKR) using the trained CatBoost model.
    Also returns 10th-90th percentile confidence bounds and Underpriced/Fair/Overpriced verdict.
    """
    engine = get_property_engine()
    prop_data = {
        "city": city,
        "area_society": area_society,
        "plot_size_marla": plot_size_marla,
        "bedrooms": bedrooms,
        "age_years": age_years,
        "property_type": property_type,
        "is_corner": is_corner,
        "is_park_facing": is_park_facing,
    }
    result = engine.evaluate_property(prop_data, listed_price_pkr=listed_price_pkr)
    payload = {
        "predicted_price_pkr": result["predicted_price_pkr"],
        "predicted_price_formatted": result["predicted_price_formatted"],
        "lower_range_formatted": result["lower_range_formatted"],
        "upper_range_formatted": result["upper_range_formatted"],
        "verdict": result["verdict"],
        "english_summary": result["english_summary"],
        "urdulish_summary": result["urdulish_summary"],
        "disclaimer": LEGAL_DISCLAIMER,
    }
    return json.dumps(payload, indent=2)


@tool
def score_lead(
    budget_pkr: float,
    preferred_city: str = "Lahore",
    lead_source: str = "WhatsApp",
    purpose: str = "Buy",
    number_of_calls: int = 2,
    avg_call_duration_mins: float = 3.0,
    response_time_hours: float = 1.0,
    visit_booked: str = "No",
    days_since_first_contact: int = 2,
    objection_raised: str = "None"
) -> str:
    """Evaluates an inbound sales lead to predict deal conversion probability, priority tier (Hot/Warm/Cold),
    customer persona, and operational SLA recommendation.
    """
    engine = get_lead_engine()
    lead_data = {
        "budget_pkr": budget_pkr,
        "preferred_city": preferred_city,
        "lead_source": lead_source,
        "purpose": purpose,
        "number_of_calls": number_of_calls,
        "avg_call_duration_mins": avg_call_duration_mins,
        "response_time_hours": response_time_hours,
        "visit_booked": visit_booked,
        "days_since_first_contact": days_since_first_contact,
        "objection_raised": objection_raised,
    }
    res = engine.score_lead(lead_data)
    payload = {
        "conversion_probability": res["conversion_probability"],
        "conversion_pct": res["conversion_pct"],
        "priority_tier": res["tier"],
        "priority_badge": res["badge"],
        "operational_sla": res["sla"],
        "customer_persona": res["customer_persona"],
        "next_best_action": res["next_best_action_en"],
        "explanation_ur": res["explanation_ur"],
        "explanation_en": res["explanation_en"],
    }
    return json.dumps(payload, indent=2)


@tool
def explain_prediction(
    model_type: str,
    city: str = "Lahore",
    area_society: str = "DHA Phase 5",
    plot_size_marla: float = 10.0,
    budget_pkr: float = 20000000.0,
    visit_booked: str = "No",
    number_of_calls: int = 2
) -> str:
    """Explains why a property was valued at a certain price or why a lead received a particular score using SHAP feature attribution in UrduLish and English."""
    if "prop" in model_type.lower() or "price" in model_type.lower():
        p_engine = get_property_engine()
        df_row = p_engine._prepare_feature_row({
            "city": city,
            "area_society": area_society,
            "plot_size_marla": plot_size_marla,
        })
        X_trans = p_engine.preprocessor.transform(df_row)
        import shap
        explainer = shap.TreeExplainer(p_engine.model)
        shap_vals = explainer.shap_values(X_trans)[0]
        feature_names = p_engine.preprocessor.get_feature_names_out()
        pred_pkr = float(np.expm1(p_engine.model.predict(X_trans)[0]))
        from shap_explainers import generate_property_plain_language_reasons
        reasons = generate_property_plain_language_reasons(shap_vals, feature_names, pred_pkr)
        return json.dumps({
            "target": "property_valuation",
            "urdulish_rationale": reasons["explanation_ur"],
            "english_rationale": reasons["explanation_en"],
        }, indent=2)
    else:
        l_engine = get_lead_engine()
        res = l_engine.score_lead({
            "budget_pkr": budget_pkr,
            "preferred_city": city,
            "visit_booked": visit_booked,
            "number_of_calls": number_of_calls
        })
        return json.dumps({
            "target": "lead_scoring",
            "urdulish_rationale": res["explanation_ur"],
            "english_rationale": res["explanation_en"],
            "top_drivers": res["top_positive_drivers"],
        }, indent=2)


@tool
def find_comparable_properties(
    city: str,
    area_society: str,
    plot_size_marla: float,
    tolerance_marla: float = 2.5,
    max_results: int = 4
) -> str:
    """Finds active and historical comparable property listings from the database matching the target location and plot size."""
    df = get_properties_database()
    if df.empty:
        return json.dumps({"error": "Property database not available."}, indent=2)

    city_clean = city.strip().title()
    soc_clean = area_society.strip().lower()

    # Filter matching city and society substring
    matches = df[df["city"].str.title() == city_clean].copy()
    if not matches.empty:
        soc_mask = matches["area_society_clean"].str.lower().str.contains(soc_clean, na=False)
        if soc_mask.any():
            matches = matches[soc_mask]

    # Filter plot size tolerance
    size_mask = (matches["plot_size_marla"] >= (plot_size_marla - tolerance_marla)) & (
        matches["plot_size_marla"] <= (plot_size_marla + tolerance_marla)
    )
    if size_mask.any():
        matches = matches[size_mask]

    matches = matches.head(max_results)
    comparables = []
    for _, row in matches.iterrows():
        pkr = float(row.get("price_pkr", 0.0))
        marla = float(row.get("plot_size_marla", 0.0))
        ppm = float(row.get("price_per_marla", pkr / max(marla, 0.1)))
        comparables.append({
            "property_id": row.get("property_id", "N/A"),
            "society": row.get("area_society_clean", area_society),
            "plot_size_marla": marla,
            "bedrooms": int(row.get("bedrooms", 4)),
            "price_formatted": format_pakistani_currency(pkr),
            "price_per_marla": format_pakistani_currency(ppm),
            "property_type": row.get("property_type", "House"),
        })

    return json.dumps({
        "query": {"city": city, "society": area_society, "target_marla": plot_size_marla},
        "total_comparables_found": len(comparables),
        "comparable_listings": comparables,
    }, indent=2)


@tool
def get_market_statistics(
    city: str,
    area_society: Optional[str] = None
) -> str:
    """Calculates official real estate micro-market statistics from historical listings, including average and median price per marla, total inventory, and price spread."""
    df = get_properties_database()
    if df.empty:
        return json.dumps({"error": "Property database empty."}, indent=2)

    city_clean = city.strip().title()
    subset = df[df["city"].str.title() == city_clean].copy()
    if subset.empty:
        return json.dumps({"error": f"No data found for city {city}."}, indent=2)

    if area_society:
        soc_mask = subset["area_society_clean"].str.lower().str.contains(area_society.strip().lower(), na=False)
        if soc_mask.any():
            subset = subset[soc_mask]

    avg_price = float(subset["price_pkr"].mean())
    median_price = float(subset["price_pkr"].median())
    avg_ppm = float(subset["price_per_marla"].mean())
    median_ppm = float(subset["price_per_marla"].median())
    min_ppm = float(subset["price_per_marla"].min())
    max_ppm = float(subset["price_per_marla"].max())

    return json.dumps({
        "city": city_clean,
        "society_filter": area_society or "All Societies",
        "sample_size_listings": len(subset),
        "avg_price_per_marla": format_pakistani_currency(avg_ppm),
        "median_price_per_marla": format_pakistani_currency(median_ppm),
        "price_per_marla_range": f"{format_pakistani_currency(min_ppm)} - {format_pakistani_currency(max_ppm)}",
        "average_overall_price": format_pakistani_currency(avg_price),
        "median_overall_price": format_pakistani_currency(median_price),
    }, indent=2)


AGENT_TOOLS = [
    predict_property_price,
    score_lead,
    explain_prediction,
    find_comparable_properties,
    get_market_statistics,
]

TOOLS_BY_NAME = {t.name: t for t in AGENT_TOOLS}

SYSTEM_PROMPT = """You are the official AI Real Estate Sales Assistant for an elite Pakistani property agency.
You assist sales agents, brokers, and callers in natural, professional UrduLish (mix of Urdu & English) or English.

STRICT OPERATIONAL RULES:
1. NEVER INVENT, GUESS, OR HALLUCINATE A PROPERTY PRICE, LEAD SCORE, OR MARKET STATISTIC.
2. EVERY NUMBER, VALUATION RANGE, CONVERSION PROBABILITY, OR RATE PER MARLA MUST COME DIRECTLY FROM ONE OF YOUR 5 TOOLS:
   - `predict_property_price`: For calculating fair market price, confidence range, and overpriced/underpriced verdict.
   - `score_lead`: For scoring an inquiry, assigning Hot/Warm/Cold priority, and identifying customer persona.
   - `explain_prediction`: For explaining SHAP factors driving a price or lead score.
   - `find_comparable_properties`: For pulling actual historical database comps.
   - `get_market_statistics`: For providing average or median price per marla by area.
3. If the user asks a question like "DHA Phase 6 mein 1 kanal, 5 saal purana ghar, kitne ka jana chahiye?", you MUST invoke `predict_property_price` and optionally `find_comparable_properties` or `explain_prediction`.
4. Tone: Helpful, knowledgeable Pakistani real estate specialist. Use respectful UrduLish (e.g. "Model ke mutabiq iski fair market value...", "Yeh lead Hot category mein aati hai kyun ke...").
"""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def build_realestate_assistant():
    """Builds and compiles the LangGraph AI Assistant with Tool Execution nodes."""
    
    # Check for LLM client
    llm = None
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        try:
            from langchain_groq import ChatGroq
            llm = ChatGroq(
                temperature=0.1,
                model_name=os.getenv("GROQ_LLM_MODEL", "llama-3.3-70b-versatile"),
                api_key=groq_api_key,
            ).bind_tools(AGENT_TOOLS)
        except Exception:
            llm = None

    def assistant_node(state: AgentState) -> Dict[str, Any]:
        msgs = list(state["messages"])
        if not any(isinstance(m, SystemMessage) for m in msgs):
            msgs = [SystemMessage(content=SYSTEM_PROMPT)] + msgs

        if llm is not None:
            try:
                response = llm.invoke(msgs)
                return {"messages": [response]}
            except Exception as e:
                # Fallback to local heuristic dispatch if external API has a temporary issue
                pass

        # Robust Local Rule-Based Tool Dispatcher (zero-downtime offline fallback)
        last_msg = msgs[-1].content if msgs else ""
        lower_txt = last_msg.lower()

        # Check prompt injection
        is_inj, reason = detect_prompt_injection(last_msg)
        if is_inj:
            return {
                "messages": [
                    AIMessage(
                        content=f"⚠️ {reason}\nMein sirf official Machine Learning models aur database tools ke zariye hi real estate maloomat faraham kar sakta hoon."
                    )
                ]
            }

        # Intent: Property Valuation
        if any(w in lower_txt for w in ["kitne ka", "price", "valuation", "qeemat", "fair value", "bikega"]):
            # Extract marla
            marla = 20.0 if "1 kanal" in lower_txt else (10.0 if "10 marla" in lower_txt else (5.0 if "5 marla" in lower_txt else 10.0))
            city = "Islamabad" if "islamabad" in lower_txt or "f-7" in lower_txt else ("Karachi" if "karachi" in lower_txt or "clifton" in lower_txt else "Lahore")
            society = "DHA Phase 6" if "phase 6" in lower_txt else ("DHA Phase 5" if "phase 5" in lower_txt else ("Sector F-7" if "f-7" in lower_txt else "DHA"))
            
            tool_output = predict_property_price.invoke({
                "city": city,
                "area_society": society,
                "plot_size_marla": marla,
                "age_years": 5.0 if "5 saal" in lower_txt else 2.0,
                "property_type": "House"
            })
            data = json.loads(tool_output)
            ans = (
                f"Model ke mutabiq iski fair market value **{data['lower_range_formatted']} se {data['upper_range_formatted']}** "
                f"ke darmiyan hai (Estimated Price: **{data['predicted_price_formatted']}**).\n\n"
                f"💡 **UrduLish Rationale:** {data['urdulish_summary']}\n\n"
                f"📌 *Note: {data['disclaimer']}*"
            )
            return {"messages": [AIMessage(content=ans)]}

        # Intent: Lead Scoring
        if any(w in lower_txt for w in ["lead", "score", "hot lead", "client"]):
            tool_output = score_lead.invoke({
                "budget_pkr": 25000000.0,
                "visit_booked": "Yes" if "visit" in lower_txt else "No",
                "number_of_calls": 4 if "call" in lower_txt else 2,
            })
            data = json.loads(tool_output)
            ans = (
                f"{data['priority_badge']} Yeh lead **{data['priority_tier'].upper()}** category mein aati hai "
                f"(Conversion Probability: **{data['conversion_pct']}**).\n"
                f"👤 **Customer Persona:** {data['customer_persona']}\n"
                f"⏱ **SLA:** {data['operational_sla']}\n"
                f"🎯 **Next Best Action:** {data['next_best_action']}\n"
                f"📝 **Tafseel:** {data['explanation_ur']}"
            )
            return {"messages": [AIMessage(content=ans)]}

        # Intent: Market Stats
        if any(w in lower_txt for w in ["rate", "average", "stats", "per marla"]):
            tool_output = get_market_statistics.invoke({"city": "Lahore", "area_society": "DHA"})
            data = json.loads(tool_output)
            ans = (
                f"📊 **Market Statistics for {data['society_filter']} ({data['city']}):**\n"
                f"- Average Rate Per Marla: **{data['avg_price_per_marla']}**\n"
                f"- Median Rate Per Marla: **{data['median_price_per_marla']}**\n"
                f"- Price Range: **{data['price_per_marla_range']}**\n"
                f"- Active Listings Analyzed: **{data['sample_size_listings']} properties**"
            )
            return {"messages": [AIMessage(content=ans)]}

        return {
            "messages": [
                AIMessage(
                    content=(
                        "Assalam-o-Alaikum! Mein aapka AI Real Estate Assistant hoon. "
                        "Aap mujh se kisi bhi property ki fair market price, lead score, area ke market rates, "
                        "ya comparable listings ke baray mein pooch sakte hain.\n"
                        "Misal ke tor par: *'DHA Phase 6 mein 1 kanal, 5 saal purana ghar, kitne ka jana chahiye?'*"
                    )
                )
            ]
        }

    def tool_execution_node(state: AgentState) -> Dict[str, Any]:
        last_msg = state["messages"][-1]
        tool_results = []
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                t_name = tc["name"]
                t_args = tc["args"]
                if t_name in TOOLS_BY_NAME:
                    tool_fn = TOOLS_BY_NAME[t_name]
                    res = tool_fn.invoke(t_args)
                    tool_results.append(ToolMessage(content=str(res), tool_call_id=tc["id"]))
        return {"messages": tool_results}

    def router_fn(state: AgentState) -> str:
        last_msg = state["messages"][-1]
        if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(AgentState)
    workflow.add_node("assistant", assistant_node)
    workflow.add_node("tools", tool_execution_node)

    workflow.set_entry_point("assistant")
    workflow.add_conditional_edges("assistant", router_fn, {"tools": "tools", END: END})
    workflow.add_edge("tools", "assistant")

    return workflow.compile()


realestate_assistant = build_realestate_assistant()


def chat_with_assistant(user_input: str, chat_history: Optional[List[Dict[str, str]]] = None) -> str:
    """Helper interface for interactive chat with the AI assistant."""
    # Guardrail: Check prompt injection
    is_inj, reason = detect_prompt_injection(user_input)
    if is_inj:
        return (
            f"🛡️ **Security Alert:** {reason}\n"
            "Assalam-o-Alaikum. Hamara system strict safety policies par mabni hai aur sirf verified real estate tools "
            "se predictions faraham karta hai."
        )

    msgs = []
    if chat_history:
        for m in chat_history:
            if m.get("role") == "user":
                msgs.append(HumanMessage(content=m["content"]))
            elif m.get("role") == "assistant":
                msgs.append(AIMessage(content=m["content"]))

    msgs.append(HumanMessage(content=user_input))
    state = realestate_assistant.invoke({"messages": msgs})
    final_msg = state["messages"][-1]
    return final_msg.content
