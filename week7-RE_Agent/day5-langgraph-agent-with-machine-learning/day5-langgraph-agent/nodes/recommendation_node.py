"""Task 2 & 4: Recommendation Node with Spoken UrduLish & Investment Advisory."""
from __future__ import annotations

import re
from typing import Any, Dict, List
from langchain_core.messages import AIMessage

from logger import default_agent_logger
from state import AgentState
from tools.availability_tools import check_property_availability
from tools.search_tools import search_properties_core


def _format_price_pkr(price: Any) -> str:
    """Format price into natural spoken Pakistani terms (e.g. 19 lakh, 2.1 crore, 50 hazar)."""
    try:
        val = float(str(price).replace(",", "").replace("PKR", "").strip())
    except (ValueError, TypeError):
        return str(price)

    if val >= 10_000_000:
        crores = val / 10_000_000
        if crores == int(crores):
            return f"{int(crores)} crore"
        return f"{crores:.2f}".rstrip("0").rstrip(".") + " crore"
    elif val >= 100_000:
        lakhs = val / 100_000
        if lakhs == int(lakhs):
            return f"{int(lakhs)} lakh"
        return f"{lakhs:.2f}".rstrip("0").rstrip(".") + " lakh"
    elif val >= 1_000:
        thousands = val / 1_000
        if thousands == int(thousands):
            return f"{int(thousands)} hazar"
        return f"{thousands:.2f}".rstrip("0").rstrip(".") + " hazar"
    return f"{int(val)} rupees"


def _clean_locality_str(locality: str) -> str:
    """Clean verbose address strings for voice speech."""
    s = str(locality or "")
    s = s.replace(", Punjab, Lahore", "").replace(", Punjab, Rawalpindi", "").replace(", Islamabad Capital Territory, Islamabad", "").replace(", Islamabad, Islamabad", "").replace(", Punjab", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def recommendation_node(state: AgentState) -> Dict[str, Any]:
    """Search, validate, and present verified properties in spoken UrduLish with investment advisory."""
    step = default_agent_logger.log_node_entry("RecommendationNode", state.get("last_node", "IntentDetectionNode"), state)

    prefs = state.get("property_preferences", {})
    city = prefs.get("city", "Lahore")
    budget = state.get("budget") or 100_000_000.0
    bedrooms = prefs.get("bedrooms")
    area_marla = prefs.get("area_marla")
    property_type = prefs.get("property_type", "House")
    purpose = prefs.get("purpose", "For Sale")
    locality = prefs.get("locality")
    is_investment = bool(prefs.get("investment_goal", False))

    # 1. Execute Search Core
    search_params = {
        "city": city,
        "budget_max": budget,
        "bedrooms": bedrooms,
        "area_marla": area_marla,
        "property_type": property_type,
        "purpose": purpose,
        "locality_contains": locality,
        "investment_goal": is_investment,
    }
    raw_results = search_properties_core(**search_params)
    step.record_tool_call("property_search_tool", search_params, raw_results)

    properties: List[Dict[str, Any]] = raw_results.get("properties", [])
    verified_properties: List[Dict[str, Any]] = []

    # 2. Strict Validation Check: Never recommend unavailable or non-existent properties
    for prop in properties:
        prop_id = prop.get("property_id", "")
        avail = check_property_availability(prop_id)
        if avail.get("available") and avail.get("exists"):
            verified_properties.append(prop)
            step.record_validation(
                check_name=f"Property Availability ({prop_id})",
                passed=True,
                details=f"Verified active in database. Locality: {prop.get('locality')}, Price: PKR {prop.get('price'):,}",
            )
        else:
            step.record_validation(
                check_name=f"Property Availability ({prop_id})",
                passed=False,
                details=f"Filtered out unavailable property: {avail.get('reason')}",
            )

    # 3. Format Response for Voice TTS
    loc_display = locality or city
    pt_label = property_type.lower() if property_type else "houses"
    marla_label = f"{int(area_marla)} marla " if area_marla else ""

    all_match_marla = False
    if area_marla and verified_properties:
        all_match_marla = all(
            p.get("area_marla") is not None and abs(float(p["area_marla"]) - float(area_marla)) < 0.5
            for p in verified_properties
        )

    if not verified_properties:
        response_text = (
            f"Maaf kijiye ga, {loc_display} {city} mein {marla_label}{pt_label} ke liye verified database mein koi matching property nahi mili. "
            f"Kya aap budget thora barhana chahenge ya kisi qareebi society mein options dekhna chahenge?"
        )
    else:
        formatted_opts = []
        for idx, p in enumerate(verified_properties[:3], 1):
            price_spoken = _format_price_pkr(p.get("price", 0))
            marla_val = p.get("area_marla", "")
            marla_str = f"{int(marla_val)} marla" if marla_val else ""
            clean_loc = _clean_locality_str(p.get("locality", ""))
            bed_count = p.get("bedrooms")
            bed_str = f", {bed_count} bedrooms" if bed_count else ""
            formatted_opts.append(f"Option {idx}: {marla_str} {p.get('property_type', 'House')} in {clean_loc}, price {price_spoken}{bed_str}.")

        options_block = " ".join(formatted_opts)

        if area_marla and not all_match_marla:
            intro = f"Ji sir, {loc_display} {city} mein {int(area_marla)} marla ke exact match na hone par aap ke budget mein yeh qareebi options available hain: "
        elif area_marla and len(verified_properties) == 1:
            intro = f"Ji sir, {loc_display} {city} mein hamare paas {int(area_marla)} marla {pt_label} ke liye yeh verified option available hai: "
        elif area_marla:
            intro = f"Ji sir, {loc_display} {city} mein hamare paas {int(area_marla)} marla {pt_label}s ke liye yeh behtareen options available hain: "
        else:
            intro = f"Ji sir, {loc_display} {city} mein hamare paas {pt_label}s ke liye yeh behtareen options available hain: "

        if is_investment:
            investment_note = "Yeh rental yield aur future capital appreciation ke liye bohot solid investment options hain. "
            response_text = (
                f"{intro}{options_block} {investment_note}"
                f"In mein se kaun sa option aap visit karna pasand karenge ji? Main aap ka visit schedule kar deta hoon."
            )
        else:
            response_text = (
                f"{intro}{options_block} "
                f"In mein se kaun sa option aap visit karna pasand karenge ji? Main aap ka visit schedule kar deta hoon."
            )

    output = {
        "recommended_properties": verified_properties,
        "final_response": response_text,
        "conversation_history": [AIMessage(content=response_text)],
        "last_node": "RecommendationNode",
        "tool_outputs": [{
            "tool": "property_search_tool",
            "found_count": len(verified_properties),
            "top_property_id": verified_properties[0].get("property_id") if verified_properties else None,
        }],
    }

    default_agent_logger.log_node_exit(
        step,
        output,
        reasoning=f"Retrieved {len(verified_properties)} verified properties formatted for voice.",
    )
    return output
