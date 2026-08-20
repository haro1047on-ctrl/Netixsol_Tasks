"""
Day 4: LangGraph Orchestrated AFL Assistant
Integrates Intent Routing, State Schema, Retrieval Nodes, Prediction Tools,
Validation & Clarification Loop, and Response Formatting.
"""

import afl_chat_agent
import os
import re
import pandas as pd
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

# Import Day 4 Prediction Tools
from prediction_tools import predict_match_winner, predict_top_player, resolve_team_alias

# Import Day 3 Retrieval Engine Tools
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "Day3"))
try:
    from afl_chat_agent import (
        get_team_stats,
        get_player_stats,
        get_team_match_results,
        get_stat_leaders,
        compare_players,
        get_afl_rules_and_info,
        verify_grounding
    )
except ImportError:
    # Fallback inline imports if Day3 package path varies
    from afl_chat_agent import get_team_stats, get_player_stats, get_afl_rules_and_info

load_dotenv()

# Initialize LLM for router and response formatting
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0)


# ==============================================================================
# 1. STATE SCHEMA DESIGN
# ==============================================================================
class AFLAgentState(TypedDict):
    user_query: str
    messages: List[BaseMessage]
    detected_intent: str           # "prediction", "retrieval", "factual", "off_topic"
    entities: Dict[str, Any]        # Extracted teams, players, stat_type, year
    tool_results: Dict[str, Any]    # Raw output from executed tools
    validation_status: str          # "VALID", "NEEDS_CLARIFICATION", "OUT_OF_SCOPE"
    clarification_prompt: Optional[str]
    final_response: str


# ==============================================================================
# 2. INTENT ROUTER NODE
# ==============================================================================
def _extract_player_names_from_query(query: str) -> List[str]:
    """
    Extracts likely player names from a natural language query by identifying
    capitalized word pairs (Title Case) that are not AFL team names.
    """
    from prediction_tools import TEAM_ALIASES
    official_teams = set(TEAM_ALIASES.values())

    # Find all Title Case word sequences (e.g. 'Sam Walsh', 'Patrick Cripps')
    pattern = r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\b'
    candidates = re.findall(pattern, query)

    player_names = []
    for name in candidates:
        # Exclude known team names
        if name not in official_teams:
            player_names.append(name)
    return player_names


# Extended off-topic keyword set
_OFF_TOPIC_KEYWORDS = [
    # Other sports
    "nba", "nfl", "nhl", "nrl", "rugby", "soccer", "football", "premier league",
    "champions league", "la liga", "bundesliga", "serie a", "world cup", "cricket",
    "tennis", "golf", "formula 1", "f1", "swimming",
    # Tech / coding
    "python", "quicksort", "code", "script", "programming", "algorithm",
    "machine learning", "chatgpt", "llm", "openai", "gemini api",
    # Finance / crypto
    "stocks", "financial advisor", "investment", "crypto", "bitcoin",
    "ethereum", "forex", "share market",
    # Lifestyle / other
    "recipe", "weather", "president", "politics", "translate", "french",
    "spanish", "german",
    # Persona overrides
    "act as", "pretend", "forget afl", "ignore your instructions", "jailbreak",
]


