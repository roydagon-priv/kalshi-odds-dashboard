# Kalshi Sports Odds Dashboard

## Goal
Interactive HTML dashboard displaying live sports (and eventually politics) odds from Kalshi, cross-referenced with Polymarket for arbitrage detection.

## Architecture

| File | Purpose |
|------|---------|
| `kalshi_fetcher.py` | Authenticated Kalshi REST calls (RSA-signed), series-based market fetching |
| `polymarket_fetcher.py` | Fetches Polymarket sports events via public API |
| `matching.py` | Cross-platform team/market alignment (Kalshi ↔ Polymarket) |
| `dashboard_generator.py` | Data processing, HTML generation, main refresh loop |
| `dashboard.html` | Generated output — open in any browser |

## Kalshi API
- Base URL: `https://api.elections.kalshi.com/trade-api/v2`
- Auth: RSA-signed requests (`KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-TIMESTAMP`, `KALSHI-ACCESS-SIGNATURE`)
- Env vars: `KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY_PATH`
- Markets fetched by `series_ticker` with `status=open`

## Currently Supported Markets

### Sports (active)
| Sport | Market Types | Series Tickers |
|-------|-------------|----------------|
| NBA | Game Winner, Total Points, Spread | KXNBAGAME, KXNBATOTAL, KXNBASPREAD |
| NHL | Game Winner, Total Points, Spread | KXNHLGAME, KXNHLTOTAL, KXNHLSPREAD |
| UCL | Match Winner, Spread | KXUCLGAME, KXUCLSPREAD |
| MLB | Game Winner, Total Points, Spread | KXMLBGAME, KXMLBTOTAL, KXMLBSPREAD |
| F1 | Race Winner, Pole Position, Fastest Lap, Podium, Top 5, Top 10 | KXF1RACE, KXF1POLE, KXF1FASTLAP, KXF1RACEPODIUM, KXF1TOP5, KXF1TOP10 |

### Polymarket Matching (active)
- NBA and NHL: moneyline, totals (O/U threshold), spreads
- UCL: moneyline (draw support), spreads — spread titles are `"Team wins by over N.5 goals?"` (single-team format, not "A vs B")
- MLB: moneyline, totals, spreads — uses fuzzy key matching (Poly uses "city team" names like "Atlanta Braves", Kalshi maps to just "braves")
- F1: matching code exists (`_match_f1`), activates when F1 events appear on Polymarket
- Date-based disambiguation: `gameStartTime` from Polymarket and `expected_expiration_time` from Kalshi are compared to distinguish games in MLB series (same teams, multiple days)
- Only markets with `sportsMarketType` in `{"moneyline", "totals", "spreads"}` are indexed; player props and first-half variants are skipped
- Arb spread calculated only for non-winner markets (totals/spreads) where both platforms have prices

### Polymarket Tag IDs
`fetch_polymarket_sports()` queries `https://gamma-api.polymarket.com/events` using multiple tag IDs with deduplication. Sport-specific tags are needed because individual events do not always carry the generic sports tag (`100639`).

| Tag ID | Sport/Purpose |
|--------|--------------|
| 100639 | "Games" tag (NBA, NHL, UCL, soccer, etc.) |
| 100381 | MLB (events missing 100639 at event level) |
| 745 | NBA (supplemental, underrepresented in 100639) |
| 899 | NHL (supplemental, underrepresented in 100639) |
| 102070 | F1 (absent from 100639 entirely) |
| 100977 | UCL (supplemental) |
| 1234 | UCL alt tag |

To discover tag IDs for new sports: `GET https://gamma-api.polymarket.com/sports` and check the `tags` field for the relevant sport slug.

### Known Issues
- **F1 Polymarket matching**: `_match_f1` and `f1_index` exist but no F1 events are currently active on Polymarket. Matching will activate automatically when F1 events appear.

### UCL Spread Matching Notes
- Kalshi UCL spread titles use single-team format: `"Barcelona wins by over 1.5 goals?"` (no opponent in title)
- `spread_index` stores entries as lists per `(team, line)` key to handle same-team domestic+UCL collisions
- Opponent disambiguation: `dashboard_generator.py` pre-builds `ucl_opponents` dict from `KXUCLGAME` titles, passed to `match_polymarket` as `ucl_opponents`
- Token-based hint filtering splits on `[\s/\-]+` with `len >= 3` to handle Unicode variants (e.g. "Bodoe/Glimt" ↔ "FK Bodø/Glimt" matched via "glimt")

## Planned Expansions

### Additional Sports
These are the priority additions. Each requires:
1. Adding series ticker(s) to `TARGET_SERIES` in `kalshi_fetcher.py`
2. Adding city/team name maps to `matching.py` if needed
3. Testing Polymarket match rate

| Sport | Notes |
|-------|-------|
| NFL | Offseason until ~Sept; series tickers likely KXNFLGAME/TOTAL/SPREAD |
| NCAAB | March Madness has heavy Kalshi activity |
| NCAAF | College football (fall) |
| Soccer (PL) | Premier League; team names usually consistent with Polymarket |
| Tennis (majors) | Player-vs-player, no team maps needed |
| Golf (PGA/Majors) | Multi-outcome markets, different structure |
| MMA/UFC | Fighter names, binary outcome |

### Politics (future, hard)
Politics markets are harder to match across platforms because:
- No shared structured schema (unlike sports team names)
- Question phrasing varies significantly between Kalshi and Polymarket
- Multi-outcome Kalshi markets vs binary Polymarket markets
- Resolution criteria can differ (e.g. date cutoffs)

Approach when implementing:
- Fuzzy text matching on question titles (normalize candidate/entity names)
- Maintain a manual `POLITICS_ALIASES` map for known entity name variants
- Match on market category slug (Kalshi `category` field) + entity name
- Consider treating politics as "display only" (no arb calc) since cross-platform arb is riskier
- Kalshi politics series tickers are not prefixed like sports — need to discover via category filter
- Polymarket has a `category` field on events; filter for `"politics"` or `"elections"`

## Dashboard Features
- Table: market name, Yes/No odds (Kalshi + Polymarket), arb profit, platform spread, volume, status
- Arb row highlighting: red border (>3¢ profit), amber border (0–3¢)
- Best-line glow on whichever platform has better odds
- Price movement indicators (↑↓ vs previous refresh)
- Filters: sport, market type, date, both-platforms, has-volume, odds-moved, arb-only
- Search by market name
- Auto-refresh every 60 seconds (anchored to actual last-fetch time)
- Filter/sort state persisted in `sessionStorage` across reloads

## Technical Stack
- Python 3.10+ with `uv` inline script deps (`# /// script`)
- Dependencies: `python-dotenv`, `kalshi_python_sync`, `requests`, `cryptography`
- HTML generated via f-strings in `dashboard_generator.py`
- Fonts: Syne (UI labels) + DM Mono (data values) via Google Fonts

## Running
```bash
uv run dashboard_generator.py
# or
./start.sh
```
