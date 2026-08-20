"""
predict.py — AFL Prediction Model Inference Module
===================================================
Exposes two clean prediction functions ready to be wrapped as LangChain/LangGraph
agent tools on Day 4:

    predict_match_winner(team_a, team_b, date, home_team=None)
        -> {"winner": str, "probability": float, "confidence": str, "details": dict}

    predict_top_player(team, match_date, n=5, stat_type="fantasy_points")
        -> {"ranked_players": list[dict], "match_date": str, "team": str}

Usage
-----
    from predict import predict_match_winner, predict_top_player

    result = predict_match_winner("Brisbane Lions", "Collingwood Magpies", "2024-08-10", home_team="Brisbane Lions")
    print(result)

    top5 = predict_top_player("Brisbane Lions", "2024-08-10", n=5)
    print(top5)

Artifacts required in the same directory:
    match_winner_model.joblib     -- HistGradientBoosting pipeline
    top_player_model.joblib       -- GradientBoosting regression pipeline
    afl_feature_table_v1.csv      -- pre-built team-match feature table
    player_career_averages.csv    -- per-player career average fantasy points
    players_round_by_round_clean.csv -- raw player-game data
    valid_teams.csv               -- list of known team names
"""

import os, re, warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
_DIR = Path(__file__).parent

# ── Feature lists (must match training) ──────────────────────────────────────
MW_FEATURES = [
    "roll3_win", "roll5_win", "roll3_goals", "roll5_goals",
    "roll3_disposals", "roll5_disposals",
    "h2h_winrate", "h2h_cumgames",
    "is_home", "rest_days", "rest_advantage",
    "season_winpct", "win_streak", "loss_streak",
    "venue_winrate",
]

PP_FEATURES = [
    "roll3_fantasy_points", "roll5_fantasy_points", "roll10_fantasy_points",
    "career_avg_fp", "games_played",
    "roll3_goals_filled", "roll5_goals_filled", "career_avg_goals",
    "roll3_disposals", "roll5_disposals",
    "roll3_kicks", "roll5_kicks",
    "roll3_marks", "roll5_marks",
    "roll3_tackles", "roll5_tackles",
    "is_home", "rest_days",
]

# ── Lazy-load models and data (load once on first call) ───────────────────────
_cache = {}


def _load():
    """Load all models and lookup tables into _cache on first call."""
    if _cache:
        return

    # Models
    _cache["mw_model"] = joblib.load(_DIR / "match_winner_model.joblib")
    _cache["pp_model"] = joblib.load(_DIR / "top_player_model.joblib")

    # Feature table for team history lookup
    _cache["feat_table"] = pd.read_csv(
        _DIR / "afl_feature_table_v1.csv", parse_dates=["match_date"]
    )

    # Player career averages for ranking fallback
    _cache["player_career"] = pd.read_csv(_DIR / "player_career_averages.csv")

    # Valid team names
    _cache["valid_teams"] = set(
        pd.read_csv(_DIR / "valid_teams.csv")["team"].dropna().tolist()
    )

    # Player rolling stats (for top-player model)
    rbr = pd.read_csv(
        _DIR / "players_round_by_round_clean.csv",
        low_memory=False, parse_dates=["match_date"]
    )
    rbr_sorted = rbr.sort_values(["player_id", "match_date"]).copy()
    rbr_sorted["goals_filled"] = rbr_sorted["goals"].fillna(0)

    for w in [3, 5, 10]:
        for col in ["fantasy_points", "goals_filled", "disposals", "kicks", "marks", "tackles"]:
            rbr_sorted[f"roll{w}_{col}"] = (
                rbr_sorted.groupby("player_id")[col]
                .transform(lambda s: s.shift(1).rolling(w, min_periods=1).mean())
            )

    rbr_sorted["career_avg_fp"] = (
        rbr_sorted.groupby("player_id")["fantasy_points"]
        .transform(lambda s: s.shift(1).expanding().mean())
    )
    rbr_sorted["career_avg_goals"] = (
        rbr_sorted.groupby("player_id")["goals_filled"]
        .transform(lambda s: s.shift(1).expanding().mean())
    )
    rbr_sorted["games_played"] = (
        rbr_sorted.groupby("player_id")["fantasy_points"]
        .transform(lambda s: s.shift(1).expanding().count())
    )

    # home/away context
    ha = pd.read_csv(_DIR / "rbr_H_A_merged.csv", low_memory=False, parse_dates=["match_date"])
    ha["is_home"] = (ha["home_away"] == "H").astype(float)
    ha_s = ha.sort_values(["player_id", "match_date"])
    ha_s["prev_date"] = ha_s.groupby("player_id")["match_date"].shift(1)
    ha_s["rest_days"] = (ha_s["match_date"] - ha_s["prev_date"]).dt.days.fillna(7)
    ha_slim = ha_s[["player_id", "match_date", "is_home", "rest_days"]].drop_duplicates(
        subset=["player_id", "match_date"]
    )
    rbr_sorted = rbr_sorted.merge(ha_slim, on=["player_id", "match_date"], how="left")
    rbr_sorted["is_home"] = rbr_sorted["is_home"].fillna(0.5)
    rbr_sorted["rest_days"] = rbr_sorted["rest_days"].fillna(7)

    # Player name lookup
    comb = pd.read_csv(_DIR / "afl_comb_CLdata.csv", low_memory=False)
    _cache["id2name"] = (
        comb[["player_id", "player_name"]].drop_duplicates()
        .set_index("player_id")["player_name"]
    )
    _cache["rbr_sorted"] = rbr_sorted


