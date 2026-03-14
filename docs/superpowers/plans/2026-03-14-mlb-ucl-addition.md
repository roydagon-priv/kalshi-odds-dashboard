# MLB + UCL Addition Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add MLB and UCL (UEFA Champions League) markets to the Kalshi/Polymarket dashboard with full Polymarket cross-matching and arbitrage detection.

**Architecture:** Add 6 new series tickers to `kalshi_fetcher.py`. Refactor `matching.py` to dispatch to per-sport handler functions (`_match_nba_nhl`, `_match_mlb`, `_match_ucl`). Update `dashboard_generator.py` to handle the new `"draw"` market type for UCL.

**Tech Stack:** Python 3.10+, `uv run`, `requests`, `cryptography`, `python-dotenv`. No test framework — verification is done by running the dashboard script directly or small diagnostic scripts via `uv run --with requests --with python-dotenv --with cryptography`.

---

## Chunk 1: kalshi_fetcher.py + matching.py

### Task 1: Verify MLB Kalshi title format

Before writing any team maps, confirm the exact format of MLB market titles from the live API. Different formats require different map keys.

**Files:**
- Create (temp, delete after): `scripts/inspect_mlb_titles.py`

- [ ] **Step 1: Write a diagnostic script**

Create `scripts/inspect_mlb_titles.py`:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["python-dotenv", "requests", "cryptography"]
# ///
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
load_dotenv()
from kalshi_fetcher import build_kalshi_client, fetch_series_markets

api_key = os.getenv("KALSHI_API_KEY_ID")
key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "").strip("'\"")
with open(key_path) as f:
    pem = f.read()
client = build_kalshi_client(api_key, pem)

print("=== KXMLBGAME sample titles ===")
markets = fetch_series_markets(client, "MLB - Game Winner", "KXMLBGAME")
for m in markets[:15]:
    print(f"  title: {m.get('title')!r}")
    print(f"  yes_sub_title: {m.get('yes_sub_title')!r}")
    print()

print("=== KXUCLGAME sample titles ===")
markets = fetch_series_markets(client, "UCL - Match Winner", "KXUCLGAME")
for m in markets[:15]:
    print(f"  title: {m.get('title')!r}")
    print(f"  yes_sub_title: {m.get('yes_sub_title')!r}")
    print()
```

- [ ] **Step 2: Run the script**

```bash
cd /Users/roydagon/personal/kalshi-odds-dashboard
uv run scripts/inspect_mlb_titles.py
```

Expected: 15 MLB titles and 15 UCL titles printed. Note the exact format of city names in MLB titles (e.g. `"Athletics at Yankees"` vs `"Oakland at New York"` vs `"OAK at NYY"`). Note UCL title format (e.g. `"Bayern Munich at Real Madrid Winner?"` vs `"Bayern Munich vs Real Madrid Winner?"`).

- [ ] **Step 3: Record the format findings**

Based on output, confirm or update the city-key format for `MLB_CITY_TO_TEAM` in Task 2. If Kalshi uses full team names rather than city keys (e.g. `"Yankees"` instead of `"New York"`), the map will map team names directly. If city-based with disambiguation suffixes, use the `"new york y"` → `"yankees"` pattern.

Also note whether UCL uses `"at"` or `"vs"` separator — needed for `_kalshi_title_to_ucl_clubs` in Task 5.

- [ ] **Step 4: Delete the diagnostic script**

```bash
rm scripts/inspect_mlb_titles.py
rmdir scripts 2>/dev/null || true
```

---

### Task 2: Add series tickers to kalshi_fetcher.py

**Files:**
- Modify: `kalshi_fetcher.py` (lines 15–28, `TARGET_SERIES` dict)

- [ ] **Step 1: Add 6 new entries to `TARGET_SERIES`**

Open `kalshi_fetcher.py`. The `TARGET_SERIES` dict closing brace `}` is at line 28. Insert the new entries **before** the closing `}`, after the last F1 entry (line 27):

```python
    "MLB - Game Winner":     "KXMLBGAME",
    "MLB - Total Runs":      "KXMLBTOTAL",
    "MLB - Run Line":        "KXMLBSPREAD",
    "UCL - Match Winner":    "KXUCLGAME",
    "UCL - Total Goals":     "KXUCLTOTAL",
    "UCL - Spread":          "KXUCLSPREAD",
