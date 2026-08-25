"""
LangGraph Orchestrated AFL Assistant
Domain-locked chat & prediction state machine for AFL.
"""

import os
import re
import sys
import pandas as pd
from typing import TypedDict, List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

from prediction_tools import (
    predict_match_winner, predict_top_player, predict_season_premier,
    resolve_team_alias, TEAM_ALIASES, feature_df
)
from afl_chat_agent import (
    get_team_stats, get_player_stats, get_team_match_results,
    get_stat_leaders, compare_players, get_afl_rules_and_info,
    get_goat_player, home_away_df, resolve_team, resolve_player
)

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.0)


class AFLAgentState(TypedDict):
    user_query: str
    messages: List[BaseMessage]
    detected_intent: str
    entities: Dict[str, Any]
    tool_results: Dict[str, Any]
    validation_status: str
    clarification_prompt: Optional[str]
    final_response: str


def _extract_player_names(query: str) -> List[str]:
    official_teams = set(TEAM_ALIASES.values())
    EXCLUDED_TITLES = {
        "Grand Final", "Brownlow Medal", "Super Bowl", "Premier League",
        "World Cup", "Coleman Medal", "All Australian", "Rising Star", "Afl Grand"
    }
    pattern = r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)\b'
    return [name for name in re.findall(pattern, query) if name not in official_teams and name not in EXCLUDED_TITLES]


_OFF_TOPIC_KEYWORDS = [
    "nba", "nfl", "nhl", "nrl", "rugby", "soccer", "premier league", "champions league",
    "world cup", "cricket", "tennis", "golf", "formula 1", "f1", "python", "quicksort",
    "code", "script", "programming", "algorithm", "machine learning", "stocks",
    "financial advisor", "investment", "crypto", "bitcoin", "ethereum", "weather",
    "recipe", "politics", "translate", "french", "spanish", "german", "act as", "pretend",
    "forget afl", "jailbreak", "dan mode", "dan activated", "stock price", "you are now"
]


def intent_router_node(state: AFLAgentState) -> AFLAgentState:
    query = state["user_query"].strip()
    q_lower = query.lower()

    if any(kw in q_lower for kw in _OFF_TOPIC_KEYWORDS):
        state["detected_intent"] = "off_topic"
        state["entities"] = {}
        return state

    pred_kw = [
        "will win", "predict", "winner", "will beat", "odds", "probabilit",
        "top-score", "top scorer", "forecast", "chance", "who will lead", "next match",
        "this week", "next week", "upcoming", "chances to win", "most chances",
        "afl final", "grand final winner", "premiership", "upcoming season",
        "2026", "2027", "2030", "going to win"
    ]
    retrieval_kw = ["disposals", "goals", "behinds", "kicks", "marks", "tackles", "how many", "scores", "record", "average", "win rate", "did", "was", "compare", "leaderboard", "leader", "leaders", "most"]
    factual_kw = ["rule", "mark inside 50", "brownlow", "mcg", "definition", "explain"]

    will_beat = re.search(r'\bwill\b.{1,40}\bbeat\b', q_lower)
    is_pred = bool(will_beat) or any(w in q_lower for w in pred_kw) or bool(re.search(r'\b(202[6-9]|20[3-9]\d)\b', query))

    if is_pred:
        state["detected_intent"] = "prediction"
    elif any(w in q_lower for w in retrieval_kw):
        state["detected_intent"] = "retrieval"
    elif any(w in q_lower for w in factual_kw):
        state["detected_intent"] = "factual"
    else:
        state["detected_intent"] = "retrieval"

    state["entities"] = extract_entities(query)
    return state


def extract_entities(query: str) -> Dict[str, Any]:
    q_lower = query.lower()
    entities: Dict[str, Any] = {}

    teams_found = []
    for alias, official in TEAM_ALIASES.items():
        if len(alias) >= 3 and re.search(r'\b' + re.escape(alias) + r'\b', q_lower):
            if official not in teams_found:
                teams_found.append(official)

    if len(teams_found) >= 2:
        entities["team_a"], entities["team_b"] = teams_found[0], teams_found[1]
    elif len(teams_found) == 1:
        entities["team_a"] = teams_found[0]

    for stat in ["disposals", "goals", "kicks", "marks", "tackles", "handballs", "behinds"]:
        if stat in q_lower:
            entities["stat_type"] = stat
            break

    yr_range = re.search(r'\b(19\d{2}|20\d{2})\b.*?\b(19\d{2}|20\d{2})\b', query)
    if yr_range:
        entities["start_year"] = int(yr_range.group(1))
        entities["end_year"] = int(yr_range.group(2))
        entities["year"] = int(yr_range.group(2))
    else:
        yr_match = re.search(r'\b(19\d\d|20\d\d)\b', query)
        if yr_match:
            entities["year"] = int(yr_match.group(1))

    players = _extract_player_names(query)
    if len(players) >= 2:
        entities["multi_player"] = players
    elif len(players) == 1:
        entities["player_name"] = players[0]

    return entities


