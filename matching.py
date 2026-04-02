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


def _filter_by_date(entries, game_date):
    """Filter index entries to those matching the given game date (YYYY-MM-DD).
    Returns filtered list if any match, otherwise returns the original list as fallback."""
    if not game_date or not entries:
        return entries
    matched = [e for e in entries if e.get("game_date") == game_date]
    return matched if matched else entries


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
        t1 = parts[0].strip().lower()
        t2 = re.split(r"\s*[:\?]", parts[1], maxsplit=1)[0].strip().lower()
        return t1, t2
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


def _extract_f1_driver(question):
    """Extract (driver_lower, f1_type) from F1 Polymarket questions like 'Will Verstappen win the GP?'"""
    q_lower = question.lower()
    if "fastest lap" in q_lower:
        f1_type = "fastestlap"
    elif "pole" in q_lower:
        f1_type = "pole"
    elif "podium" in q_lower or "top 3" in q_lower or "top three" in q_lower:
        f1_type = "podium"
    elif "top 5" in q_lower or "top five" in q_lower:
        f1_type = "top5"
    elif "top 10" in q_lower or "top ten" in q_lower:
        f1_type = "top10"
    elif "win" in q_lower:
        f1_type = "win"
    else:
        return None, None
    m = re.match(r"will\s+(.+?)\s+(?:win|get|finish|set)", question, re.I)
    if m:
        return m.group(1).strip().lower(), f1_type
    return None, None


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
    """Build three lookups:
      index: frozenset({team1, team2}) → list of poly dicts  (moneyline/totals)
      spread_index: (favored_team_lower, line) → list of poly dicts  (spreads)
      f1_index: (driver_lower, f1_type) → list of poly dicts  (F1 markets)
    Returns (index, spread_index, f1_index).
    """
    index = {}
    spread_index = {}
    f1_index = {}
    _GAME_TYPES = {"moneyline", "totals", "spreads"}
    for event in poly_events:
        for mkt in event.get("markets", []):
            smt = mkt.get("sportsMarketType") or ""
            question = mkt.get("question", "")

            # Only index markets with a recognized game-level sportsMarketType.
            # Player props (assists, rebounds, points), first-half variants,
            # and other non-game types are skipped to avoid index pollution.
            if smt not in _GAME_TYPES:
                # For untyped markets, try F1 indexing — but only if the event
                # is not a team matchup (avoid F1-indexing season futures).
                if not smt and "vs" not in event.get("title", "").lower():
                    # Only try F1 indexing for events that look like F1 races
                    evt_lower = event.get("title", "").lower()
                    is_f1_event = any(kw in evt_lower for kw in ("grand prix", " gp", "f1", "formula"))
                    f1_driver, f1_type = _extract_f1_driver(question) if is_f1_event else (None, None)
                    if f1_driver and f1_type:
                        prices = json.loads(mkt.get("outcomePrices", "[]"))
                        p1 = safe_float(prices[0]) if len(prices) > 0 else 0.0
                        p2 = safe_float(prices[1]) if len(prices) > 1 else 0.0
                        best_bid = safe_float(mkt.get("bestBid"))
                        best_ask = safe_float(mkt.get("bestAsk"))
                        entry = {
                            "question": question,
                            "outcome1": "",
                            "outcome1_ask": best_ask if best_ask else p1,
                            "outcome2": "",
                            "outcome2_ask": (1 - best_bid) if best_bid else p2,
                            "volume": safe_float(mkt.get("volume")),
                        }
                        f1_index.setdefault((f1_driver, f1_type), []).append(entry)
                continue

            # Extract game date from gameStartTime (e.g. "2026-04-03 01:40:00+00" → "2026-04-03")
            gst = mkt.get("gameStartTime") or ""
            game_date = gst[:10] if len(gst) >= 10 else ""

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
                "game_date": game_date,
            }

            if smt == "spreads":
                st = _extract_spread_team(question)
                line = _extract_spread_line(question)
                if st and line is not None:
                    entry["event_title"] = event.get("title", "")
                    spread_index.setdefault((st, line), []).append(entry)
            else:
                clean_q = re.sub(r":\s*O/U\s+[\d.]+\s*$", "", question).strip()
                t1, t2 = _extract_poly_team_names(clean_q)
                if not t1 or not t2:
                    # Fallback: try parsing from event title (e.g. soccer moneylines
                    # use "Will Team win on DATE?" with no "vs." in the question)
                    event_title = re.sub(r"\s*-\s*More Markets\s*$", "", event.get("title", ""), flags=re.I).strip()
                    t1, t2 = _extract_poly_team_names(event_title)
                if not t1 or not t2:
                    continue
                key = frozenset([t1, t2])
                index.setdefault(key, []).append(entry)

    return index, spread_index, f1_index


