"""Task 2 & 3: RAG Knowledge Base Retrieval Node in natural UrduLish."""
from __future__ import annotations

import re
from typing import Any, Dict
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from config import get_llm
from logger import default_agent_logger
from state import AgentState
from tools.rag_tools import search_kb_core


def rag_node(state: AgentState) -> Dict[str, Any]:
    """Retrieve verified knowledge and generate grounded responses in natural UrduLish."""
    step = default_agent_logger.log_node_entry("RAGNode", state.get("last_node", "IntentDetectionNode"), state)

    raw_input = state.get("raw_user_input", "")
    if not raw_input and state.get("conversation_history"):
        raw_input = state["conversation_history"][-1].content

    prefs = state.get("property_preferences", {})
    active_loc = prefs.get("locality")
    active_city = prefs.get("city")

    # 1. Execute RAG Retrieval
    rag_result = search_kb_core(raw_input, active_locality=active_loc, active_city=active_city)
    step.record_tool_call("rag_search_tool", {"query": raw_input, "locality": active_loc, "city": active_city}, rag_result)

    hits = rag_result.get("results", [])
    sources = rag_result.get("sources", [])
    
    if hits:
        context_str = "\n\n".join(f"[Source: {h.get('metadata', {}).get('source_table', 'KB')}]: {h.get('text')}" for h in hits)
    else:
        context_str = "No specific knowledge base entry found."

    # 2. LLM Synthesis in concise UrduLish
    llm = get_llm(temperature=0.1)
    system_prompt = (
        "You are an expert Pakistani Real Estate Consultant at RealEstate Hub.\n"
        "Respond in warm, natural, concise UrduLish (Roman Urdu with standard English terms like society names, NOC, installment, amenities).\n"
        "Strict Guidelines:\n"
        "1. Speak directly in 1-2 concise sentences suitable for a live voice call. Do NOT use bullet points, markdown bold (*), or hashtags.\n"
        "2. Base your answer strictly on the verified knowledge base context below (such as schools, hospitals, commercial markets, parks).\n"
        "3. NEVER invent approvals, ROI numbers, or fake amenities.\n"
        "4. If something is not in context, politely say: 'Yeh specific maloomat hamare verified record mein mojood nahi hai, lekin main consultant se rabta karwa sakta hoon.'\n\n"
        f"--- VERIFIED CONTEXT ---\n{context_str}\n-------------------------"
    )

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=raw_input),
        ]
        ai_resp = llm.invoke(messages)
        content_val = ai_resp.content
        if isinstance(content_val, list):
            raw_text = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content_val
            )
        else:
            raw_text = str(content_val)
        answer_text = re.sub(r"[\*#_`]", "", raw_text).strip()
    except Exception:
        if hits:
            clean_hit = re.sub(r"[\*#_`]", "", hits[0]['text'])
            answer_text = f"Verified record ke mutabiq: {clean_hit}"
        else:
            answer_text = "Is bare mein verified details ke liye hamare property consultant aap se direct rabta kar lenge."

    output = {
        "rag_context": context_str,
        "rag_sources": sources,
        "final_response": answer_text,
        "conversation_history": [AIMessage(content=answer_text)],
        "last_node": "RAGNode",
    }

    default_agent_logger.log_node_exit(
        step,
        output,
        reasoning=f"Generated grounded UrduLish answer from {len(hits)} verified KB chunks.",
    )
    return output
