"""
Polymarket Data Fetcher
=======================
Fetches market data from Polymarket public APIs (no auth required):
  - Gamma API  : events, tags, series, markets
  - CLOB API   : orderbook, prices, price history
  - Data API   : trades, positions, leaderboard

Notes:
  - Public Gamma ``/search`` currently returns 401, so search mode uses local
    fuzzy matching over active events/markets as a fallback.
  - Public CLOB ``/prices-history`` requires ``interval`` or
    ``startTs``+``endTs``.

Usage::

    from polymarket_autopilot.fetcher import fetch_events, search

    events = fetch_events(limit=10)
    results = search("US election")
"""

import difflib
import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ────────────────────────────── Base URLs ──────────────────────────────

GAMMA_BASE = "https://gamma-api.polymarket.com"
CLOB_BASE = "https://clob.polymarket.com"
DATA_BASE = "https://data-api.polymarket.com"


# ─────────────────────────── HTTP helper ───────────────────────────────

def _get(url: str, params: dict | None = None, retries: int = 3) -> Any:
    """GET with simple retry logic (stdlib-only, no *requests*)."""
    if params:
        sep = "&" if "?" in url else "?"
        url = url + sep + urllib.parse.urlencode(params)

    for attempt in range(retries):
        req = urllib.request.Request(url, headers={
            "User-Agent": "polymarket-fetcher/1.0",
            "Accept-Encoding": "gzip, deflate",
        })
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            if exc.code == 429:
                wait = 2 ** attempt
                time.sleep(wait)
                if attempt == retries - 1:
                    raise
            else:
                raise
        except (urllib.error.URLError, OSError):
            if attempt == retries - 1:
                raise
            time.sleep(1)
    return None


def _paginate(
    url: str,
    params: dict | None = None,
    page_size: int = 100,
    max_results: int | None = None,
) -> list:
    """
    Auto-paginate a list endpoint (offset-based).

    Args:
        page_size  : items per API request (controls HTTP payload size).
        max_results: total cap on returned items. ``None`` = fetch all pages.
                     When set, stops as soon as we have enough items.
    """
    params = dict(params or {})
    params["limit"] = page_size
    params["offset"] = 0
    results: list = []
    while True:
        batch = _get(url, params)
        if not batch:
            break
        results.extend(batch)
        if max_results is not None and len(results) >= max_results:
            return results[:max_results]
        if len(batch) < page_size:
            break
        params["offset"] += page_size
        time.sleep(0.1)
    return results


# ═══════════════════════════════════════════════════════════════════════
#  GAMMA API — Events
# ═══════════════════════════════════════════════════════════════════════

def fetch_events(
    active: bool | None = True,
    closed: bool | None = False,
    featured: bool | None = None,
    tag_slug: str | None = None,
    tag_id: int | None = None,
    liquidity_min: float | None = None,
    volume_min: float | None = None,
    start_date_min: str | None = None,
    end_date_max: str | None = None,
    order: str | None = "volume24hr",
    ascending: bool = False,
    limit: int = 100,
) -> list:
    """Fetch events from Gamma API."""
    params: dict = {}
    if active is not None:
        params["active"] = str(active).lower()
    if closed is not None:
        params["closed"] = str(closed).lower()
    if featured is not None:
        params["featured"] = str(featured).lower()
    if tag_slug:
        params["tag_slug"] = tag_slug
    if tag_id is not None:
        params["tag_id"] = tag_id
    if liquidity_min is not None:
        params["liquidity_min"] = liquidity_min
    if volume_min is not None:
        params["volume_min"] = volume_min
    if start_date_min:
        params["start_date_min"] = start_date_min
    if end_date_max:
        params["end_date_max"] = end_date_max
    if order:
        params["order"] = order
        params["ascending"] = str(ascending).lower()
    return _paginate(f"{GAMMA_BASE}/events", params, max_results=limit)


def fetch_event_by_id(event_id: str | int) -> dict:
    return _get(f"{GAMMA_BASE}/events/{event_id}")


def fetch_event_by_slug(slug: str) -> dict:
    return _get(f"{GAMMA_BASE}/events/{slug}")


def fetch_event_tags(event_id: str | int) -> list:
    return _get(f"{GAMMA_BASE}/events/{event_id}/tags")


# ═══════════════════════════════════════════════════════════════════════
#  GAMMA API — Tags
# ═══════════════════════════════════════════════════════════════════════

def fetch_tags(
    is_carousel: bool | None = None,
    include_template: bool | None = None,
) -> list:
    """Fetch all tags (categories)."""
    params: dict = {}
    if is_carousel is not None:
        params["is_carousel"] = str(is_carousel).lower()
    if include_template is not None:
        params["include_template"] = str(include_template).lower()
    return _paginate(f"{GAMMA_BASE}/tags", params)


