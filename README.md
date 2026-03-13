# Kalshi Odds Dashboard

Interactive HTML dashboard displaying live sports odds from [Kalshi](https://kalshi.com), cross-referenced with [Polymarket](https://polymarket.com) for arbitrage detection.

## Features

- Live odds for NBA, NHL, and F1 markets (game winners, totals, spreads)
- Side-by-side Kalshi vs Polymarket prices
- Arbitrage highlighting — red (>3¢ profit), amber (0–3¢)
- Best-line glow on whichever platform has better odds
- Price movement indicators since last refresh
- Filters by sport, market type, date, arb opportunity, volume, and more
- Auto-refreshes every 60 seconds

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/roydagon-priv/kalshi-odds-dashboard.git
   cd kalshi-odds-dashboard
   ```

2. **Add credentials** — create a `.env` file:
   ```
   KALSHI_API_KEY_ID=your-api-key-id
   KALSHI_PRIVATE_KEY_PATH=/path/to/your/private-key.txt
   ```

3. **Run**
   ```bash
   uv run dashboard_generator.py
   # or
   ./start.sh
   ```

4. Open `dashboard.html` in your browser.

## Requirements

- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv) (handles dependencies automatically via inline script metadata)

## File Overview

| File | Purpose |
|------|---------|
| `kalshi_fetcher.py` | Authenticated Kalshi REST calls (RSA-signed) |
| `polymarket_fetcher.py` | Fetches Polymarket sports events via public API |
| `matching.py` | Cross-platform team/market alignment |
| `dashboard_generator.py` | Data processing, HTML generation, refresh loop |
| `dashboard.html` | Generated output — open in any browser |