```

- [ ] **Step 2: Verify the dict is syntactically correct**

```bash
cd /Users/roydagon/personal/kalshi-odds-dashboard
python -c "from kalshi_fetcher import TARGET_SERIES; print(list(TARGET_SERIES.keys()))"
```

Expected: list of 18 keys printed with no errors.

- [ ] **Step 3: Commit**

```bash
git add kalshi_fetcher.py
git commit -m "feat: add MLB and UCL series tickers to TARGET_SERIES"
```

---

### Task 3: Add MLB team maps to matching.py

**Files:**
- Modify: `matching.py` (after `NHL_CITY_TO_TEAM` block, ~line 38)

**Note:** Adjust the exact keys below based on the format confirmed in Task 1. The map shown assumes Kalshi uses city-based keys with disambiguation suffixes (same pattern as NBA/NHL). If Kalshi uses full team names, adjust accordingly.

- [ ] **Step 1: Add `MLB_CITY_TO_TEAM` after `NHL_CITY_TO_TEAM`**

Insert after the closing `}` of `NHL_CITY_TO_TEAM` (around line 38):

```python
MLB_CITY_TO_TEAM = {
    # Single-city teams
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
    "oakland": "athletics",
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
    # Multi-team cities — disambiguation suffixes
    "chicago c": "cubs",
    "chicago w": "white sox",
    "los angeles d": "dodgers",
    "los angeles a": "angels",
    "new york y": "yankees",
    "new york m": "mets",
    # Fallback aliases
    "la dodgers": "dodgers",
    "la angels": "angels",
    "ny yankees": "yankees",
    "ny mets": "mets",
}
```

- [ ] **Step 2: Add `MLB_TEAM_NAMES` set and display map after the map**

```python
MLB_TEAM_NAMES = set(MLB_CITY_TO_TEAM.values())

