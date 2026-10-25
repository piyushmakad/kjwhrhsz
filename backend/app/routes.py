from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from .elexon import ElexonError, cached_fetch_day
from .schemas import AnalysisResponse, SummaryResponse
from .service import (
    DEFAULT_CUTOFF_HOUR,
    FIRST_DECISION_DATE,
    LAST_DECISION_DATE,
    DayProvider,
    build_analysis,
    build_summary,
)

router = APIRouter(prefix="/api")

# Historical data: let browsers and the Vercel CDN reuse successful responses.
CACHE_CONTROL = "public, max-age=300, s-maxage=86400, stale-while-revalidate=86400"
CutoffHour = Annotated[int, Query(ge=0, le=23, description="Decision cutoff, whole UTC hour")]
UNAVAILABLE = "Elexon data is unavailable. Please retry shortly."


def get_provider() -> DayProvider:
    return cached_fetch_day


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/analysis", response_model=AnalysisResponse)
async def day_analysis(
    response: Response,
    provider: Annotated[DayProvider, Depends(get_provider)],
    decision_date: date = Query(default=date(2026, 1, 12)),
    cutoff_hour: CutoffHour = DEFAULT_CUTOFF_HOUR,
):
    if not FIRST_DECISION_DATE <= decision_date <= LAST_DECISION_DATE:
        raise HTTPException(400, "Decision date must be in January 2026")
    try:
        result = await build_analysis(decision_date, cutoff_hour, provider)
    except ElexonError as exc:
        raise HTTPException(502, UNAVAILABLE) from exc
    response.headers["Cache-Control"] = CACHE_CONTROL
    return result


@router.get("/summary", response_model=SummaryResponse)
async def january_summary(
    response: Response,
    provider: Annotated[DayProvider, Depends(get_provider)],
    cutoff_hour: CutoffHour = DEFAULT_CUTOFF_HOUR,
):
    try:
        result = await build_summary(cutoff_hour, provider)
    except ElexonError as exc:
        raise HTTPException(502, UNAVAILABLE) from exc
    # A partially fetched month should be retried soon rather than cached at the edge.
    if result.coverage.analysedDays == result.coverage.requestedDays:
        response.headers["Cache-Control"] = CACHE_CONTROL
    return result
