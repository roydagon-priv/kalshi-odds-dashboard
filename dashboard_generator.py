# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "python-dotenv",
#   "kalshi_python_sync",
#   "requests",
# ]
# ///

import hashlib
import os
import re
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

from kalshi_fetcher import build_kalshi_client, fetch_all_sports_markets
from matching import build_polymarket_index, match_polymarket, safe_float, substitute_teams_in_title
from polymarket_fetcher import fetch_polymarket_sports

load_dotenv()

REFRESH_INTERVAL = 60  # seconds between API fetches


def to_american(price):
    """Convert decimal price (0-1) to American odds integer."""
    price = max(0.001, min(0.999, price))
    if price >= 0.5:
        return round(-(price / (1 - price)) * 100)
    else:
        return round(((1 - price) / price) * 100)


def fmt_american(price):
    """Format a price as American odds string, e.g. '-300' or '+150'."""
    odds = to_american(price)
    return f"+{odds}" if odds > 0 else str(odds)


# ---------------------------------------------------------------------------
# Kalshi data extraction
# ---------------------------------------------------------------------------

def extract_market_data(market, sport_name="", poly_match=None):
    yes_bid = safe_float(market.get("yes_bid_dollars"))
    yes_ask = safe_float(market.get("yes_ask_dollars"))
    no_bid = safe_float(market.get("no_bid_dollars"))
    no_ask = safe_float(market.get("no_ask_dollars"))
    volume = safe_float(market.get("volume_fp"))

    midpoint = (yes_bid + yes_ask) / 2 if (yes_bid or yes_ask) else 0.0
    implied_prob = midpoint * 100
    spread_cents = (yes_ask - yes_bid) * 100

    poly_yes = poly_match["poly_yes"] if poly_match else None
    poly_no = poly_match["poly_no"] if poly_match else None
    poly_volume = poly_match["poly_volume"] if poly_match else None
    _raw_opp = (poly_match.get("spread_opponent") or "") if poly_match else ""
    spread_opponent = _raw_opp.title().replace("76Ers", "76ers") if _raw_opp else None

    # Game date from expected_expiration_time (ISO string in UTC)
    exp = market.get("expected_expiration_time")
    game_date = exp[:10] if exp else ""

    # Market type: winner / totals / spread / other
    sport_cat = sport_name.lower()
    title_lower = market.get("title", "").lower()
    sub_title_lower = (market.get("yes_sub_title") or "").lower()
    if "total" in sport_cat:
        market_type = "totals"
    elif "spread" in sport_cat or "run line" in sport_cat:
        market_type = "spread"
    elif sub_title_lower == "tie":
        # UCL draw markets: yes_sub_title is "Tie", sport_name contains "winner"
        # Draw check must come BEFORE the winner check or it would never fire
        market_type = "draw"
    elif "winner" in sport_cat or "game" in sport_cat:
        market_type = "winner"
    else:
        market_type = "other"

    if poly_yes is not None and poly_no is not None and market_type not in ("winner", "draw"):
        cost_dir1 = yes_ask + poly_no    # buy YES on Kalshi, NO on Poly
        cost_dir2 = poly_yes + no_ask    # buy YES on Poly, NO on Kalshi
        arb_spread_cents = (1.0 - min(cost_dir1, cost_dir2)) * 100
    else:
        arb_spread_cents = None

    raw_title = market.get("title", "")
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
    display_title = substitute_teams_in_title(raw_title, sport_prefix) if sport_prefix else raw_title
    raw_detail = (market.get("yes_sub_title") or "").strip()
    display_detail = substitute_teams_in_title(raw_detail, sport_prefix) if sport_prefix else raw_detail

    return {
        "ticker": market.get("ticker", ""),
        "title": display_title,
        "detail": display_detail,
        "sport": sport_name,
        "market_type": market_type,
        "game_date": game_date,
        "yes_ask": yes_ask,
        "no_ask": no_ask,
        "poly_yes": poly_yes,
        "poly_no": poly_no,
        "poly_volume": poly_volume,
        "spread_opponent": spread_opponent,
        "arb_spread_cents": arb_spread_cents,
        "spread_cents": spread_cents,
        "implied_prob": implied_prob,
        "volume": volume,
        "status": market.get("status", ""),
    }


def row_color_class(m):
    arb = m["arb_spread_cents"]
    if arb is not None and arb > 3:
        return "row-arb-high"
    if arb is not None and arb > 0:
        return "row-arb-mid"
    return ""


