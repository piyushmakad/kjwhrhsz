"""Application orchestration; provider is injectable for deterministic API tests."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from datetime import date, datetime, time, timedelta, timezone

from .analysis import analyse
from .elexon import ElexonError
from .schemas import AnalysisResponse, SummaryResponse
from .summary import summarise

DayProvider = Callable[[date, date], Awaitable[tuple[list[dict], list[dict]]]]

# Pilot scope: purchase decisions made in January 2026 (delivery 2 Jan to 1 Feb).
FIRST_DECISION_DATE = date(2026, 1, 1)
LAST_DECISION_DATE = date(2026, 1, 31)
# GB day-ahead hourly auctions close at 09:20 (EPEX) and 09:50 (N2EX) UK time.
# January is GMT, so 09:00 UTC is the last whole hour before both gate closures.
DEFAULT_CUTOFF_HOUR = 9
SOURCE = "Elexon BMRS WINDFOR + FUELHH (WIND)"

logger = logging.getLogger(__name__)


def pilot_decision_dates() -> list[date]:
    days = (LAST_DECISION_DATE - FIRST_DECISION_DATE).days + 1
    return [FIRST_DECISION_DATE + timedelta(days=offset) for offset in range(days)]


async def _analyse_day(decision_date: date, cutoff_hour: int, provider: DayProvider) -> dict:
    delivery_date = decision_date + timedelta(days=1)
    cutoff = datetime.combine(decision_date, time(cutoff_hour), timezone.utc)
    forecasts, actuals = await provider(decision_date, delivery_date)
    return analyse(forecasts, actuals, cutoff, delivery_date.isoformat())


async def build_analysis(decision_date: date, cutoff_hour: int, provider: DayProvider) -> AnalysisResponse:
    result = await _analyse_day(decision_date, cutoff_hour, provider)
    return AnalysisResponse(
        **result,
        decisionDate=decision_date,
        cutoffHourUtc=cutoff_hour,
        source=SOURCE,
        fetchedAt=datetime.now(timezone.utc),
    )


async def build_summary(cutoff_hour: int, provider: DayProvider, concurrency: int = 4) -> SummaryResponse:
    """Analyse every pilot decision date. Days whose source fetch fails are reported, not guessed."""
    decision_dates = pilot_decision_dates()
    semaphore = asyncio.Semaphore(concurrency)

    async def one(decision_date: date) -> dict:
        async with semaphore:
            return await _analyse_day(decision_date, cutoff_hour, provider)

    outcomes = await asyncio.gather(*(one(d) for d in decision_dates), return_exceptions=True)
    days, unavailable = [], []
    for decision_date, outcome in zip(decision_dates, outcomes):
        if isinstance(outcome, ElexonError):
            unavailable.append(decision_date)
        elif isinstance(outcome, BaseException):
            raise outcome
        else:
            days.append(outcome)
    if not days:
        raise ElexonError("No January decision date could be fetched")
    if unavailable:
        logger.warning("Summary excludes %d unavailable decision dates", len(unavailable))

    warnings = []
    if unavailable:
        warnings.append(
            f"{len(unavailable)} decision dates could not be fetched from Elexon and are excluded: "
            + ", ".join(d.strftime("%d %b") for d in unavailable) + "."
        )
    result = summarise(days, requested_days=len(decision_dates))
    missing = result["coverage"]["expectedHours"] - result["coverage"]["matchedHours"]
    if missing:
        warnings.append(f"{missing} delivery hours lack a matched forecast and actual and are not scored.")
    return SummaryResponse(
        **result,
        cutoffHourUtc=cutoff_hour,
        firstDecisionDate=FIRST_DECISION_DATE,
        lastDecisionDate=LAST_DECISION_DATE,
        source=SOURCE,
        fetchedAt=datetime.now(timezone.utc),
        warnings=warnings,
    )
