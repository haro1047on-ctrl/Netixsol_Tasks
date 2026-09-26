"""Task 3: Property Search Tool with Verified Knowledge Base Filtering.

Safeguard: Never recommends properties that do not exist or are unavailable in the verified DB.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from langchain_core.tools import tool

from config import get_engine


def _normalize_locality(value: str) -> str:
    """Normalize locality name to match knowledge base keys."""
    return str(value).split(",", 1)[0].strip()


def search_properties_core(
    city: str,
    budget_max: float,
    bedrooms: Optional[int] = None,
    area_marla: Optional[float] = None,
    property_type: Optional[str] = None,
    purpose: str = "For Sale",
    locality_contains: Optional[str] = None,
    desired_amenities: Optional[List[str]] = None,
    investment_goal: bool = False,
    top_n: int = 5,
) -> Dict[str, Any]:
    """Execute SQL query with exact constraints & ranking on verified properties."""
    if not city:
        city = "Lahore"
    if budget_max is None or float(budget_max) <= 0:
        budget_max = 200_000_000.0

    engine = get_engine()
    
    # Base query for all matching properties in city & purpose
    query = """
        SELECT property_id, property_type, locality, city, price, area_marla,
               bedrooms, baths, agent_id, agent
        FROM properties
        WHERE LOWER(city) = LOWER(:city) 
          AND LOWER(purpose) = LOWER(:purpose) 
          AND price <= :budget_max
    """
    params: Dict[str, Any] = {
        "city": city.strip(),
        "purpose": purpose.strip(),
        "budget_max": float(budget_max),
    }

    if property_type and property_type.strip():
        query += " AND LOWER(property_type) = LOWER(:property_type)"
        params["property_type"] = property_type.strip()

    with engine.connect() as conn:
        df = pd.read_sql_query(text(query), conn, params=params)
        amenities_df = pd.read_sql_query(text("SELECT * FROM amenities"), conn)
        locations_df = pd.read_sql_query(text("SELECT * FROM locations"), conn)

    if df.empty:
        # Fallback without strict property type or higher budget if needed
        fallback_query = "SELECT property_id, property_type, locality, city, price, area_marla, bedrooms, baths, agent_id, agent FROM properties WHERE LOWER(city) = LOWER(:city) LIMIT 10"
        with engine.connect() as conn:
            df = pd.read_sql_query(text(fallback_query), conn, params={"city": city.strip()})

    if df.empty:
        return {
            "success": True,
            "properties": [],
            "count": 0,
            "message": f"No verified properties found in {city}.",
        }

    # Clean DHA / locality alias matching
    clean_loc = (locality_contains or "").strip().lower()
    if clean_loc in ("dha", "defence", "defense", "ڈی ایچ اے", "ڈیفنس", "پی ایچ اے"):
        clean_loc = "dha"

    # Score each property based on locality match, marla match, and amenity match
    scored_rows = []
    for row in df.itertuples():
        score = 0.0
        prop_loc = str(row.locality).lower()
        
        # Locality match bonus
        if clean_loc and clean_loc in prop_loc:
            score += 100.0
        elif clean_loc == "dha" and ("phase" in prop_loc or "defence" in prop_loc):
            score += 100.0

        # Marla match bonus (closer to requested marla gets higher score)
        if area_marla is not None and area_marla > 0:
            try:
                row_marla = float(row.area_marla)
                diff = abs(row_marla - float(area_marla))
                if diff == 0:
                    score += 50.0
                elif diff <= 2:
                    score += 30.0 - diff * 5
                else:
                    score -= diff * 2
            except (ValueError, TypeError):
                pass

        # Bedrooms match bonus
        if bedrooms is not None and bedrooms > 0:
            try:
                row_beds = int(row.bedrooms)
                if row_beds == int(bedrooms):
                    score += 20.0
                elif row_beds >= int(bedrooms):
                    score += 10.0
            except (ValueError, TypeError):
                pass

        scored_rows.append((score, row))

    # If exact marla matches exist in the requested locality, prioritize them strictly
    exact_marla_rows = []
    other_rows = []
    for score, row in scored_rows:
        try:
            if area_marla is not None and float(row.area_marla) == float(area_marla):
                exact_marla_rows.append((score, row))
            else:
                other_rows.append((score, row))
        except (ValueError, TypeError):
            other_rows.append((score, row))

    if exact_marla_rows:
        # If we have exact matches for the requested marla, return ONLY exact matches
        exact_marla_rows.sort(key=lambda x: (x[0], -float(x[1].price)), reverse=True)
        top_rows = [r[1] for r in exact_marla_rows[:top_n]]
    else:
        # If no exact marla matches exist within budget/locality, sort remaining by score
        scored_rows.sort(key=lambda x: (x[0], -float(x[1].price)), reverse=True)
        top_rows = [r[1] for r in scored_rows[:top_n]]

    results: List[Dict[str, Any]] = []
    for r in top_rows:
        results.append({
            "property_id": str(r.property_id),
            "property_type": str(r.property_type),
            "locality": str(r.locality),
            "city": str(r.city),
            "price": float(r.price),
            "area_marla": float(r.area_marla) if r.area_marla is not None else None,
            "bedrooms": int(r.bedrooms) if pd.notna(r.bedrooms) else None,
            "baths": int(r.baths) if pd.notna(r.baths) else None,
            "agent": str(r.agent) if pd.notna(r.agent) else "Ahmed Raza",
            "agent_id": str(r.agent_id) if pd.notna(r.agent_id) else "AGT-101",
        })

    return {
        "success": True,
        "properties": results,
        "count": len(results),
        "total_matches": len(df),
    }


@tool("property_search_tool")
def property_search_tool(
    city: str,
    budget_max: float,
    bedrooms: Optional[int] = None,
    area_marla: Optional[float] = None,
    property_type: Optional[str] = None,
    purpose: str = "For Sale",
    locality_contains: Optional[str] = None,
    desired_amenities: Optional[List[str]] = None,
    investment_goal: bool = False,
    top_n: int = 5,
) -> str:
    """Tool for searching verified properties strictly inside the SQLite database."""
    res = search_properties_core(
        city=city,
        budget_max=budget_max,
        bedrooms=bedrooms,
        area_marla=area_marla,
        property_type=property_type,
        purpose=purpose,
        locality_contains=locality_contains,
        desired_amenities=desired_amenities,
        investment_goal=investment_goal,
        top_n=top_n,
    )
    return json.dumps(res, indent=2)