def fetch_tag_by_id(tag_id: str | int) -> dict:
    return _get(f"{GAMMA_BASE}/tags/{tag_id}")


def fetch_tag_by_slug(slug: str) -> dict:
    return _get(f"{GAMMA_BASE}/tags/slug/{slug}")


def fetch_related_tags_by_id(tag_id: str | int) -> list:
    return _get(f"{GAMMA_BASE}/tags/{tag_id}/related")


# ═══════════════════════════════════════════════════════════════════════
#  GAMMA API — Series
# ═══════════════════════════════════════════════════════════════════════

def fetch_series(
    closed: bool | None = None,
    recurrence: str | None = None,
    exclude_events: bool | None = None,
    categories_labels: list[str] | None = None,
) -> list:
    """Fetch all series (recurring/grouped event sets)."""
    params: dict = {}
    if closed is not None:
        params["closed"] = str(closed).lower()
    if recurrence:
        params["recurrence"] = recurrence
    if exclude_events is not None:
        params["exclude_events"] = str(exclude_events).lower()
    if categories_labels:
        params["categories_labels"] = ",".join(categories_labels)
    return _paginate(f"{GAMMA_BASE}/series", params)


def fetch_series_by_id(series_id: str | int) -> dict:
    return _get(f"{GAMMA_BASE}/series/{series_id}")


# ═══════════════════════════════════════════════════════════════════════
#  GAMMA API — Markets
# ═══════════════════════════════════════════════════════════════════════

def fetch_markets(
    active: bool | None = True,
    closed: bool | None = False,
    archived: bool | None = None,
    liquidity_min: float | None = None,
    volume_min: float | None = None,
    tag_id: int | None = None,
    order: str | None = "volume24hr",
    ascending: bool = False,
    limit: int = 100,
) -> list:
    """Fetch individual markets (sub-questions within an event)."""
    params: dict = {}
    if active is not None:
        params["active"] = str(active).lower()
    if closed is not None:
        params["closed"] = str(closed).lower()
    if archived is not None:
        params["archived"] = str(archived).lower()
    if liquidity_min is not None:
        params["liquidity_min"] = liquidity_min
    if volume_min is not None:
        params["volume_min"] = volume_min
    if tag_id is not None:
        params["tag_id"] = tag_id
    if order:
        params["order"] = order
        params["ascending"] = str(ascending).lower()
    return _paginate(f"{GAMMA_BASE}/markets", params, max_results=limit)


def fetch_market_by_id(market_id: str) -> dict:
    return _get(f"{GAMMA_BASE}/markets/{market_id}")


def fetch_market_by_slug(slug: str) -> dict:
    return _get(f"{GAMMA_BASE}/markets/{slug}")


def fetch_simplified_markets(limit: int | None = None) -> list:
    """Lightweight market list — fewer fields, faster response."""
    return _paginate(f"{GAMMA_BASE}/markets/simplified", max_results=limit)


# ═══════════════════════════════════════════════════════════════════════
#  GAMMA API — Search
# ═══════════════════════════════════════════════════════════════════════

def search(query: str, limit: int = 10) -> dict:
    """
    Search across events and markets.

    Returns:
        dict with keys: ``markets``, ``events``, ``profiles``
    """
    query = query.strip()
    if not query:
        return {"events": [], "markets": [], "profiles": []}

    events = fetch_events(active=True, closed=False, limit=200)
    markets = fetch_markets(active=True, closed=False, limit=200)
    q = query.lower()

    def _score(item: dict, fields: list[str]) -> float:
        texts: list[str] = []
        for field in fields:
            value = item.get(field)
            if value:
                texts.append(str(value))
        haystack = " | ".join(texts).lower()
        if not haystack:
            return 0.0
        if q in haystack:
            return 2.0 + (len(q) / max(len(haystack), 1))
        return difflib.SequenceMatcher(None, q, haystack).ratio()

    ranked_events = sorted(
        ((_score(ev, ["title", "slug", "description", "ticker"]), ev) for ev in events),
        key=lambda x: x[0],
        reverse=True,
    )
    ranked_markets = sorted(
        ((_score(m, ["question", "slug", "description", "groupItemTitle"]), m) for m in markets),
        key=lambda x: x[0],
        reverse=True,
    )

    min_score = 0.25
    return {
        "events": [item for score, item in ranked_events if score >= min_score][:limit],
        "markets": [item for score, item in ranked_markets if score >= min_score][:limit],
        "profiles": [],
    }


# ═══════════════════════════════════════════════════════════════════════
#  CLOB API — Prices & Order Book
# ═══════════════════════════════════════════════════════════════════════