MLB_CITY_TO_TEAM_DISPLAY = {k: v.title() for k, v in MLB_CITY_TO_TEAM.items()}
# Fix multi-word edge cases
MLB_CITY_TO_TEAM_DISPLAY["boston"] = "Red Sox"
MLB_CITY_TO_TEAM_DISPLAY["chicago c"] = "Cubs"
MLB_CITY_TO_TEAM_DISPLAY["chicago w"] = "White Sox"
MLB_CITY_TO_TEAM_DISPLAY["st. louis"] = "Cardinals"
MLB_CITY_TO_TEAM_DISPLAY["st louis"] = "Cardinals"
MLB_CITY_TO_TEAM_DISPLAY["tampa bay"] = "Rays"
MLB_CITY_TO_TEAM_DISPLAY["toronto"] = "Blue Jays"
MLB_CITY_TO_TEAM_DISPLAY["los angeles d"] = "Dodgers"
MLB_CITY_TO_TEAM_DISPLAY["los angeles a"] = "Angels"
MLB_CITY_TO_TEAM_DISPLAY["new york y"] = "Yankees"
MLB_CITY_TO_TEAM_DISPLAY["new york m"] = "Mets"
MLB_CITY_TO_TEAM_DISPLAY["la dodgers"] = "Dodgers"
MLB_CITY_TO_TEAM_DISPLAY["la angels"] = "Angels"
MLB_CITY_TO_TEAM_DISPLAY["ny yankees"] = "Yankees"
MLB_CITY_TO_TEAM_DISPLAY["ny mets"] = "Mets"
MLB_CITY_TO_TEAM_DISPLAY["san francisco"] = "Giants"
MLB_CITY_TO_TEAM_DISPLAY["san diego"] = "Padres"
MLB_CITY_TO_TEAM_DISPLAY["kansas city"] = "Royals"
MLB_CITY_TO_TEAM_DISPLAY["arizona"] = "Diamondbacks"
```

- [ ] **Step 3: Update `MLB_TEAM_NAMES` and `NHL_TEAM_NAMES` export line**

Find the lines that define `NBA_TEAM_NAMES` and `NHL_TEAM_NAMES` (around line 41–42). They already exist. Just verify `MLB_TEAM_NAMES` is defined in the same block (it was added in Step 2 above — confirm the line is present).

- [ ] **Step 4: Verify syntax**

```bash
python -c "from matching import MLB_CITY_TO_TEAM, MLB_CITY_TO_TEAM_DISPLAY, MLB_TEAM_NAMES; print(len(MLB_CITY_TO_TEAM), 'entries')"
```

Expected: `35 entries` (approximate — actual count depends on aliases added).

- [ ] **Step 5: Commit**

```bash
git add matching.py
git commit -m "feat: add MLB_CITY_TO_TEAM maps to matching.py"
```

---

### Task 4: Update `_kalshi_title_to_teams` and `substitute_teams_in_title`

**Files:**
- Modify: `matching.py` (`_kalshi_title_to_teams` ~line 100, `substitute_teams_in_title` ~line 82)

- [ ] **Step 1: Update `_kalshi_title_to_teams` to accept a mapping parameter**

Find `_kalshi_title_to_teams` (line ~100). Change the signature and mapping selection:

```python
def _kalshi_title_to_teams(title, sport_prefix, mapping=None):
    """Parse Kalshi 'CityA at CityB ...' → set of team names (lowercase)."""
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
```

- [ ] **Step 2: Update `substitute_teams_in_title` to handle MLB**

Find `substitute_teams_in_title` (line ~82). Change to:

```python
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
```

- [ ] **Step 3: Verify syntax**

```bash
python -c "from matching import _kalshi_title_to_teams, substitute_teams_in_title; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add matching.py
git commit -m "feat: update title helpers to support MLB sport prefix"
```

---

### Task 5: Refactor `match_polymarket` — extract `_match_nba_nhl` and add `_match_mlb`

**Files:**
- Modify: `matching.py` (`match_polymarket` function, ~line 187)

- [ ] **Step 1: Extract existing `match_polymarket` body into `_match_nba_nhl`**

Add a new private function `_match_nba_nhl` directly before `match_polymarket`. This is the existing logic, extended to support MLB via an explicit if/elif chain wherever the old code had a binary NBA/NHL ternary:

```python
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
```

- [ ] **Step 2: Add `_match_mlb` after `_match_nba_nhl`**

```python
def _match_mlb(kalshi_data, poly_index, spread_index, floor_strike):
    """Match MLB Kalshi market to Polymarket. Same structure as NBA/NHL."""
    return _match_nba_nhl(kalshi_data, poly_index, spread_index, floor_strike, "MLB")
