"""Pure month-level aggregation of daily analyses: error distribution and patterns."""

from datetime import datetime
from math import sqrt

from .analysis import error_metrics

PERCENTILES = (10, 50, 90)
ABSOLUTE_PERCENTILES = (50, 90, 95)


def percentile(values: list[float], p: float) -> float | None:
    """Linear interpolation between closest ranks (the common 'inclusive' definition)."""
    if not values:
        return None
    ordered = sorted(values)
    rank = (len(ordered) - 1) * p / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (rank - lower)


def _round(value: float | None) -> float | None:
    return round(value, 1) if value is not None else None


def summarise(days: list[dict], requested_days: int) -> dict:
    """Aggregate matched hours across daily analyses.

    Errors are recomputed from unrounded forecast and actual values, so the month
    statistics do not inherit per-period display rounding.
    """
    errors: list[float] = []
    actuals: list[float] = []
    by_hour: dict[int, list[float]] = {hour: [] for hour in range(24)}
    daily = []

    for day in sorted(days, key=lambda d: d["deliveryDate"]):
        day_errors = []
        for period in day["periods"]:
            if period["forecastMw"] is None or period["actualMw"] is None:
                continue
            error = period["forecastMw"] - period["actualMw"]
            hour = datetime.fromisoformat(period["startTime"]).hour
            day_errors.append(error)
            by_hour[hour].append(error)
            actuals.append(period["actualMw"])
        errors.extend(day_errors)
        daily.append({
            "decisionDate": datetime.fromisoformat(day["decisionTime"]).date().isoformat(),
            "deliveryDate": day["deliveryDate"],
            "matchedPeriods": len(day_errors),
            **error_metrics(day_errors),
        })

    metrics = error_metrics(errors)
    mean_actual = sum(actuals) / len(actuals) if actuals else None
    mae_pct = (
        round(100 * metrics["maeMw"] / mean_actual, 1)
        if metrics["maeMw"] is not None and mean_actual
        else None
    )
    absolute = [abs(e) for e in errors]
    # Spread around the mean error: the uncertainty left if the persistent bias is corrected.
    std_dev = (
        sqrt(sum((e - sum(errors) / len(errors)) ** 2 for e in errors) / len(errors))
        if errors else None
    )

    return {
        "coverage": {
            "requestedDays": requested_days,
            "analysedDays": len(days),
            "matchedHours": len(errors),
            "expectedHours": requested_days * 24,
        },
        "metrics": metrics,
        "meanActualMw": _round(mean_actual),
        "maePctOfMeanActual": mae_pct,
        "errorStdDevMw": _round(std_dev),
        "errorPercentilesMw": {f"p{p}": _round(percentile(errors, p)) for p in PERCENTILES},
        "absErrorPercentilesMw": {f"p{p}": _round(percentile(absolute, p)) for p in ABSOLUTE_PERCENTILES},
        "byHour": [
            {"hourUtc": hour, "matchedPeriods": len(values), **error_metrics(values)}
            for hour, values in by_hour.items()
        ],
        "days": daily,
    }
