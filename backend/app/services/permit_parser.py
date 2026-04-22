"""
CSV → Permit objects → daily availability slots.

Column mapping is intentionally fuzzy: NYC Parks CSV headers vary slightly
between dataset versions, so we try multiple known aliases for each field.
"""
import csv
import io
import logging
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from dateutil import parser as dateparser

from app.config import settings
from app.models import BOROUGH_MAP, FieldAvailability, Permit, TimeSlot

logger = logging.getLogger(__name__)

# Ordered alias lists — first match wins (all lowercase, spaces stripped)
_COL_ALIASES: Dict[str, List[str]] = {
    "id":         ["eventid", "permitid", "permit_id", "id"],
    "start_date": ["startdate", "start_date", "permitstartdate", "startdt"],
    "start_time": ["starttime", "start_time", "permitstarttime"],
    "end_date":   ["enddate", "end_date", "permitenddate", "enddt"],
    "end_time":   ["endtime", "end_time", "permitendtime"],
    "activity":   ["subcategoryname", "subcategory", "activity", "sport", "categoryname", "type"],
    "park":       ["parkname", "park_name", "facilityname", "location", "eventname"],
    "prop_id":    ["propertyid", "prop_id", "propid"],
}


def _col_map(headers: List[str]) -> Dict[str, Optional[str]]:
    """Return {logical_name: actual_header} for each alias group."""
    normalized = {h.lower().replace(" ", "").replace("_", ""): h for h in headers}
    result: Dict[str, Optional[str]] = {}
    for logical, aliases in _COL_ALIASES.items():
        for alias in aliases:
            key = alias.replace("_", "").replace(" ", "")
            if key in normalized:
                result[logical] = normalized[key]
                break
        else:
            result[logical] = None
    return result


def _parse_dt(date_val: str, time_val: str = "") -> Optional[datetime]:
    raw = f"{date_val} {time_val}".strip()
    if not raw:
        return None
    try:
        return dateparser.parse(raw, fuzzy=True)
    except Exception:
        logger.debug("Could not parse datetime: %r", raw)
        return None


def parse_permits(csv_text: str, prop_id: str, activity: str) -> List[Permit]:
    permits: List[Permit] = []
    reader = csv.DictReader(io.StringIO(csv_text))

    if reader.fieldnames is None:
        return permits

    col = _col_map(list(reader.fieldnames))

    for row in reader:
        try:
            start_dt = _parse_dt(
                row.get(col["start_date"] or "", ""),
                row.get(col["start_time"] or "", "") if col["start_time"] else "",
            )
            end_dt = _parse_dt(
                row.get(col["end_date"] or "", row.get(col["start_date"] or "", "")),
                row.get(col["end_time"] or "", "") if col["end_time"] else "",
            )

            if not start_dt:
                continue
            if not end_dt or end_dt <= start_dt:
                end_dt = start_dt + timedelta(hours=settings.slot_duration_hours)

            row_activity = (
                row.get(col["activity"] or "", activity).lower().strip()
                if col["activity"]
                else activity.lower()
            )
            row_park = (
                row.get(col["park"] or "", prop_id)
                if col["park"]
                else prop_id
            )
            row_prop = (
                row.get(col["prop_id"] or "", prop_id)
                if col["prop_id"]
                else prop_id
            )
            row_id = (
                row.get(col["id"] or "", "unknown")
                if col["id"]
                else "unknown"
            )

            permits.append(
                Permit(
                    permit_id=row_id,
                    park_name=row_park,
                    prop_id=row_prop,
                    activity=row_activity,
                    start_dt=start_dt,
                    end_dt=end_dt,
                )
            )
        except Exception as exc:
            logger.debug("Skipping malformed row: %s", exc)

    logger.info("Parsed %d permits for prop_id=%s", len(permits), prop_id)
    return permits


def _build_slots(day: date) -> List[TimeSlot]:
    slots: List[TimeSlot] = []
    dt = datetime(day.year, day.month, day.day, settings.field_open_hour)
    close = datetime(day.year, day.month, day.day, settings.field_close_hour)
    step = timedelta(hours=settings.slot_duration_hours)
    while dt + step <= close:
        slots.append(TimeSlot(start=dt, end=dt + step, is_available=True))
        dt += step
    return slots


def compute_availability(
    permits: List[Permit],
    prop_id: str,
    activity: str,
    start_date: date,
    end_date: date,
    park_name: Optional[str] = None,
) -> List[FieldAvailability]:
    park_label = park_name or (permits[0].park_name if permits else prop_id)
    borough_code = prop_id[0].upper() if prop_id else "?"
    borough = BOROUGH_MAP.get(borough_code, borough_code)

    results: List[FieldAvailability] = []
    day = start_date

    while day <= end_date:
        slots = _build_slots(day)

        for permit in permits:
            if permit.start_dt.date() > day or permit.end_dt.date() < day:
                continue
            for slot in slots:
                if permit.start_dt < slot.end and permit.end_dt > slot.start:
                    slot.is_available = False
                    slot.permit_id = permit.permit_id

        available = sum(1 for s in slots if s.is_available)
        results.append(
            FieldAvailability(
                park_name=park_label,
                prop_id=prop_id,
                borough=borough,
                activity=activity,
                date=day,
                slots=slots,
                total_slots=len(slots),
                available_slots=available,
            )
        )
        day += timedelta(days=1)

    return results