```

- [ ] **Step 3: Replace `match_polymarket` body with a dispatch**

Replace the entire body of `match_polymarket` with:

```python
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
```

Note: `_match_ucl` will be defined in Task 6. For now this will raise `NameError` if a UCL market is encountered. That is acceptable during development — UCL matching will be wired up in Task 6.

- [ ] **Step 4: Verify syntax and NBA/NHL matching still works**

```bash
python -c "
from matching import match_polymarket, build_polymarket_index
poly_index, spread_index = build_polymarket_index([])
result = match_polymarket({'sport': 'NBA - Game Winner', 'title': 'Boston at Miami Winner?', 'detail': 'Miami'}, poly_index, spread_index)
print('NBA dispatch OK, result:', result)
result = match_polymarket({'sport': 'MLB - Game Winner', 'title': 'Boston at New York Y Winner?', 'detail': 'Yankees'}, poly_index, spread_index)
print('MLB dispatch OK, result:', result)
"
```

Expected: both print without error (both return `None` since index is empty — that's correct).

- [ ] **Step 5: Commit**

```bash
git add matching.py
git commit -m "feat: refactor match_polymarket to per-sport dispatch, add _match_mlb"
```

---

### Task 6: Inspect Polymarket UCL structure and implement `_match_ucl`

**Files:**
- Modify: `matching.py` (new `_match_ucl` function, update `build_polymarket_index`)

- [ ] **Step 1: Inspect live Polymarket UCL events**

Create a temporary diagnostic script `scripts/inspect_poly_ucl.py`:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
import requests, json

resp = requests.get(
    "https://gamma-api.polymarket.com/events",
    params={"tag_id": 100639, "active": "true", "closed": "false", "limit": 100},
    timeout=15,
)
events = resp.json()

ucl_events = [e for e in events if "champions" in e.get("title", "").lower() or "ucl" in e.get("title", "").lower()]
print(f"Found {len(ucl_events)} UCL events")
for event in ucl_events[:5]:
    print(f"\nEvent: {event.get('title')!r}")
    for mkt in event.get("markets", [])[:6]:
        print(f"  sportsMarketType: {mkt.get('sportsMarketType')!r}")
        print(f"  question: {mkt.get('question')!r}")
        print(f"  outcomes: {mkt.get('outcomes')!r}")
```

Run it:

```bash
uv run scripts/inspect_poly_ucl.py
```

Expected: UCL event titles and their market question formats printed. Note:
- What `sportsMarketType` values appear (e.g. `"moneyline"`, `"match_result"`, `None`)
- Whether questions follow `"Team A vs. Team B"` or another format
- How draw/tie markets are phrased (e.g. `"Will the match end in a draw?"` vs `"Bayern Munich vs Real Madrid: Draw?"`)

- [ ] **Step 2: Update `build_polymarket_index` if UCL markets are being dropped**

In `matching.py`, find the `sportsMarketType` check in `build_polymarket_index` (~line 148):

```python
if smt not in ("moneyline", "totals", "spreads"):
    continue
```

Based on the inspection output, add any UCL-specific types to the allowlist. For example, if UCL uses `"match_result"`:

```python
if smt not in ("moneyline", "totals", "spreads", "match_result"):
    continue
```

If UCL markets have `sportsMarketType = None` or empty, add fallback parsing: if `smt` is falsy but the question contains `" vs "` or `" vs. "`, treat it as `"moneyline"`.

Also add a debug log for unindexed markets (can be removed after tuning):

```python
# At end of for loop in build_polymarket_index, after the index.setdefault line:
# (Add just before the return statement)
```

Actually add this just before `return index, spread_index`:

```python
    # Debug: sample unindexed questions (remove after tuning)
    # Use the same allowlist you set at the top of this function
    _INDEXED_TYPES = {"moneyline", "totals", "spreads"}  # extend if you added more above
    _unindexed = [
        mkt.get("question", "")
        for event in poly_events
        for mkt in event.get("markets", [])
        if mkt.get("sportsMarketType") not in _INDEXED_TYPES
        and ("ucl" in mkt.get("question", "").lower() or "champions" in mkt.get("question", "").lower())
    ]
    if _unindexed:
        import sys
        print(f"  [debug] {len(_unindexed)} UCL markets not indexed. Samples:", file=sys.stderr)
        for q in _unindexed[:3]:
            print(f"    {q!r}", file=sys.stderr)
```

- [ ] **Step 3: Implement `_match_ucl`**

Add `_match_ucl` after `_match_mlb` in `matching.py`. Adjust the draw-question pattern based on what you observed in Step 1:

