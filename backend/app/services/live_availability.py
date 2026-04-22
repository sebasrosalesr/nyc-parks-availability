"""
Field availability builder.

Data sources
------------
Field catalog  : NYC Parks Mapbox vector tiles.
Availability   : NYC Parks Bulk Park Season CSV endpoints. 
                 By fetching a single CSV for a field, we grab the literal entire 
                 permit season. This avoids 600+ JSON api calls and perfectly 
                 bypasses Cloudflare limits.
"""
import asyncio
import csv
import logging
from dataclasses import dataclass
from datetime import date, datetime, time as dt_time, timedelta
from io import StringIO
from typing import Optional

from curl_cffi.requests import AsyncSession, Response, RequestsError
from cachetools import TTLCache

from app.config import settings
from app.models import (
    AvailabilityQuery,
    AvailabilityResponse,
    DayAvailability,
    FieldCatalogItem,
    FieldSchedule,
    TimeBlock,
)
from app.services.field_catalog import filter_catalog_by_type, get_field_catalog

logger = logging.getLogger(__name__)

# Cache for CSVs: ttl 15 minutes, max 1000 parks
_csv_cache: TTLCache = TTLCache(maxsize=1000, ttl=900)
_csv_lock = asyncio.Lock()

@dataclass(frozen=True)
class BookedInterval:
    start: datetime
    end: datetime

# ── Public entry point ────────────────────────────────────────────────────────