def prediction_node(state: AFLAgentState) -> AFLAgentState:
    query = state["user_query"].lower()
    entities = state.get("entities", {})

    if any(w in query for w in ["upcoming season", "final", "grand final", "premier", "chances to win", "most chances", "season winner", "2026", "2027", "2030"]):
        res = predict_season_premier(entities.get("year"))
        state["tool_results"] = {"type": "season_prediction", "data": res}
    elif "team_a" in entities and "team_b" in entities:
        res = predict_match_winner(entities["team_a"], entities["team_b"])
        state["tool_results"] = {"type": "match_prediction", "data": res}
    elif "player_name" in entities:
        pdf = resolve_player(entities["player_name"])
        team = pdf["team"].dropna().iloc[-1] if pdf is not None and not pdf.empty and "team" in pdf.columns else "Carlton Blues"
        res = predict_top_player(team, entities.get("stat_type", "disposals"))
        state["tool_results"] = {"type": "player_prediction", "data": res}
    elif "stat_type" in entities or any(w in query for w in ["lead", "top", "scorer", "disposals", "goals", "kicks", "marks", "tackles", "players"]):
        team_target = entities.get("team_a")
        stat_type = entities.get("stat_type", "disposals" if "disposals" in query else "goals")
        top_n = 5 if any(w in query for w in ["top 5", "top five", "5 players", "best 5"]) or not team_target else 1
        res = predict_top_player(team_target, stat_type, top_n=top_n)
        state["tool_results"] = {"type": "player_prediction", "data": res}
    elif "team_a" in entities:
        team = entities["team_a"]
        rival = "Collingwood Magpies" if team != "Collingwood Magpies" else "Geelong Cats"
        res = predict_match_winner(team, rival)
        state["tool_results"] = {"type": "match_prediction", "data": res}
    else:
        res = predict_season_premier()
        state["tool_results"] = {"type": "season_prediction", "data": res}

    return state


