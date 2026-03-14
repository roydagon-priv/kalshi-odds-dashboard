"""Cross-platform matching: Kalshi ↔ Polymarket team/market alignment."""

import json
import re

# ---------------------------------------------------------------------------
# Team name maps (Kalshi uses city names, Polymarket uses team names)
# ---------------------------------------------------------------------------

NBA_CITY_TO_TEAM = {
    "atlanta": "hawks", "boston": "celtics", "brooklyn": "nets",
    "charlotte": "hornets", "chicago": "bulls", "cleveland": "cavaliers",
    "dallas": "mavericks", "denver": "nuggets", "detroit": "pistons",
    "golden state": "warriors", "houston": "rockets", "indiana": "pacers",
    "los angeles l": "lakers", "los angeles c": "clippers",
    "la lakers": "lakers", "la clippers": "clippers",
    "memphis": "grizzlies", "miami": "heat", "milwaukee": "bucks",
    "minnesota": "timberwolves", "new orleans": "pelicans",
    "new york": "knicks", "oklahoma city": "thunder", "orlando": "magic",
    "philadelphia": "76ers", "phoenix": "suns", "portland": "trail blazers",
    "sacramento": "kings", "san antonio": "spurs", "toronto": "raptors",
    "utah": "jazz", "washington": "wizards",
}
NHL_CITY_TO_TEAM = {
    "anaheim": "ducks", "arizona": "coyotes", "boston": "bruins",
    "buffalo": "sabres", "calgary": "flames", "carolina": "hurricanes",
    "chicago": "blackhawks", "colorado": "avalanche", "columbus": "blue jackets",
    "dallas": "stars", "detroit": "red wings", "edmonton": "oilers",
    "florida": "panthers", "los angeles": "kings", "minnesota": "wild",
    "montreal": "canadiens", "nashville": "predators", "new jersey": "devils",
    "new york r": "rangers", "new york i": "islanders", "ny rangers": "rangers",
    "ny islanders": "islanders", "ottawa": "senators", "philadelphia": "flyers",
    "pittsburgh": "penguins", "san jose": "sharks", "seattle": "kraken",
    "st. louis": "blues", "st louis": "blues",
    "tampa bay": "lightning", "toronto": "maple leafs",
    "utah": "mammoth", "vancouver": "canucks", "vegas": "golden knights",
    "washington": "capitals", "winnipeg": "jets",
}
MLB_CITY_TO_TEAM = {
    # Single-city teams — keys are exactly what appears in Kalshi yes_sub_title (lowercased)
    "arizona": "diamondbacks",
    "atlanta": "braves",
    "baltimore": "orioles",
    "boston": "red sox",
    "cincinnati": "reds",
    "cleveland": "guardians",
    "colorado": "rockies",
    "detroit": "tigers",
    "houston": "astros",
    "kansas city": "royals",
    "miami": "marlins",
    "milwaukee": "brewers",
    "minnesota": "twins",
    "philadelphia": "phillies",
    "pittsburgh": "pirates",
    "san diego": "padres",
    "san francisco": "giants",
    "seattle": "mariners",
    "st. louis": "cardinals",
    "st louis": "cardinals",
    "tampa bay": "rays",
    "texas": "rangers",
    "toronto": "blue jays",
    "washington": "nationals",
    # Multi-team cities — trailing initial/abbrev matches Kalshi's yes_sub_title format
    "chicago c": "cubs",
    "chicago ws": "white sox",
    "los angeles d": "dodgers",
    "los angeles a": "angels",
    "new york y": "yankees",
    "new york m": "mets",
    # Athletics use team nickname only (no city prefix in Kalshi)
    "a's": "athletics",
}

# Reverse: team name → canonical name (lowercase)
NBA_TEAM_NAMES = set(NBA_CITY_TO_TEAM.values())
NHL_TEAM_NAMES = set(NHL_CITY_TO_TEAM.values())
MLB_TEAM_NAMES = set(MLB_CITY_TO_TEAM.values())

