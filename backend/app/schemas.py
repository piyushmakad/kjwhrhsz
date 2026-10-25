"""Validated public response contract, exposed by FastAPI's OpenAPI schema."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class ForecastPeriod(Contract):
    startTime: datetime
    publishTime: datetime | None
    forecastMw: float | None
    actualMw: float | None
    errorMw: float | None


class Metrics(Contract):
    maeMw: float | None
    biasMw: float | None
    rmseMw: float | None


class Coverage(Contract):
    forecastPeriods: int = Field(ge=0, le=24)
    matchedPeriods: int = Field(ge=0, le=24)
    expectedPeriods: Literal[24]
    forecastResolutionMinutes: Literal[60]
    actualHalfHours: int = Field(ge=0, le=48)


class AnalysisResponse(Contract):
    decisionDate: date
    decisionTime: datetime
    deliveryDate: date
    cutoffHourUtc: int = Field(ge=0, le=23)
    source: str
    fetchedAt: datetime
    coverage: Coverage
    metrics: Metrics
    periods: list[ForecastPeriod] = Field(min_length=24, max_length=24)
    warnings: list[str]


class Percentiles(Contract):
    p10: float | None
    p50: float | None
    p90: float | None


class AbsolutePercentiles(Contract):
    p50: float | None
    p90: float | None
    p95: float | None


class SummaryCoverage(Contract):
    requestedDays: int = Field(ge=0)
    analysedDays: int = Field(ge=0)
    matchedHours: int = Field(ge=0)
    expectedHours: int = Field(ge=0)


class HourOfDayMetrics(Metrics):
    hourUtc: int = Field(ge=0, le=23)
    matchedPeriods: int = Field(ge=0)


class DayMetrics(Metrics):
    decisionDate: date
    deliveryDate: date
    matchedPeriods: int = Field(ge=0, le=24)


class SummaryResponse(Contract):
    """Month-wide error distribution for one decision cutoff."""
    cutoffHourUtc: int = Field(ge=0, le=23)
    firstDecisionDate: date
    lastDecisionDate: date
    source: str
    fetchedAt: datetime
    coverage: SummaryCoverage
    metrics: Metrics
    meanActualMw: float | None
    maePctOfMeanActual: float | None
    errorStdDevMw: float | None
    errorPercentilesMw: Percentiles
    absErrorPercentilesMw: AbsolutePercentiles
    byHour: list[HourOfDayMetrics] = Field(min_length=24, max_length=24)
    days: list[DayMetrics]
    warnings: list[str]
