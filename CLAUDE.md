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
| F1 | Race Winner, Pole Position, Fastest Lap, Podium, Top 5, Top 10 | KXF1RACE, KXF1POLE, KXF1FASTLAP, KXF1RACEPODIUM, KXF1TOP5, KXF1TOP10 |

### Polymarket Matching (active)
- NBA and NHL: moneyline, totals (O/U threshold), spreads
- Matching uses team-name normalization (`matching.py` city→team maps)
- F1: no Polymarket match (returns `None`)
- Arb spread calculated only for non-winner markets (totals/spreads) where both platforms have prices

## Planned Expansions

### Additional Sports
These are the priority additions. Each requires:
1. Adding series ticker(s) to `TARGET_SERIES` in `kalshi_fetcher.py`
2. Adding city/team name maps to `matching.py` if needed
3. Testing Polymarket match rate

| Sport | Notes |
|-------|-------|
| NFL | Offseason until ~Sept; series tickers likely KXNFLGAME/TOTAL/SPREAD |
| MLB | Season starts ~April; large volume |
| NCAAB | March Madness has heavy Kalshi activity |
| NCAAF | College football (fall) |
| Soccer (PL/UCL) | Polymarket match harder — team names usually consistent |
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
