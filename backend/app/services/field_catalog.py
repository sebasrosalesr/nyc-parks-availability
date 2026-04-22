import asyncio
import logging
from collections.abc import Iterable
from typing import Optional

from curl_cffi.requests import AsyncSession
import mercantile

from app.services.mvt_decoder import decode as decode_mvt
from cachetools import TTLCache

from app.config import settings
from app.models import BOROUGH_MAP, FieldCatalogItem, ParkInfo

logger = logging.getLogger(__name__)

MAP_PAGE_PATH = "/permits/field-and-court/map"
HTML_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

FIELD_TYPE_TO_SPORT_IDS: dict[str, set[str]] = {
    "soccer": {"18", "19"},
    "baseball": {"1", "2", "3", "22"},
    "basketball": {"4"},
    "softball": {"20", "21"},
    "football": {"7", "8", "9", "10"},
    "cricket": {"6"},
}

CATALOG_BOUNDS = (-74.27515, 40.47527, -73.48007, 40.95351)

_catalog_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.catalog_ttl_s)
_map_shell_cache: TTLCache = TTLCache(maxsize=1, ttl=settings.catalog_ttl_s)
_catalog_lock = asyncio.Lock()
_map_shell_lock = asyncio.Lock()


async def fetch_map_shell(client: AsyncSession) -> str:
    if "html" in _map_shell_cache:
        return _map_shell_cache["html"]

    async with _map_shell_lock:
        if "html" in _map_shell_cache:
            return _map_shell_cache["html"]

        url = f"{settings.nyc_parks_base}{MAP_PAGE_PATH}"
        resp = await client.get(url, headers=HTML_HEADERS, timeout=settings.request_timeout_s)
        resp.raise_for_status()
        _map_shell_cache["html"] = resp.text
        return resp.text


def supported_sport_ids(field_type: str) -> set[str]:
    return FIELD_TYPE_TO_SPORT_IDS[field_type]


def list_field_types() -> list[str]:
    return sorted(FIELD_TYPE_TO_SPORT_IDS)


def filter_catalog_by_type(catalog: Iterable[FieldCatalogItem], field_type: str) -> list[FieldCatalogItem]:
    sport_ids = supported_sport_ids(field_type)
    return [field for field in catalog if sport_ids.intersection(field.supported_sport_ids)]


async def get_field_catalog(client: AsyncSession) -> list[FieldCatalogItem]:
    if "catalog" in _catalog_cache:
        return _catalog_cache["catalog"]

    async with _catalog_lock:
        if "catalog" in _catalog_cache:
            return _catalog_cache["catalog"]

        await fetch_map_shell(client)
        park_names = await _fetch_park_names(client)
        fields = await _fetch_fields_from_tiles(client, park_names)
        _catalog_cache["catalog"] = fields
        logger.info("Loaded live field catalog with %d permitable fields", len(fields))
        return fields


async def list_parks(client: AsyncSession) -> list[ParkInfo]:
    catalog = await get_field_catalog(client)
    parks: dict[str, ParkInfo] = {}
    for field in catalog:
        if field.prop_id in parks:
            continue
        parks[field.prop_id] = ParkInfo(
            prop_id=field.prop_id,
            name=field.park_name,
            borough=field.borough,
        )
    return sorted(parks.values(), key=lambda park: (park.borough, park.name))


async def _fetch_park_names(client: AsyncSession) -> dict[str, str]:
    park_names: dict[str, str] = {}
    zoom = settings.catalog_tile_zoom
    tiles = list(mercantile.tiles(*CATALOG_BOUNDS, [zoom]))
    semaphore = asyncio.Semaphore(settings.snapshot_concurrency)

    async def load_tile(tile: mercantile.Tile):
        async with semaphore:
            url = f"https://maps.nycgovparks.org/parks/{tile.z}/{tile.x}/{tile.y}"
            resp = await client.get(
                url,
                headers={"Accept": "application/vnd.mapbox-vector-tile"},
                timeout=settings.request_timeout_s,
            )
            resp.raise_for_status()
            decoded = decode_mvt(resp.content)
            return decoded.get("parks_gis_property", {}).get("features", [])

    feature_sets = await asyncio.gather(*(load_tile(tile) for tile in tiles))
    for features in feature_sets:
        for feature in features:
            props = feature.get("properties", {})
            prop_id = str(props.get("propnum", "")).strip()
            name = str(props.get("name", "")).strip()
            if prop_id and name and prop_id not in park_names:
                park_names[prop_id] = name

    if not park_names:
        raise RuntimeError("Could not build a live park-name index from NYC Parks tiles")

    return park_names


async def _fetch_fields_from_tiles(
    client: AsyncSession,
    park_names: dict[str, str],
) -> list[FieldCatalogItem]:
    zoom = settings.catalog_tile_zoom
    tiles = list(mercantile.tiles(*CATALOG_BOUNDS, [zoom]))
    semaphore = asyncio.Semaphore(settings.snapshot_concurrency)

    async def load_tile(tile: mercantile.Tile):
        async with semaphore:
            url = f"https://maps.nycgovparks.org/athletic_facility/{tile.z}/{tile.x}/{tile.y}"
            resp = await client.get(
                url,
                headers={"Accept": "application/vnd.mapbox-vector-tile"},
                timeout=settings.request_timeout_s,
            )
            resp.raise_for_status()
            decoded = decode_mvt(resp.content)
            return decoded.get("athletic_facility", {}).get("features", [])

    field_map: dict[str, FieldCatalogItem] = {}
    feature_sets = await asyncio.gather(*(load_tile(tile) for tile in tiles))

    for features in feature_sets:
        for feature in features:
            item = _catalog_item_from_feature(feature.get("properties", {}), park_names)
            if item and item.field_id not in field_map:
                field_map[item.field_id] = item

    return sorted(field_map.values(), key=lambda item: (item.park_name, item.field_name))


def _base_prop_id(raw: str) -> str:
    """Q099-01 → Q099 (strip zone suffix so it matches the park-names index)."""
    import re
    m = re.match(r"^([A-Z]\d{3})", raw.upper())
    return m.group(1) if m else raw


def _catalog_item_from_feature(props: dict, park_names: dict[str, str]) -> Optional[FieldCatalogItem]:
    if str(props.get("permitable", "")).upper() != "YES":
        return None

    field_id = str(props.get("system", "")).strip()
    raw_prop = str(props.get("gispropnum") or props.get("permit_parent") or "").strip()
    prop_id = _base_prop_id(raw_prop)
    field_name = str(props.get("name", "")).strip()
    if not field_id or not prop_id or not field_name:
        return None

    sport_ids = sorted({part.strip() for part in str(props.get("sports", "")).split(",") if part.strip()})
    borough_code = prop_id[0].upper()

    return FieldCatalogItem(
        field_id=field_id,
        field_name=field_name,
        park_name=park_names.get(prop_id, prop_id),
        prop_id=prop_id,
        borough=BOROUGH_MAP.get(borough_code, borough_code),
        primary_sport_code=str(props.get("primary_sport", "")).strip(),
        supported_sport_ids=sport_ids,
        opening_time=str(props.get("opening_time", "8:00 AM")).strip(),
        close_at_dusk=str(props.get("close_at_dusk", "TRUE")).upper() == "TRUE",
        surface_type=str(props.get("surface_type", "")).strip() or None,
    )