# Capitalized team names for display
NBA_CITY_TO_TEAM_DISPLAY = {k: v.title() for k, v in NBA_CITY_TO_TEAM.items()}
NHL_CITY_TO_TEAM_DISPLAY = {k: v.title() for k, v in NHL_CITY_TO_TEAM.items()}
# Fix multi-word edge cases
NHL_CITY_TO_TEAM_DISPLAY["st. louis"] = "Blues"
NHL_CITY_TO_TEAM_DISPLAY["st louis"] = "Blues"
NHL_CITY_TO_TEAM_DISPLAY["new york r"] = "Rangers"
NHL_CITY_TO_TEAM_DISPLAY["new york i"] = "Islanders"
NHL_CITY_TO_TEAM_DISPLAY["ny rangers"] = "Rangers"
NHL_CITY_TO_TEAM_DISPLAY["ny islanders"] = "Islanders"
NBA_CITY_TO_TEAM_DISPLAY["los angeles l"] = "Lakers"
NBA_CITY_TO_TEAM_DISPLAY["los angeles c"] = "Clippers"
NBA_CITY_TO_TEAM_DISPLAY["la lakers"] = "Lakers"
NBA_CITY_TO_TEAM_DISPLAY["la clippers"] = "Clippers"
NBA_CITY_TO_TEAM_DISPLAY["golden state"] = "Warriors"
NBA_CITY_TO_TEAM_DISPLAY["new orleans"] = "Pelicans"
NBA_CITY_TO_TEAM_DISPLAY["new york"] = "Knicks"
NBA_CITY_TO_TEAM_DISPLAY["oklahoma city"] = "Thunder"
NBA_CITY_TO_TEAM_DISPLAY["san antonio"] = "Spurs"
NBA_CITY_TO_TEAM_DISPLAY["trail blazers"] = "Trail Blazers"
NBA_CITY_TO_TEAM_DISPLAY["portland"] = "Trail Blazers"
MLB_CITY_TO_TEAM_DISPLAY = {k: v.title() for k, v in MLB_CITY_TO_TEAM.items()}
# Fix multi-word edge cases
MLB_CITY_TO_TEAM_DISPLAY["boston"] = "Red Sox"
MLB_CITY_TO_TEAM_DISPLAY["chicago c"] = "Cubs"
MLB_CITY_TO_TEAM_DISPLAY["chicago ws"] = "White Sox"
MLB_CITY_TO_TEAM_DISPLAY["st. louis"] = "Cardinals"
MLB_CITY_TO_TEAM_DISPLAY["st louis"] = "Cardinals"
MLB_CITY_TO_TEAM_DISPLAY["tampa bay"] = "Rays"
MLB_CITY_TO_TEAM_DISPLAY["toronto"] = "Blue Jays"
MLB_CITY_TO_TEAM_DISPLAY["los angeles d"] = "Dodgers"
MLB_CITY_TO_TEAM_DISPLAY["los angeles a"] = "Angels"
MLB_CITY_TO_TEAM_DISPLAY["new york y"] = "Yankees"
MLB_CITY_TO_TEAM_DISPLAY["new york m"] = "Mets"
MLB_CITY_TO_TEAM_DISPLAY["san francisco"] = "Giants"
MLB_CITY_TO_TEAM_DISPLAY["san diego"] = "Padres"
MLB_CITY_TO_TEAM_DISPLAY["kansas city"] = "Royals"
MLB_CITY_TO_TEAM_DISPLAY["arizona"] = "Diamondbacks"
MLB_CITY_TO_TEAM_DISPLAY["a's"] = "Athletics"


# ---------------------------------------------------------------------------
# Shared utility
# ---------------------------------------------------------------------------

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Title helpers
# ---------------------------------------------------------------------------

def substitute_teams_in_title(title, sport_prefix):
    """Replace city names with team names in a Kalshi market title."""
    if sport_prefix == "NBA":
        mapping = NBA_CITY_TO_TEAM_DISPLAY
    elif sport_prefix == "NHL":
        mapping = NHL_CITY_TO_TEAM_DISPLAY
    elif sport_prefix == "MLB":
        mapping = MLB_CITY_TO_TEAM_DISPLAY
    else:
        return title
    for city in sorted(mapping, key=len, reverse=True):
        pattern = re.compile(re.escape(city), re.IGNORECASE)
        if pattern.search(title):
            title = pattern.sub(mapping[city], title)
    return title


def _extract_poly_team_names(title):
    """Parse 'Team A vs. Team B' → (team_a_lower, team_b_lower)."""
    parts = re.split(r"\s+vs\.?\s+", title, maxsplit=1)
    if len(parts) == 2:
        return parts[0].strip().lower(), parts[1].strip().lower()
    return None, None