def generate_html(markets_data, timestamp, prev_prices=None):
    prev_prices = prev_prices or {}
    refresh_epoch_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    def _move(ticker, field, current):
        """Return HTML movement indicator if price changed since last refresh."""
        if current is None:
            return ""
        prev = prev_prices.get(ticker, {}).get(field)
        if prev is None:
            return ""
        prev_odds = to_american(prev)
        cur_odds = to_american(current)
        delta = cur_odds - prev_odds
        if delta == 0:
            return ""
        if delta > 0:
            return f'<span class="move-up">↑{delta}</span>'
        return f'<span class="move-dn">↓{abs(delta)}</span>'

    # Collect unique top-level sports for filter buttons
    sports = []
    seen = set()
    for m in markets_data:
        top = m["sport"].split(" - ")[0]
        if top not in seen:
            seen.add(top)
            sports.append(top)

    # Collect unique dates (sorted)
    dates = sorted({m["game_date"] for m in markets_data if m["game_date"]})

    sport_toggles = ''.join(
        f'<button class="filter-btn multi-toggle" data-group="sport" data-value="{s}" onclick="multiToggle(\'sport\',\'{s}\',this)">{s}</button>'
        for s in sports
    )
    sport_group_html = f'<div class="filter-group"><span class="filter-label">Sport</span><div class="toggle-group" id="group-sport">{sport_toggles}</div></div>'

    type_toggles = ''.join(
        f'<button class="filter-btn multi-toggle" data-group="type" data-value="{val}" onclick="multiToggle(\'type\',\'{val}\',this)">{label}</button>'
        for val, label in [("winner", "Winner"), ("draw", "Draw"), ("totals", "Totals"), ("spread", "Spread")]
    )
    type_group_html = f'<div class="filter-group"><span class="filter-label">Market Type</span><div class="toggle-group" id="group-type">{type_toggles}</div></div>'

    date_toggles = ''
    for d in dates:
        try:
            label = datetime.strptime(d, "%Y-%m-%d").strftime("%b %-d")
        except Exception:
            label = d
        date_toggles += f'<button class="filter-btn multi-toggle" data-group="date" data-value="{d}" onclick="multiToggle(\'date\',\'{d}\',this)">{label}</button>'
    date_group_html = f'<div class="filter-group"><span class="filter-label">Date</span><div class="toggle-group" id="group-date">{date_toggles}</div></div>'

    toggle_buttons_html = '<span class="filters-divider"></span>'
    toggle_buttons_html += '<button class="filter-btn toggle-btn" onclick="toggleFilter(\'poly\',this)">Both Platforms</button>'
    toggle_buttons_html += '<button class="filter-btn toggle-btn" onclick="toggleFilter(\'volume\',this)">Has Volume</button>'
    toggle_buttons_html += '<button class="filter-btn toggle-btn" onclick="toggleFilter(\'moved\',this)">Odds Moved</button>'
    toggle_buttons_html += '<button class="filter-btn filter-arb" onclick="toggleFilter(\'arb\',this)">Arb Opportunities</button>'
    toggle_buttons_html += '<button class="filter-btn toggle-btn" onclick="toggleNoColumns(this)">Hide &quot;No&quot; Columns</button>'
    toggle_buttons_html += '<button class="filter-btn clear-btn" onclick="clearAllFilters()">Clear Filters</button>'

    rows_html = ""
    for m in markets_data:
        css_class = row_color_class(m)
        top_sport = m["sport"].split(" - ")[0]
        search_text = f'{m["title"]} {m["detail"]}'.lower()

        # Format game date as "Mar 7"
        try:
            date_label = datetime.strptime(m["game_date"], "%Y-%m-%d").strftime("%b %-d") if m["game_date"] else ""
        except Exception:
            date_label = m["game_date"]

        # Build market name cell
        detail = m["detail"]
        mtype = m["market_type"]
        base_title = re.sub(r'\s*(Winner|Total Goals|Total Points|Spread)\??\s*$', '', m["title"], flags=re.I).strip()
        if mtype == "winner" and detail:
            # "Nets at Pistons — Detroit"
            name_line1 = f'{base_title} — {detail}'
            name_line2 = f'Winner · {date_label}' if date_label else 'Winner'
        elif mtype == "draw":
            # "Bayern Munich vs Atalanta — Draw · Mar 18"
            name_line1 = f'{base_title} — Draw'
            name_line2 = date_label if date_label else ''
        elif mtype == "totals" and detail:
            name_line1 = base_title
            name_line2 = f'{detail} · {date_label}' if date_label else detail
        elif mtype == "spread":
            opponent = m.get("spread_opponent") or ""
            # Extract just the team name and line from base_title: "Bucks wins by over 2.5 Points"
            spread_match = re.match(r'^(.+?)\s+wins\s+by\s+over\s+([\d.]+)', base_title, re.I)
            if spread_match and opponent:
                name_line1 = f'{spread_match.group(1)} vs {opponent}'
                name_line2 = f'Spread: {spread_match.group(1)} -{spread_match.group(2)} · {date_label}' if date_label else f'Spread: {spread_match.group(1)} -{spread_match.group(2)}'
            elif spread_match:
                name_line1 = spread_match.group(1)
                name_line2 = f'Spread: -{spread_match.group(2)} · {date_label}' if date_label else f'Spread: -{spread_match.group(2)}'
            else:
                name_line1 = base_title
                name_line2 = f'Spread · {date_label}' if date_label else 'Spread'
        else:
            name_line1 = m["title"]
            name_line2 = date_label

        market_name_html = f'{name_line1}<br><span class="detail">{name_line2}</span>' if name_line2 else name_line1
        has_poly = "yes" if m["poly_yes"] is not None else "no"
        arb_val = f'{m["arb_spread_cents"]:.1f}' if m["arb_spread_cents"] is not None else "0"

        arb_cell = f'{m["arb_spread_cents"]:.1f}¢' if m["arb_spread_cents"] is not None else '<span class="na">N/A</span>'

        is_winner = m["market_type"] in ("winner", "draw")

        # Platform spread: American odds point difference, YES-only for winner markets
        def _odds_diff(k_price, p_price, side):
            k_odds = to_american(k_price)
            p_odds = to_american(p_price)
            diff = p_odds - k_odds  # positive = Kalshi better (lower favorite / higher underdog)
            if abs(diff) < 1:
                return "Even"
            platform = "K" if diff > 0 else "P"
            return f'{platform} {abs(diff)} ({side})'

        if is_winner and m["poly_yes"] is not None:
            platform_spread_cell = _odds_diff(m["yes_ask"], m["poly_yes"], "YES")
        elif not is_winner and m["poly_yes"] is not None and m["poly_no"] is not None:
            yes_spread = _odds_diff(m["yes_ask"], m["poly_yes"], "YES")
            no_spread = _odds_diff(m["no_ask"], m["poly_no"], "NO")
            # Pick the side with the larger absolute odds difference
            yes_mag = abs(to_american(m["poly_yes"]) - to_american(m["yes_ask"]))
            no_mag = abs(to_american(m["poly_no"]) - to_american(m["no_ask"]))
            platform_spread_cell = yes_spread if yes_mag >= no_mag else no_spread
        else:
            platform_spread_cell = '<span class="na">N/A</span>'

        # Best line: green bold on whichever platform has the better (higher) odds for each side
        def _best(k_price, p_price):
            """Return ('k'|'p'|'even') — higher American odds = better for bettor."""
            if p_price is None:
                return 'k', 'p'
            k_odds = to_american(k_price)
            p_odds = to_american(p_price)
            if k_odds > p_odds:
                return 'k', 'p'
            elif p_odds > k_odds:
                return 'p', 'k'
            return 'even', 'even'

        yes_best, _ = _best(m["yes_ask"], m["poly_yes"])
        no_best, _ = _best(m["no_ask"], m["poly_no"] if not is_winner else None)

        ticker = m["ticker"]
        prev = prev_prices.get(ticker, {})
        has_moved = any(
            prev.get(f) is not None and to_american(prev[f]) != to_american(m[f])
            for f in ("yes_ask", "no_ask", "poly_yes", "poly_no")
            if m.get(f) is not None
        )
        yes_k_val = fmt_american(m["yes_ask"])
        yes_p_val = fmt_american(m["poly_yes"]) if m["poly_yes"] is not None else None

        yes_kalshi_cell = f'<span class="best-line">{yes_k_val}</span>' if yes_best == 'k' else yes_k_val
        yes_kalshi_cell += _move(ticker, "yes_ask", m["yes_ask"])
        poly_yes_cell = (f'<span class="best-line">{yes_p_val}</span>' if yes_best == 'p' else yes_p_val) if yes_p_val else '<span class="na">N/A</span>'
        if yes_p_val:
            poly_yes_cell += _move(ticker, "poly_yes", m["poly_yes"])

        if is_winner:
            no_kalshi_cell = '<span class="na">—</span>'
            no_poly_cell = '<span class="na">—</span>'
        else:
            no_k_val = fmt_american(m["no_ask"])
            no_p_val = fmt_american(m["poly_no"]) if m["poly_no"] is not None else None
            no_kalshi_cell = f'<span class="best-line">{no_k_val}</span>' if no_best == 'k' else no_k_val
            no_kalshi_cell += _move(ticker, "no_ask", m["no_ask"])
            no_poly_cell = (f'<span class="best-line">{no_p_val}</span>' if no_best == 'p' else no_p_val) if no_p_val else '<span class="na">N/A</span>'
            if no_p_val:
                no_poly_cell += _move(ticker, "poly_no", m["poly_no"])

        rows_html += f"""
        <tr class="{css_class}" data-title="{search_text}" data-sport="{top_sport}" data-poly="{has_poly}" data-arb="{arb_val}" data-market-type="{m['market_type']}" data-date="{m['game_date']}" data-volume="{1 if m['volume'] > 0 else 0}" data-moved="{1 if has_moved else 0}">
          <td class="market-name">{market_name_html}</td>
          <td>{yes_kalshi_cell}</td>
          <td>{poly_yes_cell}</td>
          <td class="col-no">{no_kalshi_cell}</td>
          <td class="col-no">{no_poly_cell}</td>
          <td>{arb_cell}</td>
          <td>{platform_spread_cell}</td>
          <td>{m['volume']:,.0f} / {f"{m['poly_volume']:,.0f}" if m['poly_volume'] is not None else '<span class="na">N/A</span>'}</td>
          <td><span class="status-badge status-{m['status']}">{m['status']}</span></td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sports Odds Dashboard — Kalshi + Polymarket</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Mono:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    :root {{
      --bg: #060b14;
      --surface: #0c1422;
      --surface2: #101c30;
      --border: #162033;
      --border-bright: #1e3050;
      --text: #b8cce0;
      --text-muted: #3d6080;
      --text-dim: #1e3050;
      --accent: #00cdb0;
      --accent-dim: #007a69;
      --green: #00e87a;
      --amber: #ffb300;
      --red: #ff4060;
      --red-dim: #6a1020;
      --poly: #8b72f8;
    }}

    body {{
      font-family: 'DM Mono', 'Courier New', monospace;
      background: var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 24px 20px;
      font-size: 13px;
      line-height: 1.4;
    }}

    /* ── Header ── */
    .header {{
      max-width: 1600px;
      margin: 0 auto 20px;
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      justify-content: space-between;
      gap: 12px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--border);
    }}
    .header-left {{ display: flex; flex-direction: column; gap: 4px; }}
    h1 {{
      font-family: 'Syne', sans-serif;
      font-size: 1.45rem;
      font-weight: 800;
      color: #fff;
      letter-spacing: -0.03em;
      line-height: 1;
    }}
    h1 span {{ color: var(--accent); }}
    .header-sub {{
      font-size: 0.68rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-family: 'Syne', sans-serif;
    }}
    .updated {{
      font-size: 0.75rem;
      color: var(--text-muted);
      display: flex;
      align-items: center;
      gap: 10px;
      font-family: 'DM Mono', monospace;
    }}
    .status-indicator {{
      display: flex;
      align-items: center;
      gap: 7px;
    }}
    .status-dot {{
      position: relative;
      width: 7px; height: 7px;
      border-radius: 50%;
      background: var(--green);
      flex-shrink: 0;
    }}
    .status-dot::after {{
      content: '';
      position: absolute;
      inset: -4px;
      border-radius: 50%;
      border: 1px solid var(--green);
      opacity: 0.5;
      animation: ring-out 2.4s ease-out infinite;
    }}
    @keyframes ring-out {{
      0% {{ transform: scale(0.4); opacity: 0.7; }}
      100% {{ transform: scale(2.2); opacity: 0; }}
    }}
    .status-dot.stale {{ background: var(--amber); }}
    .status-dot.stale::after {{ border-color: var(--amber); }}
    .status-dot.fetching {{ background: #5090ff; }}
    .status-dot.fetching::after {{ border-color: #5090ff; animation: ring-out 0.6s ease-out infinite; }}

    /* ── Controls ── */
    .controls {{
      max-width: 1600px;
      margin: 0 auto 14px;
    }}
    #search {{
      width: 100%;
      max-width: 340px;
      padding: 8px 14px;
      background: var(--surface);
      border: 1px solid var(--border-bright);
      border-radius: 5px;
      color: var(--text);
      font-family: 'DM Mono', monospace;
      font-size: 0.82rem;
      outline: none;
      transition: border-color 0.2s, box-shadow 0.2s;
    }}
    #search::placeholder {{ color: var(--text-muted); }}
    #search:focus {{
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(0,205,176,0.1);
    }}

    /* ── Filters ── */
    .filters {{
      max-width: 1600px;
      margin: 0 auto 14px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 10px;
    }}
    .filter-group {{
      display: flex;
      align-items: center;
      gap: 5px;
      flex-wrap: wrap;
    }}
    .toggle-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 3px;
    }}
    .filter-label {{
      font-family: 'Syne', sans-serif;
      color: var(--text-muted);
      font-size: 0.65rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      white-space: nowrap;
    }}
    .filter-btn {{
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid var(--border-bright);
      background: var(--surface);
      color: var(--text-muted);
      font-family: 'DM Mono', monospace;
      font-size: 0.75rem;
      cursor: pointer;
      transition: all 0.15s;
    }}
    .filter-btn:hover {{ border-color: var(--accent-dim); color: var(--text); }}
    .filter-btn.active {{
      background: rgba(0,205,176,0.1);
      border-color: var(--accent);
      color: var(--accent);
    }}
    .filter-arb {{ border-color: var(--red-dim); color: #e06070; }}
    .filter-arb:hover {{ border-color: var(--red); color: var(--red); }}
    .filter-arb.active {{ background: rgba(255,64,96,0.12); border-color: var(--red); color: var(--red); }}
    .clear-btn {{ border-color: var(--border); color: var(--text-dim); }}
    .clear-btn:hover {{ border-color: var(--text-muted); color: var(--text-muted); }}
    .filters-divider {{
      width: 1px; height: 20px;
      background: var(--border-bright);
      flex-shrink: 0;
    }}

    /* ── Legend ── */
    .legend {{
      max-width: 1600px;
      margin: 0 auto 12px;
      display: flex;
      flex-wrap: wrap;
      gap: 16px;
      font-size: 0.72rem;
      color: var(--text-muted);
      font-family: 'DM Mono', monospace;
    }}
    .legend-item {{ display: flex; align-items: center; gap: 7px; }}
    .legend-dot {{ width: 3px; height: 14px; border-radius: 2px; flex-shrink: 0; }}
    .dot-red {{ background: var(--red); }}
    .dot-orange {{ background: var(--amber); }}

    /* ── Table wrap ── */
    .table-wrap {{
      max-width: 1600px;
      margin: 0 auto;
      overflow-x: auto;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: var(--surface);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
    }}
    thead {{ background: var(--surface2); }}
    th {{
      position: sticky;
      top: 0;
      z-index: 1;
      background: var(--surface2);
      padding: 10px 14px;
      text-align: left;
      font-family: 'Syne', sans-serif;
      font-weight: 600;
      font-size: 0.62rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.12em;
      white-space: nowrap;
      cursor: pointer;
      user-select: none;
      border-bottom: 1px solid var(--border-bright);
      transition: color 0.15s;
    }}
    th:hover {{ color: var(--text); }}
    th.sorted-asc::after {{ content: " ↑"; color: var(--accent); font-size: 0.9em; }}
    th.sorted-desc::after {{ content: " ↓"; color: var(--accent); font-size: 0.9em; }}
    td {{
      padding: 9px 14px;
      border-top: 1px solid rgba(22,32,51,0.8);
      vertical-align: middle;
    }}

    /* Arb row left-border accent */
    tr.row-arb-high {{ box-shadow: inset 3px 0 0 var(--red); }}
    tr.row-arb-mid  {{ box-shadow: inset 3px 0 0 var(--amber); }}
    tr:hover td {{ background: rgba(255,255,255,0.015); }}

    .market-name {{ max-width: 300px; line-height: 1.35; }}
    .detail {{
      color: var(--text-muted);
      font-size: 0.8em;
      display: block;
      margin-top: 2px;
    }}
    .na {{ color: var(--text-dim); }}

    /* Best line: glow effect */
    .best-line {{
      color: var(--green);
      font-weight: 500;
      text-shadow: 0 0 10px rgba(0,232,122,0.45);
    }}
    .move-up {{ color: var(--green); font-size: 0.77em; margin-left: 4px; }}
    .move-dn {{ color: var(--red); font-size: 0.77em; margin-left: 4px; }}

    /* ── Status badges ── */
    .status-badge {{
      padding: 2px 7px;
      border-radius: 3px;
      font-family: 'Syne', sans-serif;
      font-size: 0.62em;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .status-active, .status-open {{
      background: rgba(0,232,122,0.1);
      color: var(--green);
      border: 1px solid rgba(0,232,122,0.2);
    }}
    .status-closed, .status-settled {{
      background: rgba(61,96,128,0.15);
      color: var(--text-muted);
      border: 1px solid var(--border-bright);
    }}
    .no-results {{
      text-align: center;
      padding: 60px;
      color: var(--text-muted);
      font-family: 'Syne', sans-serif;
    }}
    th.col-poly {{ color: var(--poly); opacity: 0.7; }}
    th.col-poly:hover {{ opacity: 1; }}
    .hide-no .col-no {{ display: none; }}
    @media (max-width: 640px) {{
      body {{ padding: 12px; }}
      h1 {{ font-size: 1.15rem; }}
      td, th {{ padding: 7px 10px; }}
    }}
  </style>
</head>
<body>
  <div class="header">
    <div class="header-left">
      <h1>Sports Odds <span>Dashboard</span></h1>
      <div class="header-sub">Kalshi · Polymarket · Live</div>
    </div>
    <span class="updated">
      <div class="status-indicator">
        <span class="status-dot" id="status-dot"></span>
        <span id="updated-text">Last updated: {timestamp}</span>
      </div>
      <span id="countdown"></span>
    </span>
  </div>
  <div class="filters">
    {sport_group_html}
    {type_group_html}
    {date_group_html}
    <div style="flex:1"></div>
    {toggle_buttons_html}
  </div>
  <div class="controls">
    <input type="text" id="search" placeholder="Search markets..." oninput="filterTable()">
  </div>
  <div class="legend">
    <span class="legend-item"><span class="legend-dot dot-red"></span> Arb profit &gt;3¢</span>
    <span class="legend-item"><span class="legend-dot dot-orange"></span> Arb profit 0–3¢</span>
    <span class="legend-item" style="color:#4a5568;">No highlight = no arb or N/A</span>
  </div>
  <div class="table-wrap">
    <table id="markets-table">
      <thead>
        <tr>
          <th onclick="sortTable(0)">Market Name</th>
          <th onclick="sortTable(1)">Yes (Kalshi)</th>
          <th onclick="sortTable(2)" class="col-poly">Yes (Poly)</th>
          <th onclick="sortTable(3)" class="col-no">No (Kalshi)</th>
          <th onclick="sortTable(4)" class="col-poly col-no">No (Poly)</th>
          <th onclick="sortTable(5)">Arb Profit</th>
          <th onclick="sortTable(6)">Platform Spread</th>
          <th onclick="sortTable(7)">Volume (K/P)</th>
          <th onclick="sortTable(8)">Status</th>
        </tr>
      </thead>
      <tbody id="table-body">
        {rows_html}
      </tbody>
    </table>
    <div id="no-results" class="no-results" style="display:none;">No markets match your search.</div>
  </div>

  <script>
    const _savedSort = JSON.parse(sessionStorage.getItem('dashSort') || '{{"col":-1,"dir":1}}');
    let sortCol = _savedSort.col, sortDir = _savedSort.dir;

    function parseCell(cell, col) {{
      const text = cell.textContent.trim();
      if (col === 0) return text.toLowerCase();
      if (text === 'N/A' || text === '—') return -Infinity;
      if (col === 6) {{
        if (text === 'Even') return 0;
        const m = text.match(/(\\d+)\\s*\\(/);
        return m ? parseInt(m[1]) : -Infinity;
      }}
      const num = parseFloat(text.replace(/[$,¢%]/g, ''));
      return isNaN(num) ? text.toLowerCase() : num;
    }}

    function sortTable(col) {{
      const tbody = document.getElementById('table-body');
      const headers = document.querySelectorAll('th');
      headers.forEach(h => h.classList.remove('sorted-asc', 'sorted-desc'));

      if (sortCol === col) sortDir *= -1;
      else {{ sortCol = col; sortDir = 1; }}

      headers[col].classList.add(sortDir === 1 ? 'sorted-asc' : 'sorted-desc');

      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {{
        const av = parseCell(a.cells[col], col);
        const bv = parseCell(b.cells[col], col);
        if (av < bv) return -1 * sortDir;
        if (av > bv) return 1 * sortDir;
        return 0;
      }});
      rows.forEach(r => tbody.appendChild(r));
      sessionStorage.setItem('dashSort', JSON.stringify({{col: sortCol, dir: sortDir}}));
    }}

    // Persist filters across reloads via sessionStorage
    const _saved = JSON.parse(sessionStorage.getItem('dashFilters') || '{{}}');
    // Multi-select sets for sport/type/date (empty = show all)
    const activeMulti = {{
      sport: new Set(_saved.sport || []),
      type:  new Set(_saved.type  || []),
      date:  new Set(_saved.date  || []),
    }};
    const activeToggles = {{ poly: !!_saved.poly, volume: !!_saved.volume, moved: !!_saved.moved, arb: !!_saved.arb }};

    function _saveState() {{
      sessionStorage.setItem('dashFilters', JSON.stringify({{
        sport: [...activeMulti.sport],
        type:  [...activeMulti.type],
        date:  [...activeMulti.date],
        ...activeToggles,
        search: document.getElementById('search').value,
      }}));
    }}

    function multiToggle(group, value, btn) {{
      if (activeMulti[group].has(value)) {{
        activeMulti[group].delete(value);
        btn.classList.remove('active');
      }} else {{
        activeMulti[group].add(value);
        btn.classList.add('active');
      }}
      _saveState();
      filterTable();
    }}

    function toggleFilter(key, btn) {{
      activeToggles[key] = !activeToggles[key];
      btn.classList.toggle('active', activeToggles[key]);
      _saveState();
      filterTable();
    }}

    function clearAllFilters() {{
      activeMulti.sport.clear();
      activeMulti.type.clear();
      activeMulti.date.clear();
      activeToggles.poly = false;
      activeToggles.volume = false;
      activeToggles.moved = false;
      activeToggles.arb = false;
      document.getElementById('search').value = '';
      document.querySelectorAll('.multi-toggle, .toggle-btn, .filter-arb').forEach(b => b.classList.remove('active'));
      if (noColsHidden) {{ noColsHidden = false; document.getElementById('markets-table').classList.remove('hide-no'); }}
      _saveState();
      filterTable();
    }}

    let noColsHidden = JSON.parse(sessionStorage.getItem('hideNoCols') || 'false');
    function toggleNoColumns(btn) {{
      noColsHidden = !noColsHidden;
      document.getElementById('markets-table').classList.toggle('hide-no', noColsHidden);
      btn.classList.toggle('active', noColsHidden);
      sessionStorage.setItem('hideNoCols', JSON.stringify(noColsHidden));
    }}

    function filterTable() {{
      const query = document.getElementById('search').value.toLowerCase();
      const rows = document.querySelectorAll('#table-body tr');
      let visible = 0;
      rows.forEach(row => {{
        const title   = row.getAttribute('data-title') || '';
        const sport   = row.getAttribute('data-sport') || '';
        const hasPoly = row.getAttribute('data-poly') || 'no';
        const arbVal  = parseFloat(row.getAttribute('data-arb') || '0');
        const mtype   = row.getAttribute('data-market-type') || '';
        const date    = row.getAttribute('data-date') || '';
        const hasVolume = row.getAttribute('data-volume') === '1';

        const matchSearch  = title.includes(query);
        const matchSport   = activeMulti.sport.size === 0 || activeMulti.sport.has(sport);
        const matchType    = activeMulti.type.size  === 0 || activeMulti.type.has(mtype);
        const matchDate    = activeMulti.date.size  === 0 || activeMulti.date.has(date);
        const matchPoly    = !activeToggles.poly   || hasPoly === 'yes';
        const matchVolume  = !activeToggles.volume || hasVolume;
        const matchMoved   = !activeToggles.moved  || row.getAttribute('data-moved') === '1';
        const matchArb     = !activeToggles.arb    || arbVal > 0;

        const show = matchSearch && matchSport && matchType && matchDate && matchPoly && matchVolume && matchMoved && matchArb;
        row.style.display = show ? '' : 'none';
        if (show) visible++;
      }});
      document.getElementById('no-results').style.display = visible === 0 ? 'block' : 'none';
    }}

    // Restore UI state on load
    document.querySelectorAll('.multi-toggle').forEach(btn => {{
      const g = btn.getAttribute('data-group');
      const v = btn.getAttribute('data-value');
      if (activeMulti[g] && activeMulti[g].has(v)) btn.classList.add('active');
    }});
    if (_saved.search) document.getElementById('search').value = _saved.search;
    document.querySelectorAll('.toggle-btn, .filter-arb').forEach(btn => {{
      const key = btn.getAttribute('onclick').match(/toggleFilter\\('(\\w+)'/)?.[1];
      if (key && activeToggles[key]) btn.classList.add('active');
    }});
    if (noColsHidden) {{
      document.getElementById('markets-table').classList.add('hide-no');
    }}
    filterTable();
    if (sortCol >= 0) {{
      // Restore sort: force sortDir to saved value by presetting state so sortTable doesn't flip it
      const savedDir = sortDir;
      sortCol = -1;          // make sortTable treat it as a new column
      sortTable(_savedSort.col);  // sets sortDir = 1
      if (savedDir === -1) sortTable(_savedSort.col);  // flip to descending if needed
    }}

    // Countdown + auto-reload anchored to actual last-refresh time embedded by Python
    const REFRESH_INTERVAL = {REFRESH_INTERVAL};
    const LAST_REFRESH_MS = {refresh_epoch_ms};
    const dot = document.getElementById('status-dot');
    const countdown = document.getElementById('countdown');
    let polling = false;

    setInterval(() => {{
      if (polling) return;
      const elapsed = Math.floor((Date.now() - LAST_REFRESH_MS) / 1000);
      const secondsLeft = REFRESH_INTERVAL - elapsed;
      if (secondsLeft <= 0) {{
        polling = true;
        dot.className = 'status-dot fetching';
        countdown.textContent = '(refreshing...)';
        // Save state then reload — sessionStorage persists across reloads
        _saveState();
        const msUntilNext = Math.max(1000, (LAST_REFRESH_MS + REFRESH_INTERVAL * 1000) - Date.now());
        setTimeout(() => location.reload(), msUntilNext + 2000);
      }} else {{
        const isStale = secondsLeft <= 10;
        dot.className = 'status-dot' + (isStale ? ' stale' : '');
        countdown.textContent = `(next refresh in ${{secondsLeft}}s)`;
      }}
    }}, 1000);
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    api_key_id = os.getenv("KALSHI_API_KEY_ID")
    private_key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "").strip("'\"")

    if not api_key_id:
        print("ERROR: KALSHI_API_KEY_ID not set in environment.", file=sys.stderr)
        sys.exit(1)
    if not private_key_path:
        print("ERROR: KALSHI_PRIVATE_KEY_PATH not set in environment.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(private_key_path) as f:
            private_key = f.read()
    except FileNotFoundError:
        print(f"ERROR: Private key file not found: {private_key_path}", file=sys.stderr)
        sys.exit(1)

    try:
        client = build_kalshi_client(api_key_id, private_key)
    except Exception as e:
        print(f"ERROR: Failed to initialize Kalshi client: {e}", file=sys.stderr)
        sys.exit(1)

    output_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    last_fingerprint = None
    refresh_count = 0
    prev_prices = {}  # ticker → {yes_ask, no_ask, poly_yes, poly_no}

    print(f"Starting dashboard loop (refresh every {REFRESH_INTERVAL}s). Press Ctrl+C to stop.")
    try:
        while True:
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            print(f"Refreshing... {timestamp}")

            # Fetch both platforms
            try:
                sports_markets = fetch_all_sports_markets(client)
            except Exception as e:
                print(f"  WARNING: Kalshi fetch failed: {e} — will retry next cycle", file=sys.stderr)
                time.sleep(REFRESH_INTERVAL)
                continue

            print("  Fetching Polymarket sports...")
            poly_events = fetch_polymarket_sports()
            poly_index, spread_index = build_polymarket_index(poly_events)
            poly_matched = 0
            print(f"    {len(poly_events)} Polymarket events, {len(poly_index)} game keys, {len(spread_index)} spread lines")

            if not sports_markets:
                print("  No sports markets found.")
                time.sleep(REFRESH_INTERVAL)
                continue

            # Build UCL team→opponent map from game winner titles (for spread disambiguation)
            ucl_opponents = {}
            for m_obj, s_name in sports_markets:
                if s_name == "UCL - Match Winner":
                    mv = re.match(r"^(.+?)\s+vs\.?\s+(.+?)\s+Winner\??", m_obj.get("title", ""), re.I)
                    if mv:
                        t1, t2 = mv.group(1).strip(), mv.group(2).strip()
                        ucl_opponents[t1.lower()] = t2
                        ucl_opponents[t2.lower()] = t1

            # Build preliminary data for matching, then enrich with Polymarket
            markets_data = []
            for market_obj, sport_name in sports_markets:
                preliminary = {
                    "title": market_obj.get("title", ""),
                    "detail": (market_obj.get("yes_sub_title") or "").strip(),
                    "sport": sport_name,
                }
                raw_strike = market_obj.get("floor_strike")
                floor_strike = float(raw_strike) if raw_strike is not None else None
                poly_match = match_polymarket(preliminary, poly_index, spread_index=spread_index, floor_strike=floor_strike, ucl_opponents=ucl_opponents)
                if poly_match:
                    poly_matched += 1
                md = extract_market_data(market_obj, sport_name, poly_match)
                markets_data.append(md)

            markets_data.sort(key=lambda x: x["implied_prob"], reverse=True)
            print(f"    Matched {poly_matched} Kalshi markets to Polymarket")

            # Fingerprint to skip identical writes
            fingerprint_src = "".join(
                f"{m['ticker']}{m['yes_ask']}{m['poly_yes']}{m['volume']}"
                for m in markets_data
            )
            fingerprint = hashlib.md5(fingerprint_src.encode()).hexdigest()

            if fingerprint == last_fingerprint:
                print(f"  No changes detected — skipping write ({len(markets_data)} markets)")
            else:
                html = generate_html(markets_data, timestamp, prev_prices)
                prev_prices = {
                    m["ticker"]: {
                        "yes_ask": m["yes_ask"],
                        "no_ask": m["no_ask"],
                        "poly_yes": m["poly_yes"],
                        "poly_no": m["poly_no"],
                    }
                    for m in markets_data
                }
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html)
                refresh_count += 1
                last_fingerprint = fingerprint
                print(f"  Updated dashboard.html ({len(markets_data)} markets, refresh #{refresh_count})")
                if refresh_count == 1:
                    print("\nSample markets:")
                    for m in markets_data[:5]:
                        poly_str = f"Poly=${m['poly_yes']:.2f}" if m["poly_yes"] is not None else "Poly=N/A"
                        arb_str = f"arb={m['arb_spread_cents']:.1f}¢" if m["arb_spread_cents"] is not None else ""
                        print(f"  [{m['ticker']}] {m['title'][:50]} — {m['implied_prob']:.1f}% {poly_str} {arb_str}")
                    print()

            time.sleep(REFRESH_INTERVAL)

    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
