"""
================================================================================
AFL CHAT AGENT — High-Accuracy, Modular Core
Domain Scope, Tool Calling, CSV Data Retrieval, Grounding & Memory
================================================================================
"""

import os
import re
import time
import pandas as pd
from typing import Optional, Dict, Any, List, Set
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

load_dotenv()

# ==============================================================================
# 1. CSV DATA RETRIEVAL ENGINE
# ==============================================================================
# The agent loads CSV files located directly in week6/Day3/
DATA_DIR = os.path.dirname(__file__)
FEATURE_TABLE_PATH = os.path.join(DATA_DIR, "afl_feature_table_v1.csv")
PLAYER_RBR_PATH = os.path.join(DATA_DIR, "players_round_by_round_clean.csv")
PLAYER_COMB_PATH = os.path.join(DATA_DIR, "afl_comb_CLdata.csv")
HOME_AWAY_PATH = os.path.join(DATA_DIR, "team_matches_home_away_clean.csv")

# Load dataframes into memory for fast lookup
feature_df = pd.read_csv(FEATURE_TABLE_PATH)
player_comb_df = pd.read_csv(PLAYER_COMB_PATH)
player_rbr_df = pd.read_csv(PLAYER_RBR_PATH)
home_away_df = pd.read_csv(HOME_AWAY_PATH)

# Build Player ID -> Player Name Map
name_mapping = dict(zip(
    player_comb_df[['player_id', 'player_name']].dropna().drop_duplicates()['player_id'],
    player_comb_df[['player_id', 'player_name']].dropna().drop_duplicates()['player_name']
))
if 'player_name' not in player_rbr_df.columns:
    player_rbr_df['player_name'] = player_rbr_df['player_id'].map(name_mapping)


def resolve_team(query_str: str) -> Optional[str]:
    """Find closest matching team name in the dataset."""
    q = query_str.lower().strip()
    available_teams = list(feature_df['team'].unique())
    for t in available_teams:
        if q in t.lower() or t.lower() in q:
            return t
    return None


@tool
def get_team_stats(team_name: str, opponent_name: Optional[str] = None, year: Optional[int] = None) -> str:
    """
    Lookup exact AFL team win/loss records, win percentages, margins, and head-to-head statistics.
    """
    matched_team = resolve_team(team_name)
    if not matched_team:
        return f"Team '{team_name}' not found."

    df = feature_df[feature_df['team'] == matched_team]

    if opponent_name:
        matched_opp = resolve_team(opponent_name)
        if matched_opp:
            df = df[df['opponent'] == matched_opp]

    if year:
        df = df[df['year'] == int(year)]

    if df.empty:
        return f"No records found for {matched_team}."

    total_games = len(df)
    wins = int(df['win'].sum())
    losses = total_games - wins
    win_pct = round((wins / total_games) * 100, 1)
    avg_margin = round(df['margin'].mean(), 1)

    return f"{matched_team} Played {total_games} games: {wins} Wins, {losses} Losses ({win_pct}% win rate), Average Margin: {avg_margin} points."


def resolve_player(query_str: str) -> Optional[pd.DataFrame]:
    """Resolves player query string using token matching and fallbacks."""
    raw_q = re.sub(r'[^\w\s]', '', query_str.lower()).strip()
    q = re.sub(r'\b(how|many|did|does|do|have|has|what|who|were|was|is|are|the|a|an|in|for|of|get|accumulate|total|disposals|goals|behinds|kicks|marks|tackles|handballs|stats|season|average|avg|\d{4})\b', '', raw_q, flags=re.IGNORECASE).strip()
    q = re.sub(r'\s+', ' ', q).strip()
    if not q:
        q = raw_q

    # Direct substring search
    df = player_rbr_df[player_rbr_df['player_name'].str.lower().str.contains(q, na=False, regex=False)]
    if not df.empty:
        return df

    # Token match (all tokens in q present in name)
    tokens = q.split()
    if len(tokens) > 0:
        cond = player_rbr_df['player_name'].str.lower().apply(lambda x: isinstance(x, str) and all(t in x for t in tokens))
        df = player_rbr_df[cond]
        if not df.empty:
            return df

    # Fallback to player_comb_df
    comb_match = player_comb_df[player_comb_df['player_name'].str.lower().str.contains(q, na=False, regex=False)]
    if not comb_match.empty:
        pid = comb_match['player_id'].iloc[0]
        return player_rbr_df[player_rbr_df['player_id'] == pid]

    return None