def retrieval_node(state: AFLAgentState) -> AFLAgentState:
    query = state["user_query"]
    q_lower = query.lower()
    entities = state.get("entities", {})
    results = {}

    # Pre-1983 year guard
    old_yr = re.search(r'\b(18\d\d|19[0-7]\d)\b', query)
    if old_yr:
        results["out_of_range"] = f"My AFL dataset covers history from 1983 through 2025. Records for {old_yr.group(1)} are outside coverage."
        state["tool_results"] = {"type": "retrieval", "data": results}
        return state

    # GOAT query
    if any(kw in q_lower for kw in ["greatest of all time", "goat", "best ever", "all time great", "greatest player", "greatest afl", "afl legend", "all time greatest"]) or ("greatest" in q_lower and "all time" in q_lower):
        results["goat"] = get_goat_player()

    # Stat leaders / leaderboard
    elif any(kw in q_lower for kw in ["top", "leader", "leaders", "leads", "most", "who leads", "total disposals", "total goals"]):
        stat = entities.get("stat_type", "goals")
        yr = entities.get("year")
        results["stat_leaders"] = get_stat_leaders.invoke({"stat": stat, "year": yr})

    # Team win rate
    elif any(kw in q_lower for kw in ["best team", "which team", "team win rate", "win rate", "won most"]) and "team_a" not in entities:
        if not feature_df.empty and "win" in feature_df.columns:
            df = feature_df.copy()
            start_yr, end_yr, yr = entities.get("start_year"), entities.get("end_year"), entities.get("year")
            if start_yr and end_yr:
                df = df[(df["year"] >= start_yr) & (df["year"] <= end_yr)]
            elif yr:
                df = df[df["year"] == yr]
            ranked = df.groupby("team")["win"].mean().reset_index().sort_values("win", ascending=False).head(5)
            yr_label = f"{start_yr}–{end_yr}" if start_yr and end_yr else (str(yr) if yr else "all seasons")
            lines = [f"Top 5 teams by win rate ({yr_label}):"]
            for i, (_, row) in enumerate(ranked.iterrows(), 1):
                lines.append(f"  {i}. {row['team']}: {round(row['win'] * 100, 1)}% win rate")
            results["team_leaderboard"] = "\n".join(lines)

    # Multi-player comparison
    elif "multi_player" in entities:
        results["comparison"] = compare_players.invoke({
            "player_names": ", ".join(entities["multi_player"]),
            "start_year": entities.get("start_year") or entities.get("year"),
            "end_year": entities.get("end_year") or entities.get("year")
        })

    # Single player stats
    elif "player_name" in entities:
        pname = entities["player_name"]
        start_yr, end_yr = entities.get("start_year"), entities.get("end_year")
        if start_yr and end_yr:
            results["player_stats"] = "\n".join([f"[{y}] {get_player_stats.invoke({'player_name': pname, 'year': y})}" for y in range(start_yr, end_yr + 1)])
        else:
            results["player_stats"] = get_player_stats.invoke({"player_name": pname, "year": entities.get("year")})

    # Head-to-Head team query
    elif "team_a" in entities and "team_b" in entities:
        team_a, team_b = entities["team_a"], entities["team_b"]
        m_a, m_b = resolve_team(team_a), resolve_team(team_b)
        df = home_away_df.copy()
        if entities.get("year"):
            df = df[df["year"] == entities["year"]]
        if m_a and m_b:
            sub = df[(df["team_name"] == m_a) & (df["opponent"] == m_b)]
            if "away" in q_lower:
                sub = sub[sub["home_away"].str.upper() == "A"]
            elif "home" in q_lower:
                sub = sub[sub["home_away"].str.upper() == "H"]
            if not sub.empty:
                wins = len(sub[sub["result"].str.upper() == "W"])
                losses = len(sub[sub["result"].str.upper() == "L"])
                draws = len(sub[sub["result"].str.upper() == "D"])
                win_pct = round((wins / len(sub)) * 100, 1)
                draw_str = f", {draws} Draws" if draws > 0 else ""
                results["h2h_stats"] = f"{team_a} against {team_b}: Played {len(sub)} matches — {wins} Wins, {losses} Losses{draw_str} ({win_pct}% win rate)."
            else:
                results["h2h_stats"] = f"No match records found between {team_a} and {team_b}."

    elif "team_a" in entities and "year" in entities:
        results["match_results"] = get_team_match_results.invoke({"team_name": entities["team_a"], "year": entities["year"]})
    elif "team_a" in entities:
        results["team_stats"] = get_team_stats.invoke({"team_name": entities["team_a"]})
    else:
        results["player_stats"] = "Could not identify specific AFL entity. Please specify player or team."

    state["tool_results"] = {"type": "retrieval", "data": results}
    return state


def direct_answer_node(state: AFLAgentState) -> AFLAgentState:
    state["tool_results"] = {"type": "factual", "data": get_afl_rules_and_info.invoke({"topic": state["user_query"]})}
    return state


def refusal_node(state: AFLAgentState) -> AFLAgentState:
    q = state["user_query"].lower()
    if any(k in q for k in ["python", "code", "script"]):
        resp = "I am dedicated solely as an AFL Chat Assistant and cannot help with programming tasks."
    elif any(k in q for k in ["stocks", "crypto", "investment"]):
        resp = "I'm an AFL-dedicated assistant and can't provide financial advice."
    elif any(k in q for k in ["translate", "french", "spanish"]):
        resp = "Translation is outside my domain — I'm your AFL intelligence engine!"
    else:
        resp = "My expertise is focused exclusively on AFL football! Ask me any AFL question."

    state["final_response"] = resp
    state["validation_status"] = "VALID"
    return state


def validation_node(state: AFLAgentState) -> AFLAgentState:
    res_data = state.get("tool_results", {}).get("data", {})
    if isinstance(res_data, dict) and res_data.get("status") == "ERROR":
        state["validation_status"] = "NEEDS_CLARIFICATION"
        state["clarification_prompt"] = res_data.get("message", "Please clarify your request.")
    else:
        state["validation_status"] = "VALID"
    return state


def clarification_node(state: AFLAgentState) -> AFLAgentState:
    state["final_response"] = f"CLARIFICATION REQUIRED: {state.get('clarification_prompt', 'Please specify full team or player names.')}"
    return state