```python
def _match_ucl(kalshi_data, poly_index, spread_index, floor_strike):
    """Match UCL Kalshi market to Polymarket."""
    sport_cat = kalshi_data["sport"]
    title = kalshi_data["title"]
    title_lower = title.lower()

    # Determine market type from Kalshi sport category
    if "Total" in sport_cat:
        target_type = "totals"
    elif "Spread" in sport_cat:
        target_type = "spreads"
    else:
        target_type = "moneyline"

    # Extract club names from Kalshi title: "Bayern Munich at Atalanta Winner?"
    match = re.match(r"^(.+?)\s+(?:at|vs\.?)\s+(.+?)(?:\s*[:?]|\s+Winner|\s+Total|\s+Spread|\s+Goals)", title, re.I)
    if not match:
        return None
    club1 = match.group(1).strip().lower()
    club2 = match.group(2).strip().lower()

    # Is this a draw/tie market?
    is_draw = "draw" in title_lower or "tie" in title_lower

    if target_type == "spreads" and spread_index is not None:
        # UCL spread: best-effort, reuse spread_index by club name
        for club in [club1, club2]:
            if floor_strike is not None:
                line = abs(floor_strike)
            else:
                m_line = re.search(r"over\s+([\d.]+)", title, re.I)
                line = float(m_line.group(1)) if m_line else None
            if line is None:
                continue
            best = spread_index.get((club, line))
            if best:
                return {
                    "poly_yes": best["outcome1_ask"],
                    "poly_no": best["outcome2_ask"],
                    "poly_volume": best["volume"],
                    "poly_question": best["question"],
                }
        return None

    key = frozenset([club1, club2])
    poly_markets = poly_index.get(key)
    if not poly_markets:
        return None

    if is_draw:
        # Find a draw-specific market
        for pm in poly_markets:
            q_lower = pm["question"].lower()
            if "draw" in q_lower or "tie" in q_lower:
                return {
                    "poly_yes": pm["outcome1_ask"],
                    "poly_no": pm["outcome2_ask"],
                    "poly_volume": pm["volume"],
                    "poly_question": pm["question"],
                }
        return None

    if target_type == "totals" and floor_strike is not None:
        for pm in poly_markets:
            if pm["market_type"] == "totals" and pm["threshold"] == floor_strike:
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

    # Moneyline: match by club name in Polymarket outcomes
    detail_lower = kalshi_data.get("detail", "").lower()
    for pm in poly_markets:
        if pm["market_type"] != "moneyline":
            continue
        o1_lower = pm["outcome1"].lower()
        o2_lower = pm["outcome2"].lower()
        # Find which club is the "yes" side based on Kalshi's yes_sub_title (detail)
        yes_club = None
        for club in [club1, club2]:
            if club in detail_lower:
                yes_club = club
                break
        if yes_club is None:
            return {
                "poly_yes": pm["outcome1_ask"],
                "poly_no": pm["outcome2_ask"],
                "poly_volume": pm["volume"],
                "poly_question": pm["question"],
            }
        if yes_club in o1_lower:
            return {
                "poly_yes": pm["outcome1_ask"],
                "poly_no": pm["outcome2_ask"],
                "poly_volume": pm["volume"],
                "poly_question": pm["question"],
            }
        elif yes_club in o2_lower:
            return {
                "poly_yes": pm["outcome2_ask"],
                "poly_no": pm["outcome1_ask"],
                "poly_volume": pm["volume"],
                "poly_question": pm["question"],
            }
        return {
            "poly_yes": pm["outcome1_ask"],
            "poly_no": pm["outcome2_ask"],
            "poly_volume": pm["volume"],
            "poly_question": pm["question"],
        }
    return None
```

- [ ] **Step 4: Delete diagnostic script**

```bash
rm scripts/inspect_poly_ucl.py
rmdir scripts 2>/dev/null || true
```

- [ ] **Step 5: Verify syntax**