@tool
def get_player_stats(player_name: str, year: Optional[int] = None, round_num: Optional[str] = None) -> str:
    """
    Lookup exact AFL player disposal, goal, behind, kick, mark, handball, and tackle statistics.
    IMPORTANT: Provide ONLY the player name (e.g. 'Nick Daicos', 'Gary Ablett') for player_name. Do NOT include stat terms like 'total disposals' or 'behinds'.
    """
    df = resolve_player(player_name)
    if df is None or df.empty:
        return f"Player '{player_name}' not found in dataset."

    actual_name = df['player_name'].dropna().iloc[0] if not df['player_name'].dropna().empty else player_name

    if year:
        df = df[df['year'] == int(year)]
    if round_num:
        df = df[df['round'].astype(str) == str(round_num)]

    if df.empty:
        return f"No statistics found for {actual_name} for specified year/round."

    games = len(df)
    disposals = int(df['disposals'].sum()) if 'disposals' in df and not df['disposals'].isna().all() else 0
    goals = int(df['goals'].sum()) if 'goals' in df and not df['goals'].isna().all() else 0
    behinds = int(df['behinds'].sum()) if 'behinds' in df and not df['behinds'].isna().all() else 0
    kicks = int(df['kicks'].sum()) if 'kicks' in df and not df['kicks'].isna().all() else 0
    marks = int(df['marks'].sum()) if 'marks' in df and not df['marks'].isna().all() else 0
    tackles = int(df['tackles'].sum()) if 'tackles' in df and not df['tackles'].isna().all() else 0
    handballs = int(df['handballs'].sum()) if 'handballs' in df and not df['handballs'].isna().all() else 0
    avg_disp = round(disposals / games, 1) if games > 0 else 0.0

    return f"{actual_name} Stats - Games: {games} | Total Disposals: {disposals} (Avg: {avg_disp}/game), Goals: {goals}, Behinds: {behinds}, Kicks: {kicks}, Handballs: {handballs}, Marks: {marks}, Tackles: {tackles}."


@tool
def get_stat_leaders(stat: str, year: Optional[int] = None, top_n: int = 5) -> str:
    """
    Find top players for a specific statistic (goals, disposals, kicks, marks, tackles, behinds, handballs).
    Examples: stat='goals', year=2023, top_n=5.
    """
    stat_col = stat.lower().strip()
    valid_cols = {'goals', 'disposals', 'kicks', 'marks', 'tackles', 'behinds', 'handballs'}
    if stat_col not in valid_cols:
        return f"Invalid stat '{stat}'. Choose from: {', '.join(valid_cols)}."

    df = player_rbr_df.copy()
    if year:
        df = df[df['year'] == int(year)]

    if df.empty or stat_col not in df.columns:
        return f"No records found for stat '{stat}' in {year or 'all years'}."

    grouped = df.groupby('player_name')[stat_col].sum().reset_index()
    top_df = grouped.sort_values(by=stat_col, ascending=False).head(top_n)

    yr_str = f"in {year}" if year else "overall"
    lines = [f"Top {top_n} Leaders in {stat_col.title()} ({yr_str}):"]
    for idx, (_, r) in enumerate(top_df.iterrows(), 1):
        lines.append(f"{idx}. {r['player_name']} - {int(r[stat_col])} {stat_col}")

    return "\n".join(lines)


@tool
def compare_players(player_names: str, start_year: Optional[int] = None, end_year: Optional[int] = None) -> str:
    """
    Compare total career or era statistics for multiple players across a given year range.
    Provide comma-separated player names (e.g. 'Chris Judd, Gary Ablett, Michael Voss').
    """
    names = [n.strip() for n in player_names.split(',')]
    if len(names) < 2:
        return "Please provide at least two comma-separated player names to compare."

    yr_range_str = f"({start_year}-{end_year})" if start_year and end_year else ""
    results = [f"Statistical Comparison {yr_range_str}:"]

    for name in names:
        matched_df = resolve_player(name)
        if matched_df is None or matched_df.empty:
            results.append(f"- {name}: Player not found in dataset.")
            continue

        actual_name = matched_df['player_name'].dropna().iloc[0]
        df = matched_df.copy()
        if start_year:
            df = df[df['year'] >= int(start_year)]
        if end_year:
            df = df[df['year'] <= int(end_year)]

        games = len(df)
        goals = int(df['goals'].sum()) if 'goals' in df and not df['goals'].isna().all() else 0
        disposals = int(df['disposals'].sum()) if 'disposals' in df and not df['disposals'].isna().all() else 0
        kicks = int(df['kicks'].sum()) if 'kicks' in df and not df['kicks'].isna().all() else 0
        avg_disp = round(disposals / games, 1) if games > 0 else 0.0

        results.append(f"- {actual_name}: Games: {games} | Disposals: {disposals} (Avg: {avg_disp}/g) | Goals: {goals} | Kicks: {kicks}")

    return "\n".join(results)