def intent_router_node(state: AFLAgentState) -> AFLAgentState:
    """
    Classifies user query into one of four intent channels:
    - 'prediction': Match winner predictions, upcoming game odds, top scorer predictions
    - 'retrieval': Historical stats, disposals, goals, win rates, match scores
    - 'factual': Rules, MCG venue info, Brownlow medal, AFL terminology
    - 'off_topic': Non-AFL sports, coding, recipes, weather, politics, persona overrides
    """
    query = state["user_query"].strip()
    q_lower = query.lower()

    # --- Hard off-topic filter first (before any other routing) ---
    if any(kw in q_lower for kw in _OFF_TOPIC_KEYWORDS):
        state["detected_intent"] = "off_topic"
        state["entities"] = {}
        return state

    # --- Future year guard (beyond dataset scope 1983-2025) ---
    future_yr = re.search(r'\b(202[6-9]|20[3-9]\d|2[1-9]\d\d)\b', query)
    if future_yr:
        state["detected_intent"] = "off_topic"
        state["entities"] = {}
        return state

    # --- Keyword-based fast classification ---
    pred_kw = ["will win", "predict", "winner", "who will beat", "will beat", "odds",
               "probabilit", "top-score", "top scorer", "forecast", "chance",
               "will dominate", "who will lead"]
    retrieval_kw = ["stats", "disposals", "goals", "behinds", "kicks", "marks",
                    "tackles", "how many", "scores", "record", "average", "win rate",
                    "did", "was", "compare", "more often", "highest", "most", "top 5",
                    "top five", "leaderboard"]
    factual_kw = ["rule", "mark inside 50", "brownlow", "mcg", "disposal in afl",
                  "what is a", "how does", "explain", "definition"]

    if any(w in q_lower for w in pred_kw) and not any(w in q_lower for w in ["did", "was", "history", "previous"]):
        state["detected_intent"] = "prediction"
    elif any(w in q_lower for w in retrieval_kw):
        state["detected_intent"] = "retrieval"
    elif any(w in q_lower for w in factual_kw):
        state["detected_intent"] = "factual"
    else:
        # LLM Classifier for complex or ambiguous queries
        prompt = f"""Classify the user's intent into EXACTLY ONE of these categories:
- 'prediction': Future match outcome forecasts, probabilities, who will win, top scorer prediction.
- 'retrieval': Historical statistics, player numbers, match scores, past win rates.
- 'factual': AFL rules, ground dimensions, Brownlow medal, general league info.
- 'off_topic': Non-AFL topics (coding, cooking, weather, politics, other sports, translation, finance).

User Query: "{query}"

Output ONLY the category name in lowercase (prediction / retrieval / factual / off_topic)."""
        try:
            res = llm.invoke([HumanMessage(content=prompt)])
            cat = res.content.strip().lower()
            if cat in ["prediction", "retrieval", "factual", "off_topic"]:
                state["detected_intent"] = cat
            else:
                state["detected_intent"] = "retrieval"
        except Exception:
            state["detected_intent"] = "retrieval"

    # Extract entities (teams, players, years)
    state["entities"] = extract_entities(query)
    return state


def extract_entities(query: str) -> Dict[str, Any]:
    """Helper to extract teams, players, year ranges from user query."""
    q_lower = query.lower()
    entities: Dict[str, Any] = {}

    # Extract team pairs
    teams_found = []
    from prediction_tools import TEAM_ALIASES
    for alias, official in TEAM_ALIASES.items():
        if len(alias) >= 3 and re.search(r'\b' + re.escape(alias) + r'\b', q_lower):
            if official not in teams_found:
                teams_found.append(official)

    if len(teams_found) >= 2:
        entities["team_a"] = teams_found[0]
        entities["team_b"] = teams_found[1]
    elif len(teams_found) == 1:
        entities["team_a"] = teams_found[0]

    # Stat type
    for stat in ["disposals", "goals", "kicks", "marks", "tackles", "handballs", "behinds"]:
        if stat in q_lower:
            entities["stat_type"] = stat
            break

    # Year range: "across 2022 and 2023", "2022 to 2023", "2022-2023"
    yr_range = re.search(r'\b(19\d{2}|20\d{2})\b.*?\b(19\d{2}|20\d{2})\b', query)
    if yr_range:
        entities["start_year"] = int(yr_range.group(1))
        entities["end_year"] = int(yr_range.group(2))
        entities["year"] = int(yr_range.group(2))  # use end year as primary
    else:
        yr_match = re.search(r'\b(19\d\d|20\d\d)\b', query)
        if yr_match:
            entities["year"] = int(yr_match.group(1))

    # Extract player names (proper nouns not matching known team names)
    player_names = _extract_player_names_from_query(query)
    if len(player_names) >= 2:
        entities["multi_player"] = player_names
    elif len(player_names) == 1:
        entities["player_name"] = player_names[0]

    return entities