# ── Validation helpers ────────────────────────────────────────────────────────
def _validate_team(name: str):
    _load()
    if name not in _cache["valid_teams"]:
        known = sorted(_cache["valid_teams"])
        # fuzzy suggestion: first match by substring
        suggestions = [t for t in known if name.lower() in t.lower()]
        hint = f" Did you mean: {suggestions[:3]}?" if suggestions else ""
        raise ValueError(
            f"Unknown team '{name}'.{hint} "
            f"Call get_valid_teams() to see all {len(known)} known team names."
        )


def _validate_date(date_str: str, min_year: int = 1983, max_year: int = 2025):
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(date_str)):
        raise ValueError(
            f"Date '{date_str}' must be in ISO format 'YYYY-MM-DD' (e.g. '2024-07-20')."
        )
    try:
        d = pd.to_datetime(date_str)
    except Exception:
        raise ValueError(
            f"Cannot parse date '{date_str}'. Use ISO format: 'YYYY-MM-DD'."
        )
    if d.year < min_year or d.year > max_year:
        raise ValueError(
            f"Date {date_str} is outside the data range ({min_year}–{max_year}). "
            "Predictions beyond 2025 are not supported."
        )
    return d


# ── Public API ────────────────────────────────────────────────────────────────

def get_valid_teams() -> list:
    """Return the list of all known AFL team names."""
    _load()
    return sorted(_cache["valid_teams"])