def response_formatter_node(state: AFLAgentState) -> AFLAgentState:
    intent = state.get("detected_intent")
    tool_res = state.get("tool_results", {})
    res_type = tool_res.get("type")
    res_data = tool_res.get("data", {})

    if intent == "prediction" and res_type == "match_prediction":
        winner, prob = res_data["predicted_winner"], res_data["win_probability"]
        loser, loser_prob = res_data["loser"], res_data["loser_probability"]
        conf = res_data["confidence"]
        feats = "\n".join([f"  - {f}" for f in res_data["driving_features"]])
        disc = res_data["disclaimer"]

        state["final_response"] = f"""Probabilistic match forecast:

* **Predicted Winner:** **{winner}** ({prob}% probability)
* **Opponent:** {loser} ({loser_prob}% probability)
* **Model Confidence:** **{conf}**

**Key Driving Features:**
{feats}

> *{disc}*"""

    elif intent == "prediction" and res_type == "player_prediction":
        player, stat = res_data["predicted_player"], res_data["stat_type"]
        avg, peak = res_data["expected_average"], res_data["recent_peak"]
        team, conf = res_data["team"], res_data["confidence"]
        feats = "\n".join([f"  - {f}" for f in res_data["driving_features"]])
        disc = res_data["disclaimer"]
        top_players = res_data.get("top_players", [])

        if len(top_players) > 1:
            plist = "\n".join([f"  #{p['rank']}. **{p['player_name']}** ({p['team']}) — ~{p['expected_average']} {stat.lower()}/match (Peak: {p['recent_peak']})" for p in top_players])
            state["final_response"] = f"""Probabilistic Top {len(top_players)} Player Forecast ({stat}) for **{team}**:

{plist}

* **Model Confidence:** **{conf}**

**Key Driving Factors:**
{feats}

> *{disc}*"""
        else:
            state["final_response"] = f"""Probabilistic player forecast for **{team}**:

* **Top Performer Expectation:** **{player}** ({stat})
* **Projected Average:** ~{avg} {stat.lower()} per match (Recent Peak: {peak})
* **Model Confidence:** **{conf}**

**Key Driving Factors:**
{feats}

> *{disc}*"""

    elif intent == "prediction" and res_type == "season_prediction":
        winner, prob = res_data["predicted_winner"], res_data["win_probability"]
        yr, conf = res_data["target_year"], res_data["confidence"]
        runners = "\n".join(res_data["runners_up"])
        feats = "\n".join([f"  - {f}" for f in res_data["driving_features"]])
        disc = res_data["disclaimer"]

        state["final_response"] = f"""Probabilistic season forecast for **{yr}**:

* **Predicted Champion / Highest Chance:** **{winner}** ({prob}% win probability)
* **Model Confidence:** **{conf}**

**Top Contenders & Runners-Up:**
{runners}

**Key Driving Features:**
{feats}

> *{disc}*"""

    elif intent == "retrieval":
        val = next(iter(res_data.values())) if isinstance(res_data, dict) and res_data else res_data
        state["final_response"] = str(val)
    elif intent == "factual":
        state["final_response"] = str(res_data)

    return state


def route_by_intent(state: AFLAgentState) -> str:
    intent = state.get("detected_intent", "retrieval")
    return "prediction_node" if intent == "prediction" else ("retrieval_node" if intent == "retrieval" else ("direct_answer_node" if intent == "factual" else "refusal_node"))


def route_by_validation(state: AFLAgentState) -> str:
    status = state.get("validation_status", "VALID")
    return "clarification_node" if status == "NEEDS_CLARIFICATION" else ("END" if status == "OUT_OF_SCOPE" else "response_formatter_node")


def build_afl_graph():
    workflow = StateGraph(AFLAgentState)
    workflow.add_node("intent_router", intent_router_node)
    workflow.add_node("prediction_node", prediction_node)
    workflow.add_node("retrieval_node", retrieval_node)
    workflow.add_node("direct_answer_node", direct_answer_node)
    workflow.add_node("refusal_node", refusal_node)
    workflow.add_node("validation_node", validation_node)
    workflow.add_node("clarification_node", clarification_node)
    workflow.add_node("response_formatter_node", response_formatter_node)

    workflow.set_entry_point("intent_router")
    workflow.add_conditional_edges("intent_router", route_by_intent, {
        "prediction_node": "prediction_node", "retrieval_node": "retrieval_node",
        "direct_answer_node": "direct_answer_node", "refusal_node": "refusal_node"
    })
    workflow.add_edge("prediction_node", "validation_node")
    workflow.add_edge("retrieval_node", "validation_node")
    workflow.add_conditional_edges("validation_node", route_by_validation, {
        "clarification_node": "clarification_node", "response_formatter_node": "response_formatter_node", "END": END
    })
    workflow.add_edge("direct_answer_node", "response_formatter_node")
    workflow.add_edge("response_formatter_node", END)
    workflow.add_edge("clarification_node", END)
    workflow.add_edge("refusal_node", END)

    return workflow.compile()


afl_app = build_afl_graph()
