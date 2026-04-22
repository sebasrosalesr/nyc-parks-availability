import logging
from datetime import date, datetime
from typing import List, Optional

from curl_cffi.requests import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.requests import Request

from app.config import settings
from app.models import AvailabilityResponse, ParkInfo
from app.services.field_catalog import list_field_types, list_parks
from app.services.live_availability import build_availability_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["availability"])


def get_client(request: Request) -> AsyncSession:
    return request.app.state.http_client


@router.get("/parks", response_model=List[ParkInfo])
async def get_parks(client: AsyncSession = Depends(get_client)):
    return await list_parks(client)


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    field_type: str = Query(..., description="Sport: soccer, baseball, basketball, …"),
    start_date: date = Query(..., description="Start date YYYY-MM-DD"),
    end_date: date = Query(..., description="End date YYYY-MM-DD"),
    prop_ids: Optional[str] = Query(
        None, description="Comma-separated prop_ids (default: all known parks)"
    ),
    client: AsyncSession = Depends(get_client),
):
    field_type = field_type.lower().strip()
    valid_field_types = list_field_types()
    if field_type not in valid_field_types:
        raise HTTPException(400, f"field_type must be one of: {', '.join(valid_field_types)}")
    if end_date < start_date:
        raise HTTPException(400, "end_date must be ≥ start_date")
    if (end_date - start_date).days > settings.max_range_days:
        raise HTTPException(400, f"Date range cannot exceed {settings.max_range_days} days")

    targets = [part.strip() for part in prop_ids.split(",") if part.strip()] if prop_ids else None

    try:
        return await build_availability_response(
            client=client,
            field_type=field_type,
            start_date=start_date,
            end_date=end_date,
            prop_ids=targets,
        )
    except Exception as exc:
        logger.exception("Availability query failed")
        raise HTTPException(502, f"Could not fetch NYC Parks availability: {exc}") from exc