def _parse_clob_token_ids(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except json.JSONDecodeError:
            return [value]
    return []


def resolve_market_token_id(market: str, outcome_index: int = 0) -> str:
    """
    Resolve a user-facing market identifier into the CLOB asset id.

    Accepted inputs: direct CLOB token id, Gamma market slug,
    Gamma conditionId, Gamma market id.
    """
    market = str(market).strip()
    if market.isdigit() and len(market) > 20:
        return market

    candidates: list[dict] = []
    for fetcher in (fetch_market_by_slug, fetch_market_by_id):
        try:
            data = fetcher(market)
            if isinstance(data, dict) and data.get("id"):
                candidates.append(data)
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            pass

    if not candidates:
        try:
            markets = fetch_markets(active=None, closed=None, limit=500)
            for item in markets:
                if market in {str(item.get("id", "")), str(item.get("slug", "")), str(item.get("conditionId", ""))}:
                    candidates.append(item)
                    break
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            pass

    if not candidates:
        return market

    token_ids = _parse_clob_token_ids(candidates[0].get("clobTokenIds"))
    if not token_ids:
        return market
    if outcome_index < 0 or outcome_index >= len(token_ids):
        raise IndexError(f"outcome_index {outcome_index} out of range for market {market}")
    return token_ids[outcome_index]


def fetch_price_history(
    market: str,
    interval: str = "1h",
    start_ts: int | None = None,
    end_ts: int | None = None,
    outcome_index: int = 0,
) -> list:
    """Fetch price history for a market."""
    asset_id = resolve_market_token_id(market, outcome_index=outcome_index)
    params: dict = {"market": asset_id}
    if start_ts is not None and end_ts is not None:
        params["startTs"] = start_ts
        params["endTs"] = end_ts
    else:
        params["interval"] = interval
    data = _get(f"{CLOB_BASE}/prices-history", params)
    return data.get("history", []) if isinstance(data, dict) else data


def fetch_orderbook(token_id: str) -> dict:
    """Fetch the order book for a given outcome token ID."""
    return _get(f"{CLOB_BASE}/book", {"token_id": token_id})


def fetch_midpoint(token_id: str) -> dict:
    """Fetch midpoint price for an outcome token."""
    return _get(f"{CLOB_BASE}/midpoint", {"token_id": token_id})


def fetch_spread(token_id: str) -> dict:
    """Fetch bid-ask spread for an outcome token."""
    return _get(f"{CLOB_BASE}/spread", {"token_id": token_id})


# ═══════════════════════════════════════════════════════════════════════
#  DATA API — Trades & Positions
# ═══════════════════════════════════════════════════════════════════════

def fetch_trades(
    maker_address: str | None = None,
    taker_address: str | None = None,
    market_id: str | None = None,
    limit: int | None = 500,
) -> list:
    """Fetch trades (public — no auth required for historical data)."""
    params: dict = {}
    if maker_address:
        params["maker_address"] = maker_address
    if taker_address:
        params["taker_address"] = taker_address
    if market_id:
        params["market"] = market_id
    return _paginate(f"{DATA_BASE}/trades", params, max_results=limit)


def fetch_leaderboard(limit: int = 50) -> list:
    """Fetch top trader leaderboard."""
    return _get(f"{DATA_BASE}/leaderboard", {"limit": limit}) or []


def fetch_open_interest(market_id: str) -> dict:
    """Fetch open interest stats for a market."""
    return _get(f"{DATA_BASE}/open-interest", {"conditionId": market_id})


# ═══════════════════════════════════════════════════════════════════════
#  Convenience — bulk snapshot
# ═══════════════════════════════════════════════════════════════════════

def fetch_all_snapshot(
    events_active: bool = True,
    events_limit: int = 100,
    markets_active: bool = True,
    markets_limit: int = 100,
    output_dir: str | Path = ".",
) -> dict:
    """
    Fetch a full snapshot and save each category as a JSON file.

    Returns:
        dict with keys: events, tags, series, markets (lists)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    def _save(name: str, data: list | dict) -> None:
        path = output_dir / f"polymarket_{name}_{ts}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        count = len(data) if isinstance(data, list) else 1
        print(f"  ✓ {name}: {count} records → {path}")

    print("▶ Fetching tags …")
    tags = fetch_tags()
    _save("tags", tags)

    print("▶ Fetching series …")
    series = fetch_series(exclude_events=True)
    _save("series", series)

    print("▶ Fetching events …")
    events = fetch_events(active=events_active, limit=events_limit)
    _save("events", events)

    print("▶ Fetching markets …")
    markets = fetch_markets(active=markets_active, limit=markets_limit)
    _save("markets", markets)

    snapshot = {"events": events, "tags": tags, "series": series, "markets": markets}
    _save("snapshot", snapshot)
    return snapshot
