from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel

BOROUGH_MAP = {"M": "Manhattan", "B": "Brooklyn", "Q": "Queens", "X": "Bronx", "R": "Staten Island"}


class TimeBlock(BaseModel):
    start: datetime
    end: datetime


class DayAvailability(BaseModel):
    date: date
    open_blocks: List[TimeBlock]
    open_minutes: int
    potential_minutes: int


class FieldSchedule(BaseModel):
    field_id: str
    field_name: str
    park_name: str
    prop_id: str
    borough: str
    surface_type: Optional[str] = None
    total_available_minutes: int
    days: List[DayAvailability]


class FieldCatalogItem(BaseModel):
    field_id: str
    field_name: str
    park_name: str
    prop_id: str
    borough: str
    primary_sport_code: str
    supported_sport_ids: List[str]
    opening_time: str
    close_at_dusk: bool
    surface_type: Optional[str] = None


class ParkInfo(BaseModel):
    prop_id: str
    name: str
    borough: str


class AvailabilityQuery(BaseModel):
    field_type: str
    start_date: date
    end_date: date
    prop_ids: List[str]
    matching_field_count: int
    matching_park_count: int
    snapshot_count: int
    live_snapshot_count: int
    cached_snapshot_count: int


class AvailabilityResponse(BaseModel):
    fields: List[FieldSchedule]
    fetched_at: datetime
    query: AvailabilityQuery