def _kalshi_title_to_teams(title, sport_prefix, mapping=None):
    """Parse Kalshi 'CityA vs CityB ...' → set of team names (lowercase)."""
    match = re.match(r"^(.+?)\s+(?:at|vs\.?)\s+(.+?)(?:\s*[:?]|\s+Winner|\s+Total|\s+Spread)", title, re.I)
    if not match:
        return set()
    city1 = match.group(1).strip().lower()
    city2 = match.group(2).strip().lower()
    if mapping is None:
        if sport_prefix == "NBA":
            mapping = NBA_CITY_TO_TEAM
        elif sport_prefix == "NHL":
            mapping = NHL_CITY_TO_TEAM
        elif sport_prefix == "MLB":
            mapping = MLB_CITY_TO_TEAM
        else:
            return set()
    teams = set()
    for city in [city1, city2]:
        if city in mapping:
            teams.add(mapping[city])
    return teams


def _extract_ou_threshold(question):
    """Extract O/U threshold from Polymarket question like 'Teams: O/U 6.5' → 6.5."""
    m = re.search(r"O/U\s+([\d.]+)", question)
    return float(m.group(1)) if m else None


def _extract_spread_line(question):
    """Extract spread line magnitude from 'Spread: Team (-1.5)' → 1.5."""
    m = re.search(r"\(-?([\d.]+)\)", question)
    return float(m.group(1)) if m else None


def _extract_spread_team(question):
    """Extract favored team from 'Spread: Kings (-1.5)' → 'kings'."""
    m = re.match(r"Spread:\s+(.+?)\s+\(", question)
    return m.group(1).strip().lower() if m else None


# ---------------------------------------------------------------------------
# Index building & matching
# ---------------------------------------------------------------------------

def build_polymarket_index(poly_events):
    """Build two lookups:
      index: frozenset({team1, team2}) → list of poly dicts  (moneyline/totals)
      spread_index: (favored_team_lower, line) → poly dict    (spreads, one entry per line)
    Returns (index, spread_index).
    """
    index = {}
    spread_index = {}
    for event in poly_events:
        for mkt in event.get("markets", []):
            smt = mkt.get("sportsMarketType", "")
            if smt not in ("moneyline", "totals", "spreads"):
                continue
            question = mkt.get("question", "")

            prices = json.loads(mkt.get("outcomePrices", "[]"))
            outcomes = json.loads(mkt.get("outcomes", "[]"))
            p1 = safe_float(prices[0]) if len(prices) > 0 else 0.0
            p2 = safe_float(prices[1]) if len(prices) > 1 else 0.0
            o1 = outcomes[0] if len(outcomes) > 0 else ""
            o2 = outcomes[1] if len(outcomes) > 1 else ""
            best_bid = safe_float(mkt.get("bestBid"))
            best_ask = safe_float(mkt.get("bestAsk"))
            o1_ask = best_ask if best_ask else p1
            o2_ask = (1 - best_bid) if best_bid else p2
            entry = {
                "question": question,
                "outcome1": o1, "outcome1_ask": o1_ask,
                "outcome2": o2, "outcome2_ask": o2_ask,
                "volume": safe_float(mkt.get("volume")),
                "market_type": smt,
                "threshold": _extract_ou_threshold(question),
            }

            if smt == "spreads":
                st = _extract_spread_team(question)
                line = _extract_spread_line(question)
                if st and line is not None:
                    entry["event_title"] = event.get("title", "")
                    spread_index[(st, line)] = entry
            else:
                clean_q = re.sub(r":\s*O/U\s+[\d.]+\s*$", "", question).strip()
                t1, t2 = _extract_poly_team_names(clean_q)
                if not t1 or not t2:
                    continue
                key = frozenset([t1, t2])
                index.setdefault(key, []).append(entry)
    return index, spread_index