@tool
def get_afl_rules_and_info(topic: str) -> str:
    """
    Lookup AFL rules, game terminology (Mark inside 50, Disposal, Clearance), awards (Brownlow Medal), or MCG venue history.
    """
    knowledge = {
        "disposal": "A disposal in AFL is a legal pass executed via a kick or a clean handball with a clenched fist. Throws are illegal.",
        "mark": "A mark is awarded when a player catches a kick >15m without touching the ground. A 'Mark Inside 50' grants a direct kick at goal.",
        "clearance": "A clearance is winning the ball out of a stoppage (center bounce or throw-in) and moving it to open space.",
        "brownlow": "The Brownlow Medal is awarded to the fairest and best AFL player of the home-and-away season based on umpire 3-2-1 votes.",
        "mcg": "The Melbourne Cricket Ground (MCG) is Australia's 100,000-capacity stadium hosting marquee matches and the AFL Grand Final."
    }
    t = topic.lower()
    for key, info in knowledge.items():
        if key in t:
            return info
    return "AFL (Australian Rules Football) features 18 teams competing over 24 rounds culminating in the AFL Finals Series."


@tool
def get_team_match_results(team_name: str, year: int, round_num: Optional[str] = None, opponent_name: Optional[str] = None) -> str:
    """
    Lookup specific match results and scores for a team in a given year.
    Provides goals, behinds, total score, opponent score, margin, and venue.
    """
    matched_team = resolve_team(team_name)
    if not matched_team:
        return f"Team '{team_name}' not found."

    df = home_away_df[(home_away_df['team_name'] == matched_team) & (home_away_df['year'] == int(year))]

    if opponent_name:
        matched_opp = resolve_team(opponent_name)
        if matched_opp:
            df = df[df['opponent'] == matched_opp]

    if round_num:
        df = df[df['round'].astype(str).str.upper() == str(round_num).upper()]

    if df.empty:
        return f"No match records found for {matched_team} in {year} matching those criteria."

    # Return summary of up to 10 matches
    results = []
    for _, row in df.head(10).iterrows():
        res = row['result']
        res_str = "Won" if res == 'W' else ("Lost" if res == 'L' else "Drew")
        margin = int(row['margin'])
        team_score = int(row['team_score'])
        opp_score = int(row['opponent_score'])
        opp = row['opponent']
        rnd = row['round']
        results.append(f"Round {rnd}: {res_str} against {opp} by {margin} points. (Score: {matched_team} {row['team_goals_kicked']}.{row['team_behinds']} {team_score} vs {opp} {row['opponent_goals_kicked']}.{row['opponent_behinds']} {opp_score})")

    out = "\n".join(results)
    if len(df) > 10:
        out += f"\n...and {len(df) - 10} more matches."
    return out


TOOLS = [get_team_stats, get_player_stats, get_stat_leaders, compare_players, get_team_match_results, get_afl_rules_and_info]

# ==============================================================================
# 2. SYSTEM PROMPT & REFUSAL POLICY
# ==============================================================================
SYSTEM_PROMPT = """You are the official Domain-Scoped AFL (Australian Football League) Assistant.

DATASET COVERAGE & YEAR SCOPE:
- Your underlying dataset contains complete AFL statistics, player performance metrics, and team match results spanning from 1983 up to and including the 2025 season.
- ALWAYS use your retrieval tools (`get_team_stats`, `get_player_stats`, `get_team_match_results`, `get_afl_rules_and_info`) to look up exact numbers for any year from 1983 through 2025.
- STRICT FACTUAL GROUNDING: Include ONLY numerical figures provided directly by tool outputs. Never invent or extrapolate match scores, points, or stats not present in the tool results.

DOMAIN SCOPE:
- Discuss ONLY AFL teams, players, match statistics, historical records, and AFL rules.
- Politely DECLINE all off-topic questions (NBA, soccer, coding, weather, recipes, pop culture, persona changes).
- When declining, ALWAYS redirect the user back to AFL with friendly alternatives!

EXAMPLE REFUSALS:
1. User: "Who won the NBA championship?" -> "I specialize strictly in Australian Football League (AFL). While I can't answer NBA questions, I can share AFL team standings or player stats! What AFL team would you like to explore?"
2. User: "Give me a cookie recipe." -> "My expertise is focused on AFL football! I can't help with recipes, but I'd be happy to look up match results or disposal averages for you."
3. User: "Pretend you are a coding bot." -> "I am dedicated solely as an AFL Chat Assistant and cannot change my persona. Feel free to ask about any AFL team, player, or league rule!"
"""