```bash
python -c "from matching import match_polymarket, _match_ucl, _match_mlb; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add matching.py
git commit -m "feat: add _match_ucl and update build_polymarket_index for UCL"
```

---

## Chunk 2: dashboard_generator.py + end-to-end verification

### Task 7: Update dashboard_generator.py

**Files:**
- Modify: `dashboard_generator.py` (lines 69–88, 79, 152–162)

- [ ] **Step 1: Add `"draw"` market type detection and fix `sport_prefix` ternary**

Find `extract_market_data` in `dashboard_generator.py`. Around line 69–77, the market type is detected. Also around line 87, `sport_prefix` is set. Replace both blocks:

Current market type block (lines 69–77):
```python
    sport_cat = sport_name.lower()
    if "total" in sport_cat:
        market_type = "totals"
    elif "spread" in sport_cat:
        market_type = "spread"
    elif "winner" in sport_cat or "game" in sport_cat:
        market_type = "winner"
    else:
        market_type = "other"
```

Replace with:
```python
    sport_cat = sport_name.lower()
    title_lower = market.get("title", "").lower()
    sub_title_lower = (market.get("yes_sub_title") or "").lower()
    if "total" in sport_cat:
        market_type = "totals"
    elif "spread" in sport_cat:
        market_type = "spread"
    elif "draw" in title_lower or "tie" in title_lower or "draw" in sub_title_lower:
        # Draw check must come BEFORE the winner check: UCL draw markets are served
        # under KXUCLGAME (sport_name "UCL - Match Winner"), which contains "winner".
        # If winner check ran first, draw markets would never be classified as "draw".
        market_type = "draw"
    elif "winner" in sport_cat or "game" in sport_cat:
        market_type = "winner"
    else:
        market_type = "other"
```

Current `sport_prefix` line (line ~87):
```python
    sport_prefix = "NBA" if "NBA" in sport_name.upper() else ("NHL" if "NHL" in sport_name.upper() else "")
```

Replace with:
```python
    if "NBA" in sport_name.upper():
        sport_prefix = "NBA"
    elif "NHL" in sport_name.upper():
        sport_prefix = "NHL"
    elif "MLB" in sport_name.upper():
        sport_prefix = "MLB"
    elif "UCL" in sport_name.upper():
        sport_prefix = "UCL"
    else:
        sport_prefix = ""
```

- [ ] **Step 2: Update the arb exclusion gate**

Find line ~79:
```python
    if poly_yes is not None and poly_no is not None and market_type != "winner":
```

Replace with:
```python
    if poly_yes is not None and poly_no is not None and market_type not in ("winner", "draw"):
```

- [ ] **Step 3: Update the `is_winner` check to include draw**

Find in `generate_html` (~line 227):
```python
        is_winner = m["market_type"] == "winner"
```

Replace with:
```python
        is_winner = m["market_type"] in ("winner", "draw")
```

This ensures draw rows also show `—` in No columns and skip the No odds display, matching the intended behavior.

- [ ] **Step 4: Add "Draw" filter button**

Find the `type_toggles` f-string (~line 158–161):
```python
    type_toggles = ''.join(
        f'<button class="filter-btn multi-toggle" data-group="type" data-value="{val}" onclick="multiToggle(\'type\',\'{val}\',this)">{label}</button>'
        for val, label in [("winner", "Winner"), ("totals", "Totals"), ("spread", "Spread")]
    )
```

Replace with:
```python
    type_toggles = ''.join(
        f'<button class="filter-btn multi-toggle" data-group="type" data-value="{val}" onclick="multiToggle(\'type\',\'{val}\',this)">{label}</button>'
        for val, label in [("winner", "Winner"), ("draw", "Draw"), ("totals", "Totals"), ("spread", "Spread")]
    )
```

- [ ] **Step 4b: Add draw branch to `market_name_html` builder**