# ==============================================================================
# 3. NODE IMPLEMENTATIONS
# ==============================================================================

def prediction_node(state: AFLAgentState) -> AFLAgentState:
    """Executes Day 2 prediction models."""
    query = state["user_query"]
    entities = state.get("entities", {})

    if "team_a" in entities and "team_b" in entities:
        res = predict_match_winner(entities["team_a"], entities["team_b"])
        state["tool_results"] = {"type": "match_prediction", "data": res}
    elif "stat_type" in entities or "top" in query.lower():
        team_target = entities.get("team_a", "League-wide")
        stat_type = entities.get("stat_type", "goals")
        res = predict_top_player(team_target, stat_type)
        state["tool_results"] = {"type": "player_prediction", "data": res}
    else:
        # Generic match prediction prompt parsing
        words = re.findall(r'\b[A-Za-z]+\b', query)
        found = [resolve_team_alias(w) for w in words if resolve_team_alias(w)]
        unique_found = list(dict.fromkeys(found))
        if len(unique_found) >= 2:
            res = predict_match_winner(unique_found[0], unique_found[1])
            state["tool_results"] = {"type": "match_prediction", "data": res}
        else:
            state["tool_results"] = {
                "type": "error",
                "data": {"status": "ERROR", "message": "Could not identify two opposing teams to predict."}
            }

    return state


def retrieval_node(state: AFLAgentState) -> AFLAgentState:
    """Executes Day 3 historical retrieval tools."""
    query = state["user_query"]
    entities = state.get("entities", {})
    results = {}

    # 1. Multi-player comparison (e.g. "compare Sam Walsh and Lachie Neale")
    if "multi_player" in entities:
        player_str = ", ".join(entities["multi_player"])
        start_yr = entities.get("start_year", None)
        end_yr = entities.get("end_year", None)
        yr = entities.get("year", None)
        res = compare_players.invoke({
            "player_names": player_str,
            "start_year": start_yr or yr,
            "end_year": end_yr or yr
        })
        results["comparison"] = res

    # 2. Player name found via entity extraction → direct player stats
    elif "player_name" in entities:
        pname = entities["player_name"]
        yr = entities.get("year", None)
        start_yr = entities.get("start_year", None)
        end_yr = entities.get("end_year", None)

        if start_yr and end_yr:
            # Year range: aggregate stats across both years
            all_rows = []
            for y in range(start_yr, end_yr + 1):
                r = get_player_stats.invoke({"player_name": pname, "year": y})
                all_rows.append(f"[{y}] {r}")
            results["player_stats"] = "\n".join(all_rows)
        else:
            res = get_player_stats.invoke({"player_name": pname, "year": yr})
            results["player_stats"] = res

    # 3. Fallback: Try resolving player name from full query text
    else:
        from afl_chat_agent import resolve_player
        p_df = resolve_player(query)

        if p_df is not None and not p_df.empty:
            actual_name = p_df['player_name'].dropna().iloc[0]
            yr = entities.get("year", None)
            start_yr = entities.get("start_year", None)
            end_yr = entities.get("end_year", None)

            if start_yr and end_yr:
                all_rows = []
                for y in range(start_yr, end_yr + 1):
                    r = get_player_stats.invoke({"player_name": actual_name, "year": y})
                    all_rows.append(f"[{y}] {r}")
                results["player_stats"] = "\n".join(all_rows)
            else:
                res = get_player_stats.invoke({"player_name": actual_name, "year": yr})
                results["player_stats"] = res

    if results:
        state["tool_results"] = {"type": "retrieval", "data": results}
        return state

    q_lower = query.lower()

    # Leaderboard queries: top/leader/most/best player
    if any(kw in q_lower for kw in ["top", "leader", "leaders", "most"]):
        stat = entities.get("stat_type", "goals")
        yr = entities.get("year", None)
        res = get_stat_leaders.invoke({"stat": stat, "year": yr})
        results["stat_leaders"] = res

    # "Who is the best player / who leads" → return disposals leaderboard for latest year
    elif any(kw in q_lower for kw in ["best player", "who is the best", "greatest player", "who leads"]):
        res = get_stat_leaders.invoke({"stat": "disposals", "year": 2024, "top_n": 5})
        results["stat_leaders"] = f"Based on total disposals in 2024 (most recent full season):\n{res}"

    # "Best team win rate / which team won most" → compute from feature table
    elif any(kw in q_lower for kw in ["best team", "which team", "team win rate", "win rate", "won most"]):
        from prediction_tools import feature_df
        if not feature_df.empty and "win" in feature_df.columns:
            df = feature_df.copy()
            start_yr = entities.get("start_year", None)
            end_yr = entities.get("end_year", None)
            yr = entities.get("year", None)
            if start_yr and end_yr:
                df = df[(df["year"] >= start_yr) & (df["year"] <= end_yr)]
            elif yr:
                df = df[df["year"] == yr]
            ranked = df.groupby("team")["win"].mean().reset_index()
            ranked = ranked.sort_values("win", ascending=False).head(5)
            yr_label = f"{start_yr}–{end_yr}" if start_yr and end_yr else (str(yr) if yr else "all seasons")
            lines = [f"Top 5 teams by win rate ({yr_label}):"]
            for i, (_, row) in enumerate(ranked.iterrows(), 1):
                lines.append(f"  {i}. {row['team']}: {round(row['win'] * 100, 1)}% win rate")
            results["team_leaderboard"] = "\n".join(lines)
        else:
            results["team_leaderboard"] = "Team win rate data is unavailable at this time."

    elif "team_a" in entities and "year" in entities:
        res = get_team_match_results.invoke({"team_name": entities["team_a"], "year": entities["year"]})
        results["match_results"] = res
    elif "team_a" in entities:
        res = get_team_stats.invoke({"team_name": entities["team_a"]})
        results["team_stats"] = res
    else:
        # Final fallback: return "not enough info" rather than passing raw query as player name
        results["player_stats"] = "I couldn't identify a specific AFL player, team, or stat from your query. Could you provide more details? For example: 'How many disposals did Sam Walsh get in 2023?' or 'What is Carlton's win rate?'"

    state["tool_results"] = {"type": "retrieval", "data": results}
    return state


