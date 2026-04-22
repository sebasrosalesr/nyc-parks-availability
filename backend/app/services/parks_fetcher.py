"""
Permit data fetcher with three tiers:

  1. Mock (USE_MOCK_DATA=true, default)
     Generates realistic synthetic data — use for demos and development.
     NYC Parks does not expose a public permit API; the map at
     https://www.nycgovparks.org/permits/field-and-court/map is behind
     Cloudflare and returns 403 to non-browser clients.

  2. NYC Parks direct (future)
     Once the live XHR endpoint is confirmed (inspect Network tab on the map
     page in a browser), set USE_MOCK_DATA=false and update _fetch_nyc_parks_direct.

  3. NYC Open Data fallback (future)
     Requires confirming the correct permit dataset ID on
     https://data.cityofnewyork.us — the parks permit data has not been
     found as a public Socrata dataset yet.

Caching:       in-memory TTLCache keyed by (prop_id, activity, start, end)
Rate limiting: enforces a minimum gap between outbound HTTP requests
Retries:       exponential back-off on 429 / transient errors
"""
import asyncio
import logging
import time
from datetime import date
from typing import Optional, Tuple

import httpx
from cachetools import TTLCache

from app.config import settings
from app.services.mock_data import generate_mock_csv

logger = logging.getLogger(__name__)

_cache: TTLCache = TTLCache(maxsize=settings.cache_maxsize, ttl=settings.cache_ttl_s)
_cache_lock = asyncio.Lock()

_last_request_at: float = 0.0
_rate_lock = asyncio.Lock()


async def _polite_get(client: httpx.AsyncClient, url: str, params: dict) -> httpx.Response:
    global _last_request_at

    for attempt in range(settings.max_retries):
        async with _rate_lock:
            gap = time.monotonic() - _last_request_at
            if gap < settings.request_delay_s:
                await asyncio.sleep(settings.request_delay_s - gap)
            _last_request_at = time.monotonic()

        try:
            resp = await client.get(url, params=params, timeout=settings.request_timeout_s)
            resp.raise_for_status()
            return resp

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                wait = 5 * (2 ** attempt)
                logger.warning("429 rate-limited; backing off %ds (attempt %d)", wait, attempt + 1)
                await asyncio.sleep(wait)
            else:
                raise

        except httpx.RequestError as exc:
            wait = 2 * (2 ** attempt)
            logger.warning("Request error %s; retry in %ds (attempt %d)", exc, wait, attempt + 1)
            await asyncio.sleep(wait)

    raise RuntimeError(f"Exhausted {settings.max_retries} retries for {url}")


async def _fetch_nyc_parks_direct(
    client: httpx.AsyncClient,
    prop_id: str,
    activity: Optional[str],
    start_date: date,
    end_date: date,
) -> str:
    """
    Placeholder for the live NYC Parks endpoint.

    To activate: open https://www.nycgovparks.org/permits/field-and-court/map
    in a browser → DevTools → Network → reload → find the XHR/Fetch call
    that returns permit data → copy the URL and params here.
    """
    url = f"{settings.nyc_parks_base}/permits/field-and-court/search"
    params: dict = {
        "prop_id": prop_id,
        "start_date": start_date.strftime("%m/%d/%Y"),
        "end_date": end_date.strftime("%m/%d/%Y"),
        "format": "csv",
    }
    if activity:
        params["activity"] = activity

    resp = await _polite_get(client, url, params)
    text = resp.text
    if "<html" in text[:200].lower() or "," not in text[:500]:
        raise ValueError("Response is HTML, not CSV")
    return text


async def fetch_permits_csv(
    client: httpx.AsyncClient,
    prop_id: str,
    activity: Optional[str],
    start_date: date,
    end_date: date,
) -> Tuple[str, bool]:
    """Return (csv_text, from_cache)."""
    cache_key = (prop_id, activity or "", str(start_date), str(end_date))

    async with _cache_lock:
        if cache_key in _cache:
            logger.debug("Cache HIT  %s", cache_key)
            return _cache[cache_key], True

    if settings.use_mock_data:
        logger.info("Mock data  prop_id=%-6s  %s → %s  activity=%s",
                    prop_id, start_date, end_date, activity)
        csv_text = generate_mock_csv(prop_id, activity, start_date, end_date)
    else:
        logger.info("Live fetch  prop_id=%-6s  %s → %s  activity=%s",
                    prop_id, start_date, end_date, activity)
        try:
            csv_text = await _fetch_nyc_parks_direct(client, prop_id, activity, start_date, end_date)
            logger.info("Source: NYC Parks direct  prop_id=%s", prop_id)
        except Exception as exc:
            logger.error(
                "Live fetch failed for %s: %s — set USE_MOCK_DATA=true for demo mode", prop_id, exc
            )
            raise

    async with _cache_lock:
        _cache[cache_key] = csv_text

    return csv_text, False