Find the `market_name_html` builder in `generate_html` (~lines 197–219). It has branches for `winner`, `totals`, `spread`, and a final `else`. Insert a `"draw"` branch after the `"winner"` branch (around line 202):

```python
        elif mtype == "draw":
            # "Bayern Munich at Atalanta — Draw"
            name_line1 = f'{base_title} — Draw'
            name_line2 = date_label if date_label else ''
```

This prevents draw rows from falling through to the `else` branch which renders the raw unstripped title.

- [ ] **Step 5: Verify syntax**

```bash
cd /Users/roydagon/personal/kalshi-odds-dashboard
uv run --with python-dotenv --with requests --with cryptography -c "
import sys; sys.argv = ['']
# Just check parse-level imports, not runtime
import ast, pathlib
src = pathlib.Path('dashboard_generator.py').read_text()
ast.parse(src)
print('dashboard_generator.py syntax OK')
src = pathlib.Path('matching.py').read_text()
ast.parse(src)
print('matching.py syntax OK')
"
```

Expected: both `OK` lines printed with no errors.

- [ ] **Step 6: Commit**

```bash
git add dashboard_generator.py
git commit -m "feat: add draw market type, UCL/MLB sport_prefix, update arb gate and filter"
```

---

### Task 8: End-to-end verification

- [ ] **Step 1: Run the dashboard for one cycle**

```bash
cd /Users/roydagon/personal/kalshi-odds-dashboard
timeout 120 uv run dashboard_generator.py 2>&1 | head -60
```

Expected output includes lines like:
```
  Fetching MLB - Game Winner (KXMLBGAME)...
    Found N markets
  Fetching UCL - Match Winner (KXUCLGAME)...
    Found N markets
  ...
  Matched X Kalshi markets to Polymarket
  Updated dashboard.html (N markets, refresh #1)
```

If `KXMLBTOTAL` or `KXMLBSPREAD` return 0 markets, that's expected (MLB regular season may not have started).

- [ ] **Step 2: Check the dashboard for MLB and UCL rows**

Open `dashboard.html` in a browser (or `grep` for team names):

```bash
grep -i "yankees\|dodgers\|astros\|marlins\|guardians" dashboard.html | head -5
grep -i "Bayern\|Real Madrid\|Barcelona\|Arsenal" dashboard.html | head -5
```

Expected: MLB team names appear substituted (not raw city abbreviations), and UCL club names appear.

- [ ] **Step 3: Check that Draw rows appear for UCL**

```bash
grep -i 'data-market-type="draw"' dashboard.html | head -5
```

Expected: at least one draw row if UCL match winner markets are available.

- [ ] **Step 4: Check for Python errors in stderr**

Rerun with stderr visible:

```bash
timeout 120 uv run dashboard_generator.py 2>/tmp/dash_err.txt; cat /tmp/dash_err.txt
```

Expected: no unhandled exceptions. Debug lines about unindexed UCL markets are acceptable and informative.

- [ ] **Step 5: Spot-check Polymarket match rate**

Look at the console output line:
```
Matched X Kalshi markets to Polymarket
```

Two distinct failure scenarios to distinguish:

- **"Found 0 markets" for KXMLBTOTAL / KXMLBSPREAD** — expected if MLB regular season hasn't started yet. Not a bug.
- **KXMLBGAME returns markets but 0 matched to Polymarket** — indicates `MLB_CITY_TO_TEAM` key format is wrong. Re-run Task 1 diagnostic to inspect live MLB titles and update the map keys accordingly.
- **UCL markets fetched but 0 matched** — indicates `build_polymarket_index` is not indexing UCL events (wrong `sportsMarketType` or question format). Re-run the Task 6 Step 1 diagnostic (`inspect_poly_ucl.py`) and update the allowlist/parser in `build_polymarket_index`.

- [ ] **Step 6: Final commit**

```bash
git add dashboard.html
git commit -m "chore: regenerate dashboard with MLB and UCL markets"
```