def direct_answer_node(state: AFLAgentState) -> AFLAgentState:
    """Handles conceptual AFL rules and history directly."""
    query = state["user_query"]
    info = get_afl_rules_and_info.invoke({"topic": query})
    state["tool_results"] = {"type": "factual", "data": info}
    return state


def refusal_node(state: AFLAgentState) -> AFLAgentState:
    """Politely declines off-topic queries with warm AFL redirection."""
    query = state["user_query"].lower()

    if any(kw in query for kw in ["python", "quicksort", "code", "script", "programming", "algorithm"]):
        resp = "I am dedicated solely as an AFL Chat Assistant and cannot help with programming tasks or writing scripts. I'd be happy to look up AFL match scores or player stats for you!"
    elif any(kw in query for kw in ["nba", "nfl", "nhl", "nrl", "rugby", "premier league", "champions league", "world cup", "cricket", "tennis", "golf"]):
        resp = "I specialize strictly in Australian Football League (AFL). While I can't answer questions about other sports leagues, I can share AFL team standings or player stats! Which AFL team would you like to explore?"
    elif any(kw in query for kw in ["stocks", "financial", "investment", "crypto", "bitcoin", "ethereum", "forex"]):
        resp = "I'm an AFL-dedicated assistant and can't provide financial or investment advice. However, I can predict which AFL team has the best 'winning investment' of form right now! Ask me about any team."
    elif any(kw in query for kw in ["translate", "french", "spanish", "german"]):
        resp = "Translation is outside my domain — I'm your AFL intelligence engine! I can share exact match scores, player stats, or make probabilistic match forecasts. What AFL question can I answer for you?"
    elif any(kw in query for kw in ["act as", "pretend", "forget afl", "jailbreak", "ignore your"]):
        resp = "I am dedicated solely as an AFL Chat Assistant and cannot change my persona or ignore my domain focus. Feel free to ask about any AFL team, player, or league rule!"
    elif any(kw in query for kw in ["llm", "chatgpt", "openai", "ai", "gemini"]):
        resp = "I'm your AFL-specialist assistant! Questions about AI systems are outside my scope, but I can answer any question about AFL history, player stats, or match predictions."
    elif re.search(r'\b(202[6-9]|20[3-9]\d)\b', query):
        resp = "My dataset covers AFL history from 1983 through the 2025 season. I cannot make predictions or retrieve data for years beyond 2025. Can I help you with a query within that range?"
    else:
        resp = "My expertise is focused exclusively on AFL football! I can't help with off-topic requests, but I'd be happy to check AFL match scores, head-to-head stats, or player disposal averages. What AFL question can I answer?"

    state["final_response"] = resp
    state["validation_status"] = "VALID"
    return state


