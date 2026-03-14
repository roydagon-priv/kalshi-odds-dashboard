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
- MLB: moneyline, totals, spreads
- F1: no Polymarket match (returns `None`)
- Arb spread calculated only for non-winner markets (totals/spreads) where both platforms have prices

### Known Issues
- **Spread matching regression**: The `spread_index` list-based storage + UCL opponent-hint filtering introduced in the UCL spread fix has broken spread matching for other markets (NBA, NHL, MLB). Needs a focused debugging pass — likely the list-based lookup or hint filtering leaking into non-UCL paths.
- **F1 Polymarket matching not implemented**: Polymarket now has F1 markets (race winner, etc.). `_match_f1` or similar needs to be added to `matching.py`; currently `match_polymarket` returns `None` for F1.

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
