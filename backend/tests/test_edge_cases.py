from datetime import datetime, timezone

import pytest

from app.analysis import analyse

CUTOFF = datetime(2026, 1, 12, 11, tzinfo=timezone.utc)
DAY = "2026-01-13"


def forecast(hour=0, value=100, published="2026-01-12T11:00:00Z"):
    return {"startTime": f"{DAY}T{hour:02d}:00:00Z", "publishTime": published, "generation": value}


def actual(hour=0, minute=0, value=90, published="2026-01-14T00:00:00Z"):
    return {"startTime": f"{DAY}T{hour:02d}:{minute:02d}:00Z", "publishTime": published, "fuelType": "WIND", "generation": value}


def test_cutoff_equality_is_included_but_one_second_later_is_excluded():
    result = analyse([forecast(), forecast(value=999, published="2026-01-12T11:00:01Z")], [], CUTOFF, DAY)
    assert result["periods"][0]["forecastMw"] == 100


def test_missing_forecast_preserves_full_timeline_and_null_metrics():
    result = analyse([forecast(hour=2)], [], CUTOFF, DAY)
    assert len(result["periods"]) == 24
    assert result["periods"][0]["forecastMw"] is None
    assert result["periods"][2]["forecastMw"] == 100
    assert result["metrics"]["maeMw"] is None
    assert result["coverage"]["expectedPeriods"] == 24


def test_missing_second_half_hour_does_not_create_false_accuracy():
    result = analyse([forecast()], [actual()], CUTOFF, DAY)
    assert result["periods"][0]["actualMw"] is None
    assert result["periods"][0]["errorMw"] is None
    assert result["coverage"]["matchedPeriods"] == 0


@pytest.mark.parametrize("reverse", [False, True])
def test_actual_revision_selection_is_independent_of_input_order(reverse):
    rows = [actual(value=20, published="2026-01-13T01:00:00Z"), actual(value=80), actual(minute=30, value=100)]
    result = analyse([forecast()], rows[::-1] if reverse else rows, CUTOFF, DAY)
    assert result["periods"][0]["actualMw"] == 90
    assert result["periods"][0]["errorMw"] == 10


def test_conflicting_latest_values_are_not_chosen_arbitrarily():
    result = analyse([forecast(), forecast(value=200)], [actual(), actual(minute=30)], CUTOFF, DAY)
    assert result["periods"][0]["forecastMw"] is None
    assert any("Conflicting" in warning for warning in result["warnings"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), None, True])
def test_invalid_values_are_excluded_and_reported(value):
    result = analyse([forecast(value=value)], [actual(), actual(minute=30)], CUTOFF, DAY)
    assert result["coverage"]["forecastPeriods"] == 0
    assert any("invalid" in warning for warning in result["warnings"])


def test_formula_values_and_wind_only_filter():
    rows = [actual(value=80), actual(minute=30, value=100), actual(hour=1, value=130), actual(hour=1, minute=30, value=130)]
    rows.append({**actual(value=9999), "fuelType": "CCGT"})
    result = analyse([forecast(), forecast(hour=1)], rows, CUTOFF, DAY)
    assert result["metrics"] == {"maeMw": 20.0, "biasMw": -10.0, "rmseMw": 22.4}
    assert result["coverage"]["matchedPeriods"] == 2


def test_empty_source_returns_missing_values_not_zero_error():
    result = analyse([], [], CUTOFF, DAY)
    assert len(result["periods"]) == 24
    assert result["metrics"] == {"maeMw": None, "biasMw": None, "rmseMw": None}
