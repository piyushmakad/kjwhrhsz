"""Elexon API adapter. No provider-specific request logic leaks into analysis."""

import asyncio
import logging
import os
from datetime import date, datetime, timedelta, timezone

import httpx

from .cache import AsyncTTLCache

BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"
logger = logging.getLogger(__name__)


class ElexonError(Exception):
    pass


async def _get_rows(client: httpx.AsyncClient, path: str, params: dict) -> list[dict]:
    for attempt in range(2):
        try:
            response = await client.get(path, params=params)
            if attempt == 0 and (response.status_code == 429 or response.status_code >= 500):
                await asyncio.sleep(0.5)
                continue
            response.raise_for_status()
            body = response.json()
            rows = body.get("data") if isinstance(body, dict) else body
            if not isinstance(rows, list):
                raise ElexonError("Unexpected Elexon response shape")
            return rows
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
            logger.warning("Elexon transport failure for %s: %s", path, type(exc).__name__)
            raise ElexonError("Elexon transport failure") from exc
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning("Elexon response failure for %s: %s", path, type(exc).__name__)
            raise ElexonError("Elexon response failure") from exc
    raise ElexonError("Elexon retry exhausted")


async def fetch_day(decision_date: date, delivery_date: date) -> tuple[list[dict], list[dict]]:
    # Raw WINDFOR is filtered by publication; FUELHH can be filtered by settlement day.
    # Read two preceding publication days so an older valid forecast remains available,
    # and read through the end of the decision day so one fetch serves every cutoff hour.
    # The domain layer applies the exact cutoff.
    publish_from = datetime.combine(decision_date - timedelta(days=2), datetime.min.time(), timezone.utc)
    publish_to = datetime.combine(decision_date + timedelta(days=1), datetime.min.time(), timezone.utc)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=12.0) as client:
        forecasts, actuals = await asyncio.gather(_get_rows(client, "/datasets/WINDFOR/stream", {
            "publishDateTimeFrom": publish_from.isoformat().replace("+00:00", "Z"),
            "publishDateTimeTo": publish_to.isoformat().replace("+00:00", "Z"),
        }), _get_rows(client, "/datasets/FUELHH/stream", {
            "settlementDateFrom": delivery_date.isoformat(),
            "settlementDateTo": delivery_date.isoformat(),
            "fuelType": "WIND",
        }))
    return forecasts, actuals


# Historical source data: a decision date's fetch is reused across cutoffs and requests.
_day_cache: AsyncTTLCache[tuple[list[dict], list[dict]]] = AsyncTTLCache(
    ttl_seconds=float(os.getenv("ELEXON_CACHE_TTL_SECONDS", 6 * 3600)),
    max_entries=64,
)


async def cached_fetch_day(decision_date: date, delivery_date: date) -> tuple[list[dict], list[dict]]:
    return await _day_cache.get_or_load(
        (decision_date, delivery_date), lambda: fetch_day(decision_date, delivery_date)
    )