def predict_match_winner(
    team_a: str,
    team_b: str,
    date: str,
    home_team: str = None,
) -> dict:
    """
    Predict the winner of an AFL match.

    Parameters
    ----------
    team_a    : First team (e.g. 'Brisbane Lions')
    team_b    : Second team (e.g. 'Collingwood Magpies')
    date      : Match date in ISO format 'YYYY-MM-DD'
    home_team : Which team is at home (defaults to team_a if None)

    Returns
    -------
    dict with keys:
        winner      : str  — predicted winning team
        probability : float — P(winner wins), 0-1
        confidence  : str  — 'high' / 'medium' / 'low'
        team_a_prob : float — P(team_a wins)
        team_b_prob : float — P(team_b wins)
        details     : dict — raw feature values used for prediction

    Raises
    ------
    ValueError if team names are unknown or date is out of range.
    """
    _validate_team(team_a)
    _validate_team(team_b)
    match_date = _validate_date(date)

    if home_team is None:
        home_team = team_a
    if home_team not in (team_a, team_b):
        raise ValueError(f"home_team '{home_team}' must be one of '{team_a}' or '{team_b}'.")

    feat = _cache["feat_table"]

    def get_team_features(team, opponent, is_home_val):
        # Latest available features for this team before the match date
        rows = feat[
            (feat["team"] == team) &
            (feat["match_date"] < match_date)
        ].sort_values("match_date")

        if len(rows) == 0:
            # No history — return neutral/median values
            row = {f: feat[f].median() if feat[f].dtype != object else 0.5
                   for f in MW_FEATURES}
            row["is_home"] = float(is_home_val)
            return row

        latest = rows.iloc[-1]

        # Head-to-head: historical record vs this specific opponent
        h2h_rows = feat[
            (feat["team"] == team) &
            (feat["opponent"] == opponent) &
            (feat["match_date"] < match_date)
        ]
        h2h_winrate = h2h_rows["win"].mean() if len(h2h_rows) > 0 else 0.5
        h2h_cumgames = float(len(h2h_rows))

        # Opponent rest advantage
        opp_rows = feat[
            (feat["team"] == opponent) &
            (feat["match_date"] < match_date)
        ].sort_values("match_date")
        team_rest = float(latest.get("rest_days", 7))
        opp_rest = float(opp_rows.iloc[-1].get("rest_days", 7)) if len(opp_rows) > 0 else 7.0

        return {
            "roll3_win":          float(latest.get("roll3_win", 0.5)),
            "roll5_win":          float(latest.get("roll5_win", 0.5)),
            "roll3_goals":        float(latest.get("roll3_goals", 50)),
            "roll5_goals":        float(latest.get("roll5_goals", 50)),
            "roll3_disposals":    float(latest.get("roll3_disposals", 370)),
            "roll5_disposals":    float(latest.get("roll5_disposals", 370)),
            "h2h_winrate":        h2h_winrate,
            "h2h_cumgames":       h2h_cumgames,
            "is_home":            float(is_home_val),
            "rest_days":          team_rest,
            "rest_advantage":     team_rest - opp_rest,
            "season_winpct":      float(latest.get("season_winpct", 0.5)),
            "win_streak":         float(latest.get("win_streak", 0)),
            "loss_streak":        float(latest.get("loss_streak", 0)),
            "venue_winrate":      float(latest.get("venue_winrate", 0.5)),
        }

    is_home_a = (home_team == team_a)
    feat_a = get_team_features(team_a, team_b, is_home_a)
    feat_b = get_team_features(team_b, team_a, not is_home_a)

    X = pd.DataFrame([feat_a, feat_b])
    probs = _cache["mw_model"].predict_proba(X)[:, 1]
    prob_a, prob_b = float(probs[0]), float(probs[1])

    # Re-normalise to sum to 1 (since both rows are independent predictions)
    total = prob_a + prob_b
    prob_a_norm = prob_a / total
    prob_b_norm = prob_b / total

    winner = team_a if prob_a_norm >= prob_b_norm else team_b
    win_prob = max(prob_a_norm, prob_b_norm)
    confidence = "high" if win_prob >= 0.65 else "medium" if win_prob >= 0.55 else "low"

    return {
        "winner":       winner,
        "probability":  round(win_prob, 3),
        "confidence":   confidence,
        "team_a":       team_a,
        "team_b":       team_b,
        "team_a_prob":  round(prob_a_norm, 3),
        "team_b_prob":  round(prob_b_norm, 3),
        "details":      feat_a,
    }


def predict_top_player(
    team: str,
    match_date: str,
    n: int = 5,
    stat_type: str = "fantasy_points",
) -> dict:
    """
    Predict the top N performers for a team in an upcoming match.

    Parameters
    ----------
    team       : Team name (e.g. 'Brisbane Lions')
    match_date : Date of the match 'YYYY-MM-DD'
    n          : Number of top players to return (default 5)
    stat_type  : 'fantasy_points' or 'goals' (affects ranking target)

    Returns
    -------
    dict with keys:
        team           : str
        match_date     : str
        stat_type      : str
        ranked_players : list of dicts [{rank, player_id, player_name,
                          predicted_fantasy_points, career_avg_fp, recent_form_3}]

    Raises
    ------
    ValueError if team name is unknown, date is out of range, or
    no historical player data is found for this team.
    """
    _validate_team(team)
    d = _validate_date(match_date)

    rbr_sorted = _cache["rbr_sorted"]
    id2name    = _cache["id2name"]

    # Get players who have played for this team before the given date
    team_players = rbr_sorted[
        (rbr_sorted["team"] == team) &
        (rbr_sorted["match_date"] < d)
    ]

    if len(team_players) == 0:
        raise ValueError(
            f"No historical player data found for team '{team}' before {match_date}. "
            "Check that the team name is correct and the date is after the team's first season."
        )

    # Take most recent appearance per player to get their current rolling stats
    latest_per_player = (
        team_players.sort_values("match_date")
        .groupby("player_id")
        .last()
        .reset_index()
    )

    # Keep only players who have appeared in the last 2 seasons (active roster proxy)
    cutoff_year = d.year - 2
    latest_per_player = latest_per_player[
        latest_per_player["match_date"].dt.year >= cutoff_year
    ]

    if len(latest_per_player) == 0:
        raise ValueError(
            f"No recently-active players found for '{team}' within 2 seasons of {match_date}."
        )

    # Impute missing PP_FEATURES with median across all players
    X_players = latest_per_player[
        [f for f in PP_FEATURES if f in latest_per_player.columns]
    ].copy()
    for col in PP_FEATURES:
        if col not in X_players.columns:
            X_players[col] = rbr_sorted[col].median() if col in rbr_sorted.columns else 0.0

    X_players = X_players[PP_FEATURES]

    # Predict fantasy points
    predicted_fp = _cache["pp_model"].predict(X_players)
    latest_per_player = latest_per_player.copy()
    latest_per_player["predicted_fp"] = predicted_fp

    # Sort by predicted fantasy points (or goals proxy if requested)
    sort_col = "predicted_fp"
    latest_per_player = latest_per_player.sort_values(sort_col, ascending=False).head(n)
    latest_per_player["player_name"] = latest_per_player["player_id"].map(id2name)

    ranked = []
    for rank, (_, row) in enumerate(latest_per_player.iterrows(), start=1):
        ranked.append({
            "rank":                      rank,
            "player_id":                 int(row["player_id"]),
            "player_name":               str(row.get("player_name", "Unknown")),
            "predicted_fantasy_points":  round(float(row["predicted_fp"]), 1),
            "career_avg_fp":             round(float(row.get("career_avg_fp", 0)), 1),
            "recent_form_3games":        round(float(row.get("roll3_fantasy_points", 0)), 1),
        })

    return {
        "team":            team,
        "match_date":      match_date,
        "stat_type":       stat_type,
        "ranked_players":  ranked,
    }


