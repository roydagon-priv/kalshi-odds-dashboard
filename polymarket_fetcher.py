"""Polymarket Gamma API fetcher."""

import sys

import requests

POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com/events"

# Tag IDs for sports leagues we care about
SPORT_TAGS = {
    "nba": [745],
    "ucl": [100977, 1234],
    "mlb": [100381],
    "nfl": [450],
    "f1": [102070],
    "nhl": [899],
}


def fetch_polymarket_sports():
    """Fetch active sports events from Polymarket Gamma API."""
    seen_ids = set()
    all_events = []
    tag_ids = [tid for tags in SPORT_TAGS.values() for tid in tags]
    for tag_id in tag_ids:
        offset = 0
        limit = 100
        while True:
            try:
                resp = requests.get(
                    POLYMARKET_GAMMA_URL,
                    params={
                        "tag_id": tag_id,
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
                print(f"  Polymarket fetch error (tag_id={tag_id}, offset={offset}): {e}", file=sys.stderr)
                break
            if not events:
                break
            for event in events:
                eid = event.get("id")
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    all_events.append(event)
            if len(events) < limit:
                break
            offset += limit
    return all_events