def _match_nba_nhl(kalshi_data, poly_index, spread_index, floor_strike, sport_prefix):
    """Match NBA, NHL, or MLB Kalshi market to Polymarket."""
    sport_cat = kalshi_data["sport"]
    target_type = "moneyline"
    if "Total" in sport_cat:
        target_type = "totals"
    elif "Spread" in sport_cat:
        target_type = "spreads"

    # Select mapping and team_names by sport — explicit chain avoids silent fallthrough
    if sport_prefix == "NBA":
        mapping = NBA_CITY_TO_TEAM
        team_names = NBA_TEAM_NAMES
    elif sport_prefix == "NHL":
        mapping = NHL_CITY_TO_TEAM
        team_names = NHL_TEAM_NAMES
    elif sport_prefix == "MLB":
        mapping = MLB_CITY_TO_TEAM
        team_names = MLB_TEAM_NAMES
    else:
        return None

    if target_type == "spreads" and spread_index is not None:
        title_lower = kalshi_data["title"].lower()

        kalshi_team = None
        for team in sorted(team_names, key=len, reverse=True):
            if team in title_lower:
                kalshi_team = team
                break
        if not kalshi_team:
            for city, team in sorted(mapping.items(), key=lambda x: len(x[0]), reverse=True):
                if city in title_lower:
                    kalshi_team = team
                    break

        if floor_strike is not None:
            line = abs(floor_strike)
        else:
            m_line = re.search(r"over\s+([\d.]+)", kalshi_data["title"], re.I)
            line = float(m_line.group(1)) if m_line else None

        if not kalshi_team or line is None:
            return None

        best = spread_index.get((kalshi_team, line))
        if not best:
            return None
        event_title = best.get("event_title", "")
        t1, t2 = _extract_poly_team_names(event_title)
        opponent = None
        if t1 and t2:
            opponent = t2 if t1 == kalshi_team else t1 if t2 == kalshi_team else None
        return {
            "poly_yes": best["outcome1_ask"],
            "poly_no": best["outcome2_ask"],
            "poly_volume": best["volume"],
            "poly_question": best["question"],
            "spread_opponent": opponent,
        }

    kalshi_teams = _kalshi_title_to_teams(kalshi_data["title"], sport_prefix)
    if len(kalshi_teams) < 2:
        return None

    key = frozenset(kalshi_teams)
    poly_markets = poly_index.get(key)
    if not poly_markets:
        return None

    best = None
    if target_type == "totals" and floor_strike is not None:
        for pm in poly_markets:
            if pm["market_type"] == "totals" and pm["threshold"] == floor_strike:
                best = pm
                break
    else:
        for pm in poly_markets:
            if pm["market_type"] == target_type:
                best = pm
                break

    if not best:
        if target_type == "moneyline":
            for pm in poly_markets:
                if pm["market_type"] == "moneyline":
                    best = pm
                    break
    if not best:
        return None

    if target_type == "totals":
        o1_lower = best["outcome1"].lower()
        if "over" in o1_lower:
            return {
                "poly_yes": best["outcome1_ask"],
                "poly_no": best["outcome2_ask"],
                "poly_volume": best["volume"],
                "poly_question": best["question"],
            }
        else:
            return {
                "poly_yes": best["outcome2_ask"],
                "poly_no": best["outcome1_ask"],
                "poly_volume": best["volume"],
                "poly_question": best["question"],
            }

    detail = kalshi_data.get("detail", "").lower()
    # mapping and team_names already set at function top

    kalshi_yes_team = None
    for city, team in mapping.items():
        if city in detail or team in detail:
            kalshi_yes_team = team
            break
    if not kalshi_yes_team:
        for team in team_names:
            if team in detail:
                kalshi_yes_team = team
                break

    if not kalshi_yes_team:
        return {
            "poly_yes": best["outcome1_ask"],
            "poly_no": best["outcome2_ask"],
            "poly_volume": best["volume"],
            "poly_question": best["question"],
        }

    o1_lower = best["outcome1"].lower()
    o2_lower = best["outcome2"].lower()
    if kalshi_yes_team in o1_lower:
        return {
            "poly_yes": best["outcome1_ask"],
            "poly_no": best["outcome2_ask"],
            "poly_volume": best["volume"],
            "poly_question": best["question"],
        }
    elif kalshi_yes_team in o2_lower:
        return {
            "poly_yes": best["outcome2_ask"],
            "poly_no": best["outcome1_ask"],
            "poly_volume": best["volume"],
            "poly_question": best["question"],
        }
    else:
        return {
            "poly_yes": best["outcome1_ask"],
            "poly_no": best["outcome2_ask"],
            "poly_volume": best["volume"],
            "poly_question": best["question"],
        }


def _match_mlb(kalshi_data, poly_index, spread_index, floor_strike):
    """Match MLB Kalshi market to Polymarket. Same structure as NBA/NHL."""
    return _match_nba_nhl(kalshi_data, poly_index, spread_index, floor_strike, "MLB")


def match_polymarket(kalshi_data, poly_index, spread_index=None, floor_strike=None):
    """Dispatch to per-sport matching handler."""
    sport_prefix = kalshi_data["sport"].split(" - ")[0]
    if sport_prefix in ("NBA", "NHL"):
        return _match_nba_nhl(kalshi_data, poly_index, spread_index, floor_strike, sport_prefix)
    if sport_prefix == "MLB":
        return _match_mlb(kalshi_data, poly_index, spread_index, floor_strike)
    if sport_prefix == "UCL":
        return _match_ucl(kalshi_data, poly_index, spread_index, floor_strike)
    return None