def _match_team_sport(kalshi_data, poly_index, spread_index, floor_strike, sport_prefix, game_date=None):
    """Match NBA, NHL, or MLB Kalshi market to Polymarket."""
    sport_cat = kalshi_data["sport"]
    target_type = "moneyline"
    if "Total" in sport_cat:
        target_type = "totals"
    elif "Spread" in sport_cat or "Run Line" in sport_cat:
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

        entries = spread_index.get((kalshi_team, line))
        if not entries:
            # Partial match: Polymarket may use full "city team" name vs just "team"
            for (key_team, key_line), ents in spread_index.items():
                if key_line == line and (kalshi_team in key_team or key_team in kalshi_team):
                    entries = ents
                    break
        entries = _filter_by_date(entries, game_date) if entries else entries
        best = entries[0] if entries else None
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
        # Fuzzy fallback: Polymarket may use "city team" (e.g. "atlanta braves")
        # while Kalshi maps to just the team name ("braves"). Check if each Kalshi
        # team name appears as a substring of a Poly index key member.
        kalshi_list = sorted(kalshi_teams)
        for pkey, pmarkets in poly_index.items():
            plist = sorted(pkey)
            if len(plist) != len(kalshi_list):
                continue
            if all(any(kt in pt for pt in plist) for kt in kalshi_list):
                poly_markets = pmarkets
                break
    if not poly_markets:
        return None

    # Filter to same-date markets (critical for MLB series where teams play multiple games)
    poly_markets = _filter_by_date(poly_markets, game_date)

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


def _match_f1(kalshi_data, f1_index):
    """Match F1 Kalshi market to Polymarket by driver name and market type."""
    if not f1_index:
        return None
    sport_cat = kalshi_data["sport"]
    driver = kalshi_data.get("detail", "").strip().lower()
    if not driver:
        return None

    if "Race Winner" in sport_cat:
        f1_type = "win"
    elif "Pole" in sport_cat:
        f1_type = "pole"
    elif "Fastest Lap" in sport_cat:
        f1_type = "fastestlap"
    elif "Podium" in sport_cat:
        f1_type = "podium"
    elif "Top 5" in sport_cat:
        f1_type = "top5"
    elif "Top 10" in sport_cat:
        f1_type = "top10"
    else:
        return None

    entries = f1_index.get((driver, f1_type))
    if not entries:
        # Partial driver name match (e.g. "max verstappen" vs "verstappen")
        driver_parts = [p for p in driver.split() if len(p) > 3]
        for (key_driver, key_type), ents in f1_index.items():
            if key_type == f1_type and any(p in key_driver for p in driver_parts):
                entries = ents
                break
    if not entries:
        return None

    best = entries[0]
    return {
        "poly_yes": best["outcome1_ask"],
        "poly_no": best["outcome2_ask"],
        "poly_volume": best["volume"],
        "poly_question": best["question"],
    }


def _match_mlb(kalshi_data, poly_index, spread_index, floor_strike, game_date=None):
    """Match MLB Kalshi market to Polymarket. Same structure as NBA/NHL."""
    return _match_team_sport(kalshi_data, poly_index, spread_index, floor_strike, "MLB", game_date=game_date)


