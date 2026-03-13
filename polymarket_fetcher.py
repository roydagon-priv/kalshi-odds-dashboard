"""Polymarket Gamma API fetcher."""

import sys

import requests

POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com/events"


def fetch_polymarket_sports():
    """Fetch active sports events from Polymarket Gamma API."""
    all_events = []
    offset = 0
    limit = 100
    while True:
        try:
            resp = requests.get(
                POLYMARKET_GAMMA_URL,
                params={
                    "tag_id": 100639,
                    "active": "true",
                    "closed": "false",
                    "limit": limit,
                    "offset": offset,
                },
                timeout=15,
            )
            resp.raise_for_status()
            events = resp.json()
        except Exception as e:
            print(f"  Polymarket fetch error (offset={offset}): {e}", file=sys.stderr)
            break
        if not events:
            break
        all_events.extend(events)
        if len(events) < limit:
            break
        offset += limit
    return all_events
