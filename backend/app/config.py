from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Live public endpoints ────────────────────────────────────────────────
    nyc_parks_base: str = "https://www.nycgovparks.org"

    # ── Request behaviour ────────────────────────────────────────────────────
    # Availability is now 1 request per date (not per 30-min slot), so the
    # per-request delay can be longer without slowing the overall response.
    request_delay_s: float = 1.0   # polite gap between sequential date queries
    request_timeout_s: float = 30.0
    max_retries: int = 3
    snapshot_concurrency: int = 1  # kept for tile fetches; availability is serial

    # ── In-memory cache ──────────────────────────────────────────────────────
    cache_ttl_s: int = 3600
    catalog_ttl_s: int = 86400
    cache_maxsize: int = 512

    # ── Search bounds ────────────────────────────────────────────────────────
    catalog_tile_zoom: int = 13
    field_open_hour: int = 8
    field_close_hour: int = 22
    slot_minutes: int = 60
    max_range_days: int = 14
    prefer_fallback_availability: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