def _match_ucl(kalshi_data, poly_index, spread_index, floor_strike, opponent_hint=None, game_date=None):
    """Match UCL Kalshi market to Polymarket.

    Polymarket soccer match structure (observed):
    - Moneyline: sportsMarketType='moneyline', outcomes=["Yes","No"],
        question="Will Team A win on DATE?" (one per team) or
        question="Will Team A vs. Team B end in a draw?"
    - Totals: sportsMarketType='totals', outcomes=["Over","Under"],
        question="Team A vs. Team B: O/U N.5"
    - Spreads: sportsMarketType='spreads', outcomes=[team1, team2],
        question="Spread: Team A (-N.5)"

    Kalshi UCL titles: "Bayern Munich vs Atalanta Winner?"
    Draw markets: detail (yes_sub_title) == "Tie"
    """
    sport_cat = kalshi_data["sport"]
    title = kalshi_data["title"]
    detail_lower = kalshi_data.get("detail", "").lower()

    # Determine market type from Kalshi sport category
    if "Total" in sport_cat:
        target_type = "totals"
    elif "Spread" in sport_cat:
        target_type = "spreads"
    else:
        target_type = "moneyline"

    if target_type == "spreads":
        # UCL spread titles: "Barcelona wins by over 1.5 goals?" — single team only.
        # Polymarket spread_index uses full club names (e.g. "galatasaray sk"), so
        # partial-match the key team. Use opponent_hint to pick the right game when
        # a team has entries for multiple concurrent events.
        fav_match = re.match(r'^(.+?)\s+wins\s+by\s+over\s+([\d.]+)', title, re.I)
        if not fav_match:
            return None
        fav_team = fav_match.group(1).strip().lower()
        line = abs(float(fav_match.group(2)))
        opp_hint = opponent_hint.lower() if opponent_hint else None
        # Split hint into tokens for fuzzy matching (handles unicode variants like Bodø vs Bodoe)
        opp_tokens = [p for p in re.split(r'[\s/\-]+', opp_hint) if len(p) >= 3] if opp_hint else []

        best = None
        for (key_team, key_line), entries in spread_index.items():
            if key_line != line or not (fav_team in key_team or key_team in fav_team):
                continue
            for entry in entries:
                event_lower = entry.get("event_title", "").lower()
                # If we have an opponent hint, require at least one token to appear in the event title
                if opp_tokens and not any(tok in event_lower for tok in opp_tokens):
                    continue
                best = entry
                break
            if best:
                break

        if not best:
            return None
        event_title = re.sub(r"\s*-\s*More Markets\s*$", "", best.get("event_title", ""), flags=re.I)
        t1, t2 = _extract_poly_team_names(event_title)
        opponent = None
        if t1 and t2:
            opponent = t2 if (fav_team in t1 or t1 in fav_team) else t1
        return {
            "poly_yes": best["outcome1_ask"],
            "poly_no": best["outcome2_ask"],
            "poly_volume": best["volume"],
            "poly_question": best["question"],
            "spread_opponent": opponent.title() if opponent else None,
        }

    # Extract club names from Kalshi title: "Bayern Munich vs Atalanta Winner?"
    match = re.match(
        r"^(.+?)\s+(?:at|vs\.?)\s+(.+?)(?:\s*[:?]|\s+Winner|\s+Total|\s+Spread|\s+Goals)",
        title, re.I,
    )
    if not match:
        return None
    club1 = match.group(1).strip().lower()
    club2 = match.group(2).strip().lower()

    is_draw = detail_lower == "tie"

    # Build index key from club names
    key = frozenset([club1, club2])
    poly_markets = poly_index.get(key)

    # If exact frozenset not found, try searching for markets whose question
    # contains both club names (partial match for name variants)
    if not poly_markets:
        candidate_markets = []
        for k, v in poly_index.items():
            key_list = list(k)
            if len(key_list) < 2:
                continue
            if any((club1 in t or t in club1) for t in key_list) and \
               any((club2 in t or t in club2) for t in key_list):
                candidate_markets.extend(v)
        poly_markets = candidate_markets if candidate_markets else None

    if not poly_markets:
        return None

    if target_type == "totals" and floor_strike is not None:
        for pm in poly_markets:
            if pm["market_type"] == "totals" and pm["threshold"] == floor_strike:
                # outcomes=["Over","Under"]
                o1_lower = pm["outcome1"].lower()
                if "over" in o1_lower:
                    return {
                        "poly_yes": pm["outcome1_ask"],
                        "poly_no": pm["outcome2_ask"],
                        "poly_volume": pm["volume"],
                        "poly_question": pm["question"],
                    }
                else:
                    return {
                        "poly_yes": pm["outcome2_ask"],
                        "poly_no": pm["outcome1_ask"],
                        "poly_volume": pm["volume"],
                        "poly_question": pm["question"],
                    }
        return None

    # Moneyline: outcomes=["Yes","No"], club name is in the question text
    if is_draw:
        # Find the draw-specific Polymarket question
        for pm in poly_markets:
            if pm["market_type"] != "moneyline":
                continue
            q_lower = pm["question"].lower()
            if "draw" in q_lower or "tie" in q_lower:
                return {
                    "poly_yes": pm["outcome1_ask"],
                    "poly_no": pm["outcome2_ask"],
                    "poly_volume": pm["volume"],
                    "poly_question": pm["question"],
                }
        return None

    # Regular moneyline: find question "Will <yes_club> win ..."
    # detail (yes_sub_title) contains the club name for the "yes" side
    yes_club = detail_lower  # e.g. "Bayern Munich"

    for pm in poly_markets:
        if pm["market_type"] != "moneyline":
            continue
        q_lower = pm["question"].lower()
        # Skip draw markets
        if "draw" in q_lower or "tie" in q_lower:
            continue
        # Match by club name in question
        if yes_club and yes_club in q_lower:
            return {
                "poly_yes": pm["outcome1_ask"],  # outcome1=Yes
                "poly_no": pm["outcome2_ask"],   # outcome2=No
                "poly_volume": pm["volume"],
                "poly_question": pm["question"],
            }

    # Fallback: return first non-draw moneyline if no club name match
    for pm in poly_markets:
        if pm["market_type"] != "moneyline":
            continue
        q_lower = pm["question"].lower()
        if "draw" in q_lower or "tie" in q_lower:
            continue
        return {
            "poly_yes": pm["outcome1_ask"],
            "poly_no": pm["outcome2_ask"],
            "poly_volume": pm["volume"],
            "poly_question": pm["question"],
        }
    return None


def match_polymarket(kalshi_data, poly_index, spread_index=None, floor_strike=None, ucl_opponents=None, f1_index=None, game_date=None):
    """Dispatch to per-sport matching handler."""
    sport_prefix = kalshi_data["sport"].split(" - ")[0]
    if sport_prefix in ("NBA", "NHL"):
        return _match_team_sport(kalshi_data, poly_index, spread_index, floor_strike, sport_prefix, game_date=game_date)
    if sport_prefix == "MLB":
        return _match_mlb(kalshi_data, poly_index, spread_index, floor_strike, game_date=game_date)
    if sport_prefix == "UCL":
        opponent_hint = None
        if ucl_opponents and kalshi_data["sport"] == "UCL - Spread":
            fav_m = re.match(r'^(.+?)\s+wins\s+by\s+over', kalshi_data["title"], re.I)
            if fav_m:
                opponent_hint = ucl_opponents.get(fav_m.group(1).strip().lower())
        return _match_ucl(kalshi_data, poly_index, spread_index, floor_strike, opponent_hint=opponent_hint, game_date=game_date)
    if sport_prefix == "F1":
        return _match_f1(kalshi_data, f1_index)
    return None
