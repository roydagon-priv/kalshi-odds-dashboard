"""Kalshi API fetcher — direct REST calls with RSA signing (no SDK)."""

import base64
import sys
import time
from datetime import datetime, timezone

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2"

# Series tickers for game-level markets only (no futures/awards)
TARGET_SERIES = {
    "NBA - Game Winner":     "KXNBAGAME",
    "NBA - Total Points":    "KXNBATOTAL",
    "NBA - Spread":          "KXNBASPREAD",
    "NHL - Game Winner":     "KXNHLGAME",
    "NHL - Total Points":    "KXNHLTOTAL",
    "NHL - Spread":          "KXNHLSPREAD",
    "F1 - Race Winner":      "KXF1RACE",
    "F1 - Pole Position":    "KXF1POLE",
    "F1 - Fastest Lap":      "KXF1FASTLAP",
    "F1 - Podium":           "KXF1RACEPODIUM",
    "F1 - Top 5":            "KXF1TOP5",
    "F1 - Top 10":           "KXF1TOP10",
    "MLB - Game Winner":     "KXMLBGAME",
    "MLB - Total Runs":      "KXMLBTOTAL",
    "MLB - Run Line":        "KXMLBSPREAD",
    "UCL - Match Winner":    "KXUCLGAME",
    "UCL - Total Goals":     "KXUCLTOTAL",
    "UCL - Spread":          "KXUCLSPREAD",
}


def _load_private_key(pem_text):
    return serialization.load_pem_private_key(pem_text.encode(), password=None)


def _sign_request(private_key, timestamp_ms, method, path):
    msg = f"{timestamp_ms}{method}{path}".encode()
    sig = private_key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(sig).decode()


def _auth_headers(api_key_id, private_key, method, path):
    ts = str(int(time.time() * 1000))
    sig = _sign_request(private_key, ts, method, path)
    return {
        "KALSHI-ACCESS-KEY": api_key_id,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": sig,
        "Content-Type": "application/json",
    }


def build_kalshi_client(api_key_id, private_key_pem):
    """Return a callable that makes authenticated GET requests."""
    private_key = _load_private_key(private_key_pem)

    def get(path, params=None):
        headers = _auth_headers(api_key_id, private_key, "GET", path)
        resp = requests.get(
            KALSHI_API_BASE + path,
            headers=headers,
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    return get


def fetch_series_markets(get, sport_name, series_ticker):
    markets = []
    cursor = None
    page = 0
    while True:
        page += 1
        params = {"limit": 200, "status": "open", "series_ticker": series_ticker}
        if cursor:
            params["cursor"] = cursor
        try:
            data = get("/markets", params=params)
        except Exception as e:
            print(f"Error fetching {sport_name} page {page}: {e}", file=sys.stderr)
            break
        batch = data.get("markets") or []
        markets.extend(batch)
        cursor = data.get("cursor")
        if not cursor:
            break
    return markets


def fetch_all_sports_markets(get):
    all_markets = []  # list of (market_dict, sport_name)
    for sport_name, series_ticker in TARGET_SERIES.items():
        print(f"  Fetching {sport_name} ({series_ticker})...")
        markets = fetch_series_markets(get, sport_name, series_ticker)
        print(f"    Found {len(markets)} markets")
        for m in markets:
            all_markets.append((m, sport_name))
    return all_markets
