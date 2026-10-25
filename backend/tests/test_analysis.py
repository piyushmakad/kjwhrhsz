from datetime import datetime, timezone

from app.analysis import analyse


def test_latest_available_forecast_and_no_lookahead():
    target = "2026-01-13T00:00:00Z"
    forecasts = [
        {"startTime": target, "publishTime": "2026-01-11T20:00:00Z", "generation": 8000},
        {"startTime": target, "publishTime": "2026-01-12T10:00:00Z", "generation": 7000},
        {"startTime": target, "publishTime": "2026-01-12T12:00:00Z", "generation": 6100},
    ]
    actuals = [
        {"startTime": target, "settlementDate": "2026-01-13", "fuelType": "WIND", "generation": 6500},
        {"startTime": "2026-01-13T00:30:00Z", "settlementDate": "2026-01-13", "fuelType": "WIND", "generation": 6700},
    ]
    result = analyse(forecasts, actuals, datetime(2026, 1, 12, 11, tzinfo=timezone.utc), "2026-01-13")
    assert result["periods"][0]["forecastMw"] == 7000
    assert result["periods"][0]["actualMw"] == 6600
    assert result["periods"][0]["errorMw"] == 400
    assert result["metrics"]["maeMw"] == 400
    assert result["metrics"]["biasMw"] == 400
    assert result["coverage"]["expectedPeriods"] == 24
