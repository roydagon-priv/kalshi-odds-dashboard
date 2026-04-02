"""Polymarket Gamma API fetcher."""

import sys

import requests

POLYMARKET_GAMMA_URL = "https://gamma-api.polymarket.com/events"

# Tag IDs for sports leagues we care about
TAG_IDS = [745, 100977, 1234, 100381, 450, 102070, 899]  # NBA, UCL, UCL-alt, MLB, NFL, F1, NHL


def fetch_polymarket_sports():
    """Fetch active sports events from Polymarket Gamma API."""
    seen_ids = set()
    all_events = []
    for tag_id in TAG_IDS:
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
