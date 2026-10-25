"""Pure domain logic: availability at cutoff, hourly alignment, and error metrics."""

from datetime import datetime, timedelta, timezone
from math import isfinite, sqrt

UTC = timezone.utc


def parse_time(value: str) -> datetime:
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("A source timestamp must include its UTC offset")
    return timestamp.astimezone(UTC)


def generation(row: dict) -> float:
    if isinstance(row.get("generation"), bool):
        raise ValueError("Boolean generation is invalid")
    value = float(row["generation"])
    if not isfinite(value):
        raise ValueError("Non-finite generation is invalid")
    return value


def error_metrics(errors: list[float]) -> dict:
    """MAE, signed bias, and RMSE in MW; error is forecast minus actual."""
    count = len(errors)
    return {
        "maeMw": round(sum(abs(e) for e in errors) / count, 1) if count else None,
        "biasMw": round(sum(errors) / count, 1) if count else None,
        "rmseMw": round(sqrt(sum(e * e for e in errors) / count), 1) if count else None,
    }


def latest_values(versions: dict) -> tuple[dict, int]:
    """Equal-time contradictory values remain missing; input order never decides."""
    selected = {}
    conflicts = 0
    for target, publications in versions.items():
        published = max(publications)
        values = publications[published]
        if len(values) != 1:
            conflicts += 1
            continue
        selected[target] = (published, next(iter(values)))
    return selected, conflicts


def analyse(
    forecasts: list[dict], actuals: list[dict], decision_time: datetime, delivery_date: str
) -> dict:
    # The API restricts decisions to January, with delivery through 1 February.
    # UK local time is UTC throughout that supported window.
    start = datetime.fromisoformat(delivery_date).replace(tzinfo=UTC)
    end = start + timedelta(days=1)
    forecast_versions: dict = {}
    actual_versions: dict = {}
    invalid_forecasts = invalid_actuals = 0

    for row in forecasts:
        try:
            target = parse_time(row["startTime"])
            published = parse_time(row["publishTime"])
            if not start <= target < end or published > decision_time:
                continue
            value = generation(row)
            # Elexon's documented WINDFOR frequency is hourly. Missing records
            # must not change the frequency or compress the timeline.
            if target.minute or target.second or target.microsecond:
                raise ValueError("Unexpected non-hourly WINDFOR target")
            forecast_versions.setdefault(target, {}).setdefault(published, set()).add(value)
        except (KeyError, TypeError, ValueError, AttributeError):
            invalid_forecasts += 1

    for row in actuals:
        if not isinstance(row, dict) or row.get("fuelType") != "WIND":
            continue
        try:
            target = parse_time(row["startTime"])
            if not start <= target < end:
                continue
            value = generation(row)
            published = parse_time(row["publishTime"]) if row.get("publishTime") else datetime.min.replace(tzinfo=UTC)
            if target.minute not in (0, 30) or target.second or target.microsecond:
                raise ValueError("Unexpected FUELHH target")
            actual_versions.setdefault(target, {}).setdefault(published, set()).add(value)
        except (KeyError, TypeError, ValueError, AttributeError):
            invalid_actuals += 1

    selected, forecast_conflicts = latest_values(forecast_versions)
    actual_by_target, actual_conflicts = latest_values(actual_versions)
    periods = []
    errors = []
    for hour in range(24):
        target = start + timedelta(hours=hour)
        forecast = selected.get(target)
        halves = [actual_by_target.get(target + timedelta(minutes=offset)) for offset in (0, 30)]
        actual = sum(row[1] for row in halves) / 2 if all(row is not None for row in halves) else None
        predicted = forecast[1] if forecast else None
        error = predicted - actual if predicted is not None and actual is not None else None
        if error is not None:
            errors.append(error)
        periods.append({
            "startTime": target.isoformat(),
            "publishTime": forecast[0].isoformat() if forecast else None,
            "forecastMw": predicted,
            "actualMw": actual,
            "errorMw": round(error, 2) if error is not None else None,
        })

    count = len(errors)
    warnings = []
    if len(selected) < 24:
        warnings.append(f"{24 - len(selected)} forecast hours have no valid forecast available by the cutoff.")
    missing_actuals = sum(period["actualMw"] is None for period in periods)
    if missing_actuals:
        warnings.append(f"{missing_actuals} hours lack a complete pair of half-hour wind actuals.")
    if invalid_forecasts or invalid_actuals:
        warnings.append(f"Excluded {invalid_forecasts} invalid forecast rows and {invalid_actuals} invalid wind actual rows.")
    if forecast_conflicts or actual_conflicts:
        warnings.append(f"Conflicting latest values: {forecast_conflicts} forecast hours and {actual_conflicts} actual half-hours; treated as missing.")

    return {
        "decisionTime": decision_time.isoformat(),
        "deliveryDate": delivery_date,
        "coverage": {
            "forecastPeriods": len(selected),
            "matchedPeriods": count,
            "expectedPeriods": 24,
            "forecastResolutionMinutes": 60,
            "actualHalfHours": len(actual_by_target),
        },
        "metrics": error_metrics(errors),
        "periods": periods,
        "warnings": warnings,
    }