# ── Unit tests ────────────────────────────────────────────────────────────────
def _run_tests():
    import traceback
    PASS = 0; FAIL = 0

    def ok(fn, desc):
        nonlocal PASS
        try: fn(); PASS += 1; print(f"  PASS: {desc}")
        except Exception as e: nonlocal FAIL; FAIL += 1; print(f"  FAIL: {desc} -> {e}")

    def fails(fn, exc, desc):
        nonlocal PASS, FAIL
        try: fn(); FAIL += 1; print(f"  FAIL (no error raised): {desc}")
        except exc: PASS += 1; print(f"  PASS: {desc}")
        except Exception as e: FAIL += 1; print(f"  FAIL (wrong error): {desc} -> {e}")

    print("\n=== Unit Tests ===")

    # Valid prediction
    ok(lambda: predict_match_winner("Brisbane Lions", "Collingwood Magpies", "2024-06-01",
                                     home_team="Brisbane Lions"),
       "Valid match winner prediction returns dict")

    # Unknown team
    fails(lambda: predict_match_winner("Mars FC", "Collingwood Magpies", "2024-06-01"),
          ValueError, "Unknown team raises ValueError")

    # Invalid date format
    fails(lambda: predict_match_winner("Brisbane Lions", "Collingwood Magpies", "01/06/2024"),
          ValueError, "Bad date format raises ValueError")

    # Date out of range
    fails(lambda: predict_match_winner("Brisbane Lions", "Collingwood Magpies", "2030-01-01"),
          ValueError, "Future date raises ValueError")

    # home_team not in match
    fails(lambda: predict_match_winner("Brisbane Lions", "Collingwood Magpies", "2024-06-01",
                                        home_team="Sydney Swans"),
          ValueError, "home_team not in match raises ValueError")

    # Valid top player
    ok(lambda: predict_top_player("Brisbane Lions", "2024-06-01", n=5),
       "Valid top player prediction returns dict with 5 players")

    # Unknown team for top player
    fails(lambda: predict_top_player("Fake Team FC", "2024-06-01"),
          ValueError, "Unknown team in predict_top_player raises ValueError")

    # n parameter
    ok(lambda: predict_top_player("Sydney Swans", "2024-05-01", n=3),
       "n=3 returns exactly 3 players")

    # get_valid_teams
    ok(lambda: [t for t in get_valid_teams() if isinstance(t, str)],
       "get_valid_teams returns list of strings")

    print(f"\n  Results: {PASS} passed, {FAIL} failed\n")
    return FAIL == 0


if __name__ == "__main__":
    import sys, json

    if "--test" in sys.argv:
        ok = _run_tests()
        sys.exit(0 if ok else 1)

    # Demo
    print("=== predict_match_winner demo ===")
    result = predict_match_winner(
        "Brisbane Lions", "Collingwood Magpies",
        "2024-07-20", home_team="Brisbane Lions"
    )
    print(json.dumps({k: v for k, v in result.items() if k != "details"}, indent=2))

    print("\n=== predict_top_player demo ===")
    top5 = predict_top_player("Brisbane Lions", "2024-07-20", n=5)
    for p in top5["ranked_players"]:
        print(f"  #{p['rank']}  {p['player_name']:<30}  pred={p['predicted_fantasy_points']:.0f}  "
              f"career={p['career_avg_fp']:.0f}  recent3={p['recent_form_3games']:.0f}")