# ==============================================================================
# 4. VALIDATION & SELF-CORRECTION NODE
# ==============================================================================
def validation_node(state: AFLAgentState) -> AFLAgentState:
    """
    Validates tool outputs:
    - If tool returned an error or unresolved entity -> NEEDS_CLARIFICATION
    - If stat requested is unmodeled -> OUT_OF_SCOPE
    - Otherwise -> VALID
    """
    tool_res = state.get("tool_results", {})
    res_data = tool_res.get("data", {})

    if isinstance(res_data, dict) and res_data.get("status") == "ERROR":
        msg = res_data.get("message", "")
        if "Could not resolve" in msg or "opposing teams" in msg:
            state["validation_status"] = "NEEDS_CLARIFICATION"
            state["clarification_prompt"] = f"I couldn't quite resolve the exact AFL teams from your query. Could you please specify the full team names (e.g. Collingwood Magpies vs Geelong Cats)?"
        elif "Unsupported stat" in msg:
            state["validation_status"] = "OUT_OF_SCOPE"
            state["final_response"] = f"My predictive model currently supports disposals, goals, marks, kicks, and tackles. The requested stat type is out of scope."
        else:
            state["validation_status"] = "NEEDS_CLARIFICATION"
            state["clarification_prompt"] = msg
    else:
        state["validation_status"] = "VALID"

    return state


def clarification_node(state: AFLAgentState) -> AFLAgentState:
    """Formats clarification request for the user."""
    prompt = state.get("clarification_prompt", "Could you please clarify your request with specific AFL team or player names?")
    state["final_response"] = f"CLARIFICATION REQUIRED: {prompt}"
    return state


# ==============================================================================
# 5. RESPONSE FORMATTER NODE
# ==============================================================================
def response_formatter_node(state: AFLAgentState) -> AFLAgentState:
    """
    Formats the final response according to strict framing guidelines:
    - Predictions MUST be framed probabilistically (win probability %, confidence, driving features, disclaimer).
    - Retrieval answers MUST be grounded in tool data.
    """
    intent = state.get("detected_intent")
    tool_res = state.get("tool_results", {})
    res_type = tool_res.get("type")
    res_data = tool_res.get("data")

    if intent == "prediction" and res_type == "match_prediction":
        winner = res_data["predicted_winner"]
        prob = res_data["win_probability"]
        loser = res_data["loser"]
        loser_prob = res_data["loser_probability"]
        conf = res_data["confidence"]
        feats = "\n".join([f"  - {f}" for f in res_data["driving_features"]])
        disc = res_data["disclaimer"]

        resp = f"""Based on statistical feature modeling, here is the probabilistic forecast:

* **Predicted Winner:** **{winner}** ({prob}% probability)
* **Opponent:** {loser} ({loser_prob}% probability)
* **Model Confidence:** **{conf}**

**Key Driving Features:**
{feats}

> *{disc}*"""
        state["final_response"] = resp

    elif intent == "prediction" and res_type == "player_prediction":
        player = res_data["predicted_player"]
        stat = res_data["stat_type"]
        avg = res_data["expected_average"]
        peak = res_data["recent_peak"]
        team = res_data["team"]
        conf = res_data["confidence"]
        feats = "\n".join([f"  - {f}" for f in res_data["driving_features"]])
        disc = res_data["disclaimer"]

        resp = f"""Probabilistic player forecast for **{team}**:

* **Top Performer Expectation:** **{player}** ({stat})
* **Projected Average:** ~{avg} {stat.lower()} per match (Recent Peak: {peak})
* **Model Confidence:** **{conf}**

**Key Driving Factors:**
{feats}

> *{disc}*"""
        state["final_response"] = resp

    elif intent == "retrieval":
        # Grounded summary string from retrieval tool output
        if isinstance(res_data, dict):
            val = next(iter(res_data.values())) if res_data else "No retrieval data available."
            state["final_response"] = str(val)
        else:
            state["final_response"] = str(res_data)

    elif intent == "factual":
        state["final_response"] = str(res_data)

    return state



