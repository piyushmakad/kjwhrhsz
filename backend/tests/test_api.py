from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.elexon import ElexonError
from app.main import app
from app.routes import get_provider


@pytest.fixture
def client():
    async def empty_provider(*args):
        return [], []
    app.dependency_overrides[get_provider] = lambda: empty_provider
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_january_31_delivers_february_1_and_has_typed_contract(client):
    async def boundary_provider(decision, delivery):
        assert decision == date(2026, 1, 31)
        assert delivery == date(2026, 2, 1)
        return [], []
    app.dependency_overrides[get_provider] = lambda: boundary_provider
    response = client.get("/api/analysis?decision_date=2026-01-31")
    assert response.status_code == 200
    body = response.json()
    assert body["deliveryDate"] == "2026-02-01"
    assert body["cutoffHourUtc"] == 9
    assert body["decisionTime"].startswith("2026-01-31T09:00")
    assert "s-maxage" in response.headers["cache-control"]
    assert len(body["periods"]) == 24
    assert body["metrics"]["maeMw"] is None
    schema = client.get("/openapi.json").json()
    assert "AnalysisResponse" in schema["components"]["schemas"]


@pytest.mark.parametrize("query,status", [
    ("decision_date=2025-12-31", 400),
    ("decision_date=2026-02-01", 400),
    ("decision_date=bad-date", 422),
    ("cutoff_hour=24", 422),
    ("cutoff_hour=-1", 422),
])
def test_invalid_request_is_rejected(client, query, status):
    assert client.get(f"/api/analysis?{query}").status_code == status


def test_provider_failure_returns_useful_error_without_internal_details(client):
    async def failing_provider(*args):
        raise ElexonError("upstream diagnostic detail")
    app.dependency_overrides[get_provider] = lambda: failing_provider
    response = client.get("/api/analysis")
    assert response.status_code == 502
    assert "Elexon data is unavailable" in response.json()["detail"]
    assert "diagnostic" not in response.text


def hourly_provider(failing=frozenset()):
    """Every delivery hour forecast 1000 MW; actual 900 MW, except 1200 MW at 18:00."""
    async def provider(decision, delivery):
        if decision in failing:
            raise ElexonError("upstream")
        day = delivery.isoformat()
        forecasts = [{"startTime": f"{day}T{h:02d}:00:00Z", "publishTime": f"{decision.isoformat()}T08:00:00Z",
                      "generation": 1000} for h in range(24)]
        actuals = [{"startTime": f"{day}T{h:02d}:{m:02d}:00Z", "fuelType": "WIND",
                    "generation": 1200 if h == 18 else 900} for h in range(24) for m in (0, 30)]
        return forecasts, actuals
    return provider


def test_summary_covers_every_january_decision(client):
    app.dependency_overrides[get_provider] = lambda: hourly_provider()
    response = client.get("/api/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["coverage"] == {"requestedDays": 31, "analysedDays": 31, "matchedHours": 744, "expectedHours": 744}
    assert len(body["days"]) == 31
    assert body["days"][-1]["deliveryDate"] == "2026-02-01"
    assert body["byHour"][18]["biasMw"] == -200
    assert body["byHour"][0]["biasMw"] == 100
    assert body["warnings"] == []
    assert "s-maxage" in response.headers["cache-control"]


def test_summary_reports_failed_days_and_is_not_edge_cached(client):
    failing = {date(2026, 1, 3), date(2026, 1, 20)}
    app.dependency_overrides[get_provider] = lambda: hourly_provider(failing)
    response = client.get("/api/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["coverage"]["analysedDays"] == 29
    assert "03 Jan" in body["warnings"][0] and "20 Jan" in body["warnings"][0]
    assert "cache-control" not in response.headers


def test_summary_fails_cleanly_when_no_day_is_available(client):
    app.dependency_overrides[get_provider] = lambda: hourly_provider(frozenset(
        date(2026, 1, d) for d in range(1, 32)))
    response = client.get("/api/summary")
    assert response.status_code == 502