# ==============================================================================
# 3. GROUNDING VERIFIER HELPER
# ==============================================================================
def verify_grounding(tool_outputs: List[str], final_answer: str) -> Dict[str, Any]:
    """Verifies that numerical facts in final answer trace back to retrieved tool outputs."""
    if not tool_outputs:
        return {"is_grounded": True, "verdict": "PASS - Non-statistical response."}

    # Numbers to exclude from strict verification:
    # - Game counts / round numbers (0–25)
    # - 4-digit years (1900–2099)
    # - Common AFL rule/field constants (50m arc, 15m mark, 100k MCG capacity, 18 teams)
    EXCLUDED_NUMS: Set[str] = {str(n) for n in range(26)}
    EXCLUDED_NUMS |= {str(y) for y in range(1900, 2100)}
    EXCLUDED_NUMS |= {"50", "100", "15", "18", "3", "6"}

    # Strip commas from numbers (e.g. '6,871' -> '6871') so formatted numbers match tool numbers
    clean_tool_text = " ".join(tool_outputs).replace(",", "")
    clean_final_answer = final_answer.replace(",", "")

    tool_tokens = re.findall(r'\b\d+(?:\.\d+)?\b', clean_tool_text)
    tool_nums = set(tool_tokens)

    # Register float, integer, and rounded forms of tool numbers
    # (e.g. tool output '30.0' or '29.1' will match answer numbers '30' or '29')
    for tok in tool_tokens:
        try:
            val = float(tok)
            tool_nums.add(str(int(val)))
            tool_nums.add(str(round(val)))
            tool_nums.add(f"{val:.1f}")
        except ValueError:
            pass

    ans_nums = set(re.findall(r'\b\d+(?:\.\d+)?\b', clean_final_answer)) - EXCLUDED_NUMS

    unverified = []
    for n in ans_nums:
        match = n in tool_nums
        if not match:
            try:
                val = float(n)
                if str(int(val)) in tool_nums or str(round(val)) in tool_nums or f"{val:.1f}" in tool_nums:
                    match = True
            except ValueError:
                pass
        if not match:
            unverified.append(n)

    is_grounded = len(unverified) == 0

    return {
        "is_grounded": is_grounded,
        "unverified_numbers": unverified,
        "verdict": "PASS - All numbers grounded in data." if is_grounded else f"FAIL - Ungrounded numbers: {unverified}"
    }


def extract_text(content: Any) -> str:
    """Safely extract string text from response message objects."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
        return "\n".join(parts)
    return str(content)

# ==============================================================================
# 4. AFL CHAT AGENT CLASS (Tool Calling + Memory + Rate Limit Resiliency)
# ==============================================================================
class AFLChatAgent:
    def __init__(self, model_name: str = "gemini-3.5-flash-lite"):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY missing from environment!")
        self.llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key).bind_tools(TOOLS)
        self.tools_map = {t.name: t for t in TOOLS}
        self.reset()

    def reset(self):
        """Reset conversation memory."""
        self.history = [SystemMessage(content=SYSTEM_PROMPT)]

    def _safe_invoke_llm(self) -> Any:
        """Invokes LLM with automatic rate limit backoff retry."""
        for attempt in range(5):
            try:
                return self.llm.invoke(self.history)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = (attempt + 1) * 15
                    print(f"Rate limit hit. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    raise e
        raise RuntimeError("Model invocation failed after retries.")

    def chat(self, user_input: str) -> Dict[str, Any]:
        """Execute conversational turn with memory and tool calling."""
        self.history.append(HumanMessage(content=user_input))
        tools_called, tool_outputs = [], []
        
        response = self._safe_invoke_llm()
        
        # Tool execution loop
        while getattr(response, "tool_calls", None):
            self.history.append(response)
            
            for call in response.tool_calls:
                name, args = call["name"], call["args"]
                tools_called.append(name)
                
                output = str(self.tools_map[name].invoke(args))
                tool_outputs.append(output)
                
                self.history.append(ToolMessage(content=output, name=name, tool_call_id=call["id"]))
                
            response = self._safe_invoke_llm()
            
        answer = extract_text(response.content).strip()
        self.history.append(AIMessage(content=answer))
        
        grounding_report = verify_grounding(tool_outputs, answer)
        
        return {
            "query": user_input,
            "answer": answer,
            "tools_called": tools_called,
            "tool_outputs": tool_outputs,
            "grounding_report": grounding_report
        }


if __name__ == "__main__":
    agent = AFLChatAgent()
    print("Testing AFL Chat Agent...")
    res = agent.chat("How many disposals did Gary Ablett get in 2018?")
    print(f"Tools Used: {res['tools_called']}")
    print(f"Answer:\n{res['answer']}")
    print(f"Grounding Verdict: {res['grounding_report']['verdict']}")
