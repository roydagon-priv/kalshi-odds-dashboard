# MLB + UCL Addition Design

**Date:** 2026-03-14
**Status:** Approved

## Overview

Add MLB (game winner, total runs, run line) and UCL (match winner, total goals, spread) markets to the Kalshi/Polymarket sports odds dashboard, with full Polymarket cross-matching and arbitrage detection.

---

## Series Tickers (confirmed via Kalshi API)

| Sport | Market Type | Series Ticker |
|-------|-------------|---------------|
| MLB | Game Winner | `KXMLBGAME` |
| MLB | Total Runs | `KXMLBTOTAL` |
| MLB | Run Line | `KXMLBSPREAD` |
| UCL | Match Winner | `KXUCLGAME` |
| UCL | Total Goals | `KXUCLTOTAL` |
| UCL | Spread | `KXUCLSPREAD` |

Note: `KXMLBTOTAL` and `KXMLBSPREAD` only returned settled markets during discovery (World Series 2025). They will return 0 open markets until the regular season populates — this is handled gracefully (fetcher prints `Found 0 markets` and continues).

---

## Architecture

### `kalshi_fetcher.py`
Add the 6 new entries to `TARGET_SERIES`. No other changes.

### `matching.py`

#### New team maps

`MLB_CITY_TO_TEAM` — maps Kalshi city/abbreviation keys to team names. Must cover all 30 teams with explicit disambiguation for multi-team cities:
- `"new york y"` → `"yankees"`, `"new york m"` → `"mets"`
- `"los angeles d"` → `"dodgers"`, `"los angeles a"` → `"angels"`
- `"chicago c"` → `"cubs"`, `"chicago w"` → `"white sox"`
- `"san francisco"` → `"giants"`, `"oakland"` → `"athletics"` (or current team name)
- All other single-city teams map directly

**Important:** The exact Kalshi title format for MLB (e.g. whether it uses `"new york y"` or `"nyy"` or full team name) must be verified against live market titles from `KXMLBGAME`. An early implementation step will fetch and print 10 sample MLB market titles to confirm the key format before finalizing the map.

`MLB_CITY_TO_TEAM_DISPLAY` — same pattern as `NBA_CITY_TO_TEAM_DISPLAY` and `NHL_CITY_TO_TEAM_DISPLAY`: title-cased values with manual overrides for multi-word edge cases (e.g. `"white sox"`, `"red sox"`, `"blue jays"`).

No UCL team map needed — club names on both platforms are full names; lowercase normalization is sufficient.

#### Refactor `match_polymarket`

Dispatch by sport prefix to named handler functions:
- `"NBA"` / `"NHL"` → `_match_nba_nhl(...)` (existing logic extracted verbatim)
- `"MLB"` → `_match_mlb(...)` (same structure as `_match_nba_nhl`: moneyline, totals by run threshold, run-line spread)
- `"UCL"` → `_match_ucl(...)` (club name normalization, draw market type, soccer-specific Polymarket parsing)

#### Update `_kalshi_title_to_teams`

Currently hardcodes `NBA_CITY_TO_TEAM` or `NHL_CITY_TO_TEAM`. Must accept a `mapping` argument (or add an explicit `"MLB"` branch) so MLB handlers can call it with `MLB_CITY_TO_TEAM`. Without this change, MLB title parsing silently falls through to NHL mapping and returns an empty set.

#### Update `substitute_teams_in_title`

Add `"MLB"` branch using `MLB_CITY_TO_TEAM_DISPLAY`. Without this, city names in MLB market titles are not substituted and display shows raw city abbreviations.

#### Update `build_polymarket_index`

Two changes needed:
1. **`sportsMarketType` allowlist:** Currently skips any market where `sportsMarketType not in ("moneyline", "totals", "spreads")`. UCL draw markets on Polymarket may use a different value (e.g. `"match_result"`, `"draw"`, or absent). Add UCL draw type to allowlist once verified against live data.
2. **Soccer question parsing:** Currently splits on `r"\s+vs\.?\s+"` to extract team pairs. If Polymarket UCL questions don't follow `"Team A vs. Team B"` format, the index will be empty for UCL. `build_polymarket_index` should log a sample of unindexed soccer questions on first run so the format can be verified and the parser updated if needed.

### `dashboard_generator.py`

#### `market_type` detection

Add `"draw"` case: if `"Draw"` or `"Tie"` appears in market title or `yes_sub_title`, classify as `market_type = "draw"`.

#### Arb exclusion gate

Line 79 currently reads `if ... and market_type != "winner"`. Must be updated to `market_type not in ("winner", "draw")`. Without this, draw rows with a matched Polymarket draw question would attempt arb calculation and produce wrong values.

#### Draw row display

Same as `"winner"` — No columns show `—`. No arb cell value.

#### `sport_prefix` detection

Line 87 has a nested ternary that must be extended for `"MLB"` and `"UCL"`. Recommend converting to explicit if/elif chain to avoid silent fallthrough that would assign `""` and skip title substitution.

#### Market Type filter

Add `"Draw"` toggle button to the hard-coded type toggle list in the Python f-string (alongside Winner / Totals / Spread). The JS filter reads `data-market-type` from rows dynamically, so no JS changes needed.

---

## Data Flow

1. `fetch_all_sports_markets` fetches all 12 series sequentially.
2. For each market, `match_polymarket` dispatches to the appropriate per-sport handler.
3. MLB: team-pair key lookup in Polymarket index, same as NBA/NHL.
4. UCL: extract club names from Kalshi title, normalize to lowercase, look up by club pair. Draw markets identified by title content and matched to Polymarket draw questions.
5. `extract_market_data` classifies draw markets as `market_type = "draw"`.
6. Dashboard renders draw rows with `—` in No columns, no arb value.

---

## Known Risks

- **MLB city-suffix key format:** Must verify against live `KXMLBGAME` market titles before finalizing `MLB_CITY_TO_TEAM`. First implementation step prints sample titles.
- **Polymarket UCL structure:** `sportsMarketType` values and question phrasing for soccer are unverified. `_match_ucl` and `build_polymarket_index` will log unmatched/unindexed markets on first run for diagnosis.
- **UCL spread Polymarket format:** The spread index parser uses `"Spread: Team (-1.5)"` regex anchored to NBA/NHL question format. UCL spread questions on Polymarket may differ. Treat UCL spread matching as best-effort; log misses.
- **Polymarket UCL draw `sportsMarketType`:** Allowlist in `build_polymarket_index` may need updating once live UCL draw market data is inspected.