async def build_availability_response(
    client: AsyncSession,
    field_type: str,
    start_date: date,
    end_date: date,
    prop_ids: Optional[list[str]] = None,
) -> AvailabilityResponse:
    catalog = await get_field_catalog(client)
    matched_fields = filter_catalog_by_type(catalog, field_type)
    if prop_ids:
        allowed = {p.strip() for p in prop_ids if p.strip()}
        matched_fields = [f for f in matched_fields if f.prop_id in allowed]
    else:
        allowed = sorted({f.prop_id for f in matched_fields})

    if not matched_fields:
        return _empty_response(field_type, start_date, end_date, list(allowed))

    # Identify all target parks
    target_prop_ids = {f.prop_id for f in matched_fields}
    live_count = 0
    cached_count = 0

    booked_intervals_by_field: dict[str, list[BookedInterval]] = {}
    
    # Concurrently fetch CSVs with polite limits
    semaphore = asyncio.Semaphore(10)
    
    async def process_park_csv(prop_id: str):
        nonlocal live_count, cached_count
        raw_csv, from_cache = await _fetch_park_csv(client, prop_id, semaphore)
        if from_cache:
            cached_count += 1
        else:
            live_count += 1
            
        if raw_csv:
            park_intervals = _parse_booked_intervals(raw_csv)
            for fid, intervals in park_intervals.items():
                if fid not in booked_intervals_by_field:
                    booked_intervals_by_field[fid] = []
                booked_intervals_by_field[fid].extend(intervals)

    await asyncio.gather(*(process_park_csv(pid) for pid in target_prop_ids))

    days_in_range: list[date] = []
    curr = start_date
    while curr <= end_date:
        days_in_range.append(curr)
        curr += timedelta(days=1)

    slot_minutes = settings.slot_minutes
    slot_delta = timedelta(minutes=slot_minutes)
    schedules: list[FieldSchedule] = []

    for field in matched_fields:
        total_available_minutes = 0
        day_summaries: list[DayAvailability] = []
        opening_time = _parse_twelve_hour_time(field.opening_time)
        
        # When parsing CSVs, dusk is inherently handled just by when the field permits operate.
        # We will bound searches to the configured field_close_hour
        close_time = _parse_close_time(f"{settings.field_close_hour:02d}:00") 

        field_intervals = booked_intervals_by_field.get(field.field_name, [])

        for day in days_in_range:
            open_dt = datetime.combine(day, opening_time)
            close_dt = datetime.combine(day, close_time)

            open_blocks: list[TimeBlock] = []
            block_start: Optional[datetime] = None
            block_end: Optional[datetime] = None
            open_minutes = 0
            potential_minutes = 0

            current_slot = open_dt
            while current_slot < close_dt:
                effective_end = min(current_slot + slot_delta, close_dt)
                duration = int((effective_end - current_slot).total_seconds() // 60)
                potential_minutes += duration
                
                # Check overlapping intervals
                is_open = True
                for booked in field_intervals:
                    # Overlap math: max(start1, start2) < min(end1, end2)
                    if booked.start < effective_end and booked.end > current_slot:
                        is_open = False
                        break
                
                if is_open:
                    open_minutes += duration
                    if block_start is None:
                        block_start, block_end = current_slot, effective_end
                    elif block_end == current_slot:
                        block_end = effective_end
                    else:
                        open_blocks.append(TimeBlock(start=block_start, end=block_end))
                        block_start, block_end = current_slot, effective_end
                elif block_start is not None:
                    open_blocks.append(TimeBlock(start=block_start, end=block_end))
                    block_start = block_end = None

                current_slot += slot_delta

            if block_start is not None and block_end is not None:
                open_blocks.append(TimeBlock(start=block_start, end=block_end))

            total_available_minutes += open_minutes
            day_summaries.append(DayAvailability(
                date=day,
                open_blocks=open_blocks,
                open_minutes=open_minutes,
                potential_minutes=potential_minutes,
            ))

        schedules.append(FieldSchedule(
            field_id=field.field_id,
            field_name=field.field_name,
            park_name=field.park_name,
            prop_id=field.prop_id,
            borough=field.borough,
            surface_type=field.surface_type,
            total_available_minutes=total_available_minutes,
            days=day_summaries,
        ))

    schedules.sort(key=lambda f: (-f.total_available_minutes, f.borough, f.park_name, f.field_name))

    return AvailabilityResponse(
        fields=schedules,
        fetched_at=datetime.utcnow(),
        query=AvailabilityQuery(
            field_type=field_type,
            start_date=start_date,
            end_date=end_date,
            prop_ids=list(target_prop_ids),
            matching_field_count=len(matched_fields),
            matching_park_count=len(target_prop_ids),
            snapshot_count=len(target_prop_ids),
            live_snapshot_count=live_count,
            cached_snapshot_count=cached_count,
        ),
    )


# ── CSV Loading and Parsing ──────────────────────────────────────────────────────────

async def _fetch_park_csv(client: AsyncSession, prop_id: str, semaphore: asyncio.Semaphore) -> tuple[Optional[str], bool]:
    cache_key = prop_id
    async with _csv_lock:
        if cache_key in _csv_cache:
            return _csv_cache[cache_key], True

    url = f"https://www.nycgovparks.org/permits/field-and-court/issued/{prop_id}/csv"
    
    async with semaphore:
        for attempt in range(settings.max_retries):
            try:
                resp = await client.get(url, headers={"Accept": "*/*"}, timeout=settings.request_timeout_s)
                if resp.status_code == 404:
                    return None, False
                if resp.status_code == 429:
                    wait = 0.5 * (2 ** attempt)
                    logger.warning("Rate limited CSV %s; retrying in %.1fs", prop_id, wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                
                # Check for Cloudflare challenge visually or via header
                if resp.status_code == 202 and resp.headers.get("x-amzn-waf-action") == "challenge":
                    logger.warning("WAF challenge on CSV %s", prop_id)
                    break
                
                csv_text = resp.text
                async with _csv_lock:
                    _csv_cache[cache_key] = csv_text
                return csv_text, False

            except RequestsError as exc:
                wait = 0.5 * (2 ** attempt)
                logger.warning("Request error %s on CSV %s; retrying in %.1fs", exc, prop_id, wait)
                await asyncio.sleep(wait)

        return None, False


def _parse_booked_intervals(csv_text: str) -> dict[str, list[BookedInterval]]:
    intervals: dict[str, list[BookedInterval]] = {}
    if not csv_text or not csv_text.strip():
        return intervals

    reader = csv.DictReader(StringIO(csv_text))
    if not reader.fieldnames:
        return intervals
        
    for row in reader:
        field_name = str(row.get("Field", "")).strip()
        start_str = str(row.get("Start", "")).strip()
        end_str = str(row.get("End", "")).strip()
        
        if not field_name or not start_str or not end_str:
            continue
            
        try:
            # "3/17/2026 6:30 p.m." -> "3/17/2026 6:30 PM"
            start_clean = start_str.replace("p.m.", "PM").replace("a.m.", "AM").replace(".", "")
            end_clean = end_str.replace("p.m.", "PM").replace("a.m.", "AM").replace(".", "")
            
            start_dt = datetime.strptime(start_clean, "%m/%d/%Y %I:%M %p")
            end_dt = datetime.strptime(end_clean, "%m/%d/%Y %I:%M %p")
            
            if field_name not in intervals:
                intervals[field_name] = []
            intervals[field_name].append(BookedInterval(start=start_dt, end=end_dt))
        except ValueError as e:
            logger.debug("Failed to parse CSV string '%s' or '%s': %s", start_str, end_str, e)
            
    return intervals


def _empty_response(field_type: str, start_date: date, end_date: date,
                    prop_ids: list[str]) -> AvailabilityResponse:
    return AvailabilityResponse(
        fields=[],
        fetched_at=datetime.utcnow(),
        query=AvailabilityQuery(
            field_type=field_type,
            start_date=start_date,
            end_date=end_date,
            prop_ids=prop_ids,
            matching_field_count=0,
            matching_park_count=0,
            snapshot_count=0,
            live_snapshot_count=0,
            cached_snapshot_count=0,
        ),
    )


def _parse_twelve_hour_time(value: str) -> dt_time:
    return datetime.strptime(value, "%I:%M %p").time()


def _parse_close_time(value: str) -> dt_time:
    return datetime.strptime(value, "%H:%M").time()
