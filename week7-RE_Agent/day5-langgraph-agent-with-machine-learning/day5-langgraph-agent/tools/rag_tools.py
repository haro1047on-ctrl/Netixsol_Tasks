"""Task 3: RAG Knowledge Base Search Tool with Structured Amenities & Sahooliyat Lookup."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from langchain_core.tools import tool
from sqlalchemy import text

from config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    RETRIEVAL_K,
    RETRIEVAL_MIN_SCORE,
    get_embeddings,
    get_engine,
)

_vectorstore = None


def get_vectorstore_instance():
    """Lazily load persistent Chroma vector store."""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    chroma_path = Path(CHROMA_DIR)
    if chroma_path.exists():
        try:
            from langchain_chroma import Chroma
            _vectorstore = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=get_embeddings(),
                persist_directory=str(chroma_path),
            )
            return _vectorstore
        except Exception:
            pass
    return None


def search_kb_core(query: str, k: int = RETRIEVAL_K, active_locality: Optional[str] = None, active_city: Optional[str] = None) -> Dict[str, Any]:
    """Perform semantic retrieval and structured lookup from schools, hospitals, amenities, locations, and Chroma vector store."""
    if not query or not query.strip():
        return {
            "success": False,
            "error": "Query cannot be empty.",
            "results": [],
            "sources": [],
        }

    q_clean = query.strip().lower()
    engine = get_engine()
    results = []
    sources = []

    # Detect locality / society from query or active state
    target_loc = None
    locality_cues = (
        "dha", "bahria", "johar town", "faisal town", "model town", "gulberg",
        "e-11", "f-10", "f-11", "f-6", "g-11", "g-13", "airport housing", "ghauri town"
    )
    for loc in locality_cues:
        if loc in q_clean:
            target_loc = loc
            break
    if not target_loc and active_locality:
        for loc in locality_cues:
            if loc in active_locality.lower():
                target_loc = loc
                break
    if not target_loc and active_city:
        target_loc = active_city.lower()

    loc_param = f"%{target_loc}%" if target_loc else None

    # 1. Structured Lookup: SCHOOLS
    is_school_query = any(k in q_clean for k in (
        "school", "schools", "college", "colleges", "education", "academy",
        "سکول", "سکولز", "کالج", "تعلیم", "پڑھائی", "یونیورسٹی"
    ))
    if is_school_query:
        try:
            with engine.connect() as conn:
                sql = """
                    SELECT locality_full, school_name, level, distance_km_est
                    FROM schools
                    WHERE (:loc IS NULL OR LOWER(locality_full) LIKE :loc_param)
                    LIMIT 6
                """
                rows = conn.execute(text(sql), {"loc": target_loc, "loc_param": loc_param}).mappings().all()
                if not rows and target_loc:
                    # Fallback to any schools
                    rows = conn.execute(text("SELECT locality_full, school_name, level, distance_km_est FROM schools LIMIT 5")).mappings().all()
                if rows:
                    items = [f"{r['school_name']} ({r.get('distance_km_est', '')} km, {r.get('level', '')})" for r in rows]
                    loc_name = target_loc.title() if target_loc else "Nearby"
                    summary_text = f"Verified Schools in {loc_name}: " + ", ".join(items)
                    results.append({
                        "text": summary_text,
                        "score": 0.99,
                        "metadata": {"source_table": "schools.csv"},
                    })
                    sources.append("schools.csv")
        except Exception:
            pass

    # 2. Structured Lookup: HOSPITALS & MEDICAL
    is_hospital_query = any(k in q_clean for k in (
        "hospital", "hospitals", "clinic", "clinics", "doctor", "medical", "emergency", "health",
        "ہسپتال", "ہسپتالوں", "کلینک", "ڈاکٹر", "طبی", "علاج"
    ))
    if is_hospital_query:
        try:
            with engine.connect() as conn:
                sql = """
                    SELECT locality_full, hospital_name, specialty, distance_km_est
                    FROM hospitals
                    WHERE (:loc IS NULL OR LOWER(locality_full) LIKE :loc_param)
                    LIMIT 6
                """
                rows = conn.execute(text(sql), {"loc": target_loc, "loc_param": loc_param}).mappings().all()
                if not rows and target_loc:
                    rows = conn.execute(text("SELECT locality_full, hospital_name, specialty, distance_km_est FROM hospitals LIMIT 5")).mappings().all()
                if rows:
                    items = [f"{r['hospital_name']} ({r.get('distance_km_est', '')} km, {r.get('specialty', '')})" for r in rows]
                    loc_name = target_loc.title() if target_loc else "Nearby"
                    summary_text = f"Verified Hospitals in {loc_name}: " + ", ".join(items)
                    results.append({
                        "text": summary_text,
                        "score": 0.99,
                        "metadata": {"source_table": "hospitals.csv"},
                    })
                    sources.append("hospitals.csv")
        except Exception:
            pass

    # 3. Structured Lookup: AMENITIES & SAHOOLIYAT
    is_amenity_query = any(k in q_clean for k in (
        "amenit", "sahooliyat", "sahulat", "park", "parks", "mosque", "masjid",
        "market", "commercial", "gym", "pool", "swimming", "sports", "cctv", "security",
        "سہولیات", "سہولت", "پارک", "مسجد", "مارکیٹ", "سیکورٹی", "جم", "سوئمنگ پول"
    ))
    if is_amenity_query or (not is_school_query and not is_hospital_query):
        try:
            with engine.connect() as conn:
                sql = """
                    SELECT locality_full, amenity
                    FROM amenities
                    WHERE (:loc IS NULL OR LOWER(locality_full) LIKE :loc_param)
                    LIMIT 10
                """
                rows = conn.execute(text(sql), {"loc": target_loc, "loc_param": loc_param}).mappings().all()
                if rows:
                    items = [str(r.get("amenity", "")) for r in rows if r.get("amenity")]
                    loc_name = target_loc.title() if target_loc else "Society"
                    summary_text = f"Verified Amenities & Sahooliyat for {loc_name}: " + ", ".join(items)
                    results.append({
                        "text": summary_text,
                        "score": 0.95,
                        "metadata": {"source_table": "amenities.csv"},
                    })
                    sources.append("amenities.csv")
        except Exception:
            pass

    # 2. Semantic Search in Vector Store
    vs = get_vectorstore_instance()
    if vs is not None:
        try:
            hits = vs.similarity_search_with_relevance_scores(query.strip(), k=k)
            for doc, score in hits:
                if score >= RETRIEVAL_MIN_SCORE:
                    src = doc.metadata.get("source", "Knowledge Base")
                    sources.append(src)
                    results.append({
                        "text": doc.page_content,
                        "score": round(score, 3),
                        "metadata": doc.metadata,
                    })
        except Exception:
            pass

    # 3. Direct SQL Fallback
    if not results:
        q_like = f"%{q_clean}%"
        sql_queries = [
            ("locations", "SELECT locality_name, city, description FROM locations WHERE LOWER(locality_name) LIKE :q OR LOWER(city) LIKE :q OR LOWER(description) LIKE :q LIMIT 3"),
            ("faqs", "SELECT question, answer, category FROM faqs WHERE LOWER(question) LIKE :q OR LOWER(answer) LIKE :q LIMIT 3"),
            ("developers", "SELECT developer_authority, locality_name, city, profile FROM developers WHERE LOWER(developer_authority) LIKE :q OR LOWER(profile) LIKE :q LIMIT 3"),
            ("payment_plans", "SELECT locality_name, project_name, down_payment_pct, installment_months FROM payment_plans WHERE LOWER(project_name) LIKE :q OR LOWER(locality_name) LIKE :q LIMIT 3"),
        ]

        with engine.connect() as conn:
            for tbl, sql in sql_queries:
                try:
                    rows = conn.execute(text(sql), {"q": q_like}).mappings().all()
                    for r in rows:
                        snippet = " | ".join(f"{k}: {v}" for k, v in dict(r).items() if v)
                        results.append({
                            "text": snippet,
                            "score": 0.8,
                            "metadata": {"source_table": tbl},
                        })
                        sources.append(tbl)
                except Exception:
                    continue

    return {
        "success": True,
        "results": results,
        "sources": list(set(sources)),
        "count": len(results),
    }


@tool("rag_search_tool")
def rag_search_tool(query: str) -> str:
    """Tool for retrieving verified real estate facts, amenities, schools, hospitals, and legal info."""
    res = search_kb_core(query)
    return json.dumps(res, indent=2)
