"""
Realistic synthetic permit data for demo / development.

Seeded by (prop_id + date) so results are stable across requests.
Occupancy model:
  - Weekends are 65-85% booked (high demand)
  - Weekday afternoons (12-18h) are 35-55% booked
  - Weekday mornings / evenings are 15-30% booked
"""
import hashlib
import io
import random
from datetime import date, datetime, timedelta
from typing import Optional

from app.config import settings

PARK_NAMES: dict[str, str] = {
    "M010": "Central Park",
    "M036": "Riverside Park",
    "B073": "Prospect Park",
    "B038": "Marine Park",
    "Q099": "Flushing Meadows-Corona Park",
    "Q006": "Astoria Park",
    "X099": "Van Cortlandt Park",
    "X012": "Pelham Bay Park",
    "R001": "Clove Lakes Park",
}

# Approximate number of fields per sport per park
FIELD_COUNTS: dict[str, dict[str, int]] = {
    "M010": {"soccer": 3, "baseball": 2, "basketball": 4, "softball": 1},
    "M036": {"soccer": 1, "baseball": 1, "basketball": 2},
    "B073": {"soccer": 4, "baseball": 3, "basketball": 2, "softball": 2, "cricket": 1},
    "B038": {"soccer": 5, "baseball": 4, "basketball": 3, "softball": 2},
    "Q099": {"soccer": 6, "baseball": 4, "basketball": 5, "cricket": 2},
    "Q006": {"soccer": 2, "baseball": 1, "basketball": 2},
    "X099": {"soccer": 4, "baseball": 3, "basketball": 2, "softball": 2, "football": 1},
    "X012": {"soccer": 3, "baseball": 2, "basketball": 2},
    "R001": {"soccer": 2, "baseball": 2, "basketball": 1},
}


def _seed(prop_id: str, day: date) -> random.Random:
    key = f"{prop_id}-{day.isoformat()}"
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return random.Random(h)


def _occupancy_rate(rng: random.Random, day: date, slot_hour: int) -> float:
    is_weekend = day.weekday() >= 5
    if is_weekend:
        return rng.uniform(0.55, 0.85)
    if 12 <= slot_hour < 18:
        return rng.uniform(0.30, 0.55)
    return rng.uniform(0.10, 0.30)


def generate_mock_csv(
    prop_id: str,
    activity: Optional[str],
    start_date: date,
    end_date: date,
) -> str:
    park_name = PARK_NAMES.get(prop_id, prop_id)
    park_fields = FIELD_COUNTS.get(prop_id, {"soccer": 2, "baseball": 1, "basketball": 2})

    activities = [activity.lower()] if activity else list(park_fields.keys())
    rows: list[dict] = []
    permit_counter = 10000

    current = start_date
    while current <= end_date:
        for act in activities:
            num_fields = park_fields.get(act, 1)
            rng = _seed(prop_id + act, current)

            # Build slots for the day
            slot_hour = settings.field_open_hour
            while slot_hour + settings.slot_duration_hours <= settings.field_close_hour:
                for field_num in range(1, num_fields + 1):
                    occupancy = _occupancy_rate(rng, current, slot_hour)
                    if rng.random() < occupancy:
                        start_dt = datetime(current.year, current.month, current.day, slot_hour, 0)
                        end_dt = start_dt + timedelta(hours=settings.slot_duration_hours)
                        org_names = [
                            "Brooklyn FC", "Manhattan United", "Queens Athletic",
                            "Bronx Strikers", "SI Rangers", "Park League",
                            "Youth Soccer Club", "Adult League", "School District 22",
                            "Community Board Rec",
                        ]
                        rows.append({
                            "eventid": str(permit_counter),
                            "parkname": park_name,
                            "propertyid": prop_id,
                            "subcategoryname": act.title(),
                            "startdate": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                            "enddate": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
                            "starttime": start_dt.strftime("%I:%M %p"),
                            "endtime": end_dt.strftime("%I:%M %p"),
                            "facilityname": f"Field {field_num}",
                            "eventname": rng.choice(org_names),
                        })
                        permit_counter += 1
                slot_hour += settings.slot_duration_hours
        current += timedelta(days=1)

    buf = io.StringIO()
    if rows:
        headers = list(rows[0].keys())
        buf.write(",".join(headers) + "\n")
        for row in rows:
            buf.write(",".join(str(row[h]) for h in headers) + "\n")
    else:
        buf.write("eventid,parkname,propertyid,subcategoryname,startdate,enddate,starttime,endtime,facilityname,eventname\n")

    return buf.getvalue()