# ==============================================================================
# 6. CONDITIONAL ROUTING EDGES
# ==============================================================================
def route_by_intent(state: AFLAgentState) -> str:
    intent = state.get("detected_intent", "retrieval")
    if intent == "prediction":
        return "prediction_node"
    elif intent == "retrieval":
        return "retrieval_node"
    elif intent == "factual":
        return "direct_answer_node"
    else:
        return "refusal_node"


def route_by_validation(state: AFLAgentState) -> str:
    status = state.get("validation_status", "VALID")
    if status == "NEEDS_CLARIFICATION":
        return "clarification_node"
    elif status == "OUT_OF_SCOPE":
        return "END"
    else:
        return "response_formatter_node"


# ==============================================================================
# 7. STATE GRAPH COMPILATION
# ==============================================================================
def build_afl_graph():
    workflow = StateGraph(AFLAgentState)

    # Add Nodes
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("prediction_node", prediction_node)
    workflow.add_node("retrieval_node", retrieval_node)
    workflow.add_node("direct_answer_node", direct_answer_node)
    workflow.add_node("refusal_node", refusal_node)
    workflow.add_node("validation_node", validation_node)
    workflow.add_node("clarification_node", clarification_node)
    workflow.add_node("response_formatter_node", response_formatter_node)

    # Entry point
    workflow.set_entry_point("intent_router")

    # Conditional Branching from Router
    workflow.add_conditional_edges(
        "intent_router",
        route_by_intent,
        {
            "prediction_node": "prediction_node",
            "retrieval_node": "retrieval_node",
            "direct_answer_node": "direct_answer_node",
            "refusal_node": "refusal_node"
        }
    )

    # Convergence to Validation Node
    workflow.add_edge("prediction_node", "validation_node")
    workflow.add_edge("retrieval_node", "validation_node")

    # Validation Routing
    workflow.add_conditional_edges(
        "validation_node",
        route_by_validation,
        {
            "clarification_node": "clarification_node",
            "response_formatter_node": "response_formatter_node",
            "END": END
        }
    )

    # Termination Edges
    workflow.add_edge("direct_answer_node", "response_formatter_node")
    workflow.add_edge("response_formatter_node", END)
    workflow.add_edge("clarification_node", END)
    workflow.add_edge("refusal_node", END)

    return workflow.compile()


# Export compiled graph instance
afl_app = build_afl_graph()


if __name__ == "__main__":
    print("Testing LangGraph AFL Agent Execution:")
    state = {
        "user_query": "Will the Pies beat the Cats this week?",
        "messages": [],
        "detected_intent": "",
        "entities": {},
        "tool_results": {},
        "validation_status": "",
        "clarification_prompt": None,
        "final_response": ""
    }
    out = afl_app.invoke(state)
    print("\n--- FINAL RESPONSE ---")
    print(out["final_response"])
