import pytest

from app.summary import percentile, summarise


def period(hour, forecast, actual, day="2026-01-13"):
    return {"startTime": f"{day}T{hour:02d}:00:00+00:00", "forecastMw": forecast, "actualMw": actual}


def day(periods, delivery="2026-01-13", decision="2026-01-12T09:00:00+00:00"):
    return {"deliveryDate": delivery, "decisionTime": decision, "periods": periods}


@pytest.mark.parametrize("values,p,expected", [
    ([], 50, None),
    ([5], 90, 5),
    ([1, 2, 3, 4], 50, 2.5),
    ([0, 10], 90, 9),
    ([3, 1, 2], 100, 3),
])
def test_percentile_interpolates_between_ranks(values, p, expected):
    assert percentile(values, p) == expected


def test_month_metrics_pool_hours_across_days_and_skip_unmatched():
    first = day([period(0, 1000, 900), period(1, 1000, None), period(2, None, 900)])
    second = day([period(0, 800, 1000, "2026-01-14")], "2026-01-14", "2026-01-13T09:00:00+00:00")
    result = summarise([second, first], requested_days=2)
    assert result["coverage"] == {"requestedDays": 2, "analysedDays": 2, "matchedHours": 2, "expectedHours": 48}
    assert result["metrics"] == {"maeMw": 150.0, "biasMw": -50.0, "rmseMw": 158.1}
    assert result["meanActualMw"] == 950.0
    assert result["maePctOfMeanActual"] == 15.8
    assert result["errorStdDevMw"] == 150.0
    assert [d["deliveryDate"] for d in result["days"]] == ["2026-01-13", "2026-01-14"]
    assert result["days"][0]["decisionDate"] == "2026-01-12"
    assert result["days"][0]["matchedPeriods"] == 1


def test_hour_of_day_pattern_and_error_distribution():
    periods = [period(h, 1000, 1000 - (h + 1) * 10) for h in range(24)]
    result = summarise([day(periods)], requested_days=1)
    assert result["byHour"][0] == {"hourUtc": 0, "matchedPeriods": 1, "maeMw": 10.0, "biasMw": 10.0, "rmseMw": 10.0}
    assert result["byHour"][23]["biasMw"] == 240.0
    assert result["errorPercentilesMw"] == {"p10": 33.0, "p50": 125.0, "p90": 217.0}
    assert result["absErrorPercentilesMw"]["p95"] == 228.5


def test_empty_month_has_null_statistics_not_zero():
    result = summarise([], requested_days=31)
    assert result["metrics"] == {"maeMw": None, "biasMw": None, "rmseMw": None}
    assert result["errorPercentilesMw"] == {"p10": None, "p50": None, "p90": None}
    assert result["errorStdDevMw"] is None
    assert result["coverage"]["expectedHours"] == 744
    assert len(result["byHour"]) == 24
