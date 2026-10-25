# Architecture and analytical contract

## Shape

```text
React feature (features/wind-replay)
  -> TanStack Query hooks (useSummary, useAnalysis)
  -> shared HTTP client (lib/api-client)
  -> FastAPI routes: validation, error mapping, Cache-Control     routes.py
  -> application service: date range, cutoff, fan-out             service.py
  -> cached day provider -> Elexon adapter -> WINDFOR + FUELHH    elexon.py, cache.py
  -> pure domain functions: day analysis, month aggregation       analysis.py, summary.py
```

Dependencies point inward:
- The domain modules (`analysis.py`, `summary.py`) have no HTTP or I/O code and are tested with small in-memory records.
- The routes receive the data provider through FastAPI dependency injection, so API tests swap in a fake provider and never touch the network.
- A single Python service is enough for this read-only pilot. Splitting it into separate services would add operational cost without any benefit.

## Request flow

**Day replay** (`/api/analysis`):
1. The service works out the delivery date (decision date + 1) and the UTC cutoff.
2. It asks the provider for that decision date's raw rows.
3. `analyse()` filters the rows to the cutoff and returns 24 hourly periods with metrics.

**January overview** (`/api/summary`):
1. The service runs the same per-day analysis for all 31 decision dates, at most 4 at a time.
2. `summarise()` pools all matched hours into month-level statistics.
3. If Elexon fails for a date, that date is excluded and named in a warning. The request fails only if every date fails.

## Selection and alignment

1. Parse `publishTime` and `startTime` as UTC. Keep WINDFOR rows whose target falls in the delivery day and whose publish time is at or before the cutoff.
2. For each target hour, use the row with the latest eligible `publishTime`. If two rows share that publish time but disagree, treat the hour as missing; input order never decides which value wins.
3. Filter FUELHH to `fuelType: WIND`. Average the two half-hour values within each forecast hour. If either half is missing, leave the hour unscored.
4. Error is **forecast − actual**. MAE, bias and RMSE are computed over matched hours only, and the matched count is always returned with them.

Month statistics are recomputed from unrounded forecast and actual values:
- pooled MAE, bias and RMSE, and MAE as a percentage of mean actual output
- signed error percentiles (P10, P50, P90): P90 is the shortfall band a buyer may want covered by other supply
- absolute-error percentiles
- the standard deviation of the error (the uncertainty left once the persistent bias is removed)
- by-hour and by-day breakdowns

## Decision cutoff

The GB day-ahead hourly auctions close at 09:20 (EPEX) and 09:50 (N2EX) UK time on the day before delivery. The EPEX half-hourly auction closes at 15:30. The default cutoff is 09:00, the last whole hour before the hourly gate closures. The user can choose any whole hour.

All supported decisions are in January, so UK time equals UTC for every decision and delivery timestamp. Supporting a wider date range would require explicit daylight-saving handling.

## Caching

- **Provider cache.** `elexon.fetch_day` reads WINDFOR publications through the end of the decision day. The domain layer applies the exact cutoff, so one cached fetch per decision date serves all 24 cutoff hours.
- **`AsyncTTLCache` behaviour:**
  - Concurrent requests for the same key share one in-flight load, which prevents a cache stampede.
  - Failures are not stored.
  - Least-recently-used entries are evicted beyond 64 dates.
  - Entries expire after `ELEXON_CACHE_TTL_SECONDS` (default 6 hours).
- **HTTP cache.** Successful responses carry `Cache-Control: public, max-age=300, s-maxage=86400, stale-while-revalidate=86400`. Vercel's CDN can then serve repeat requests without invoking a serverless function, which matters because the in-process cache does not survive cold starts. A summary with failed days is not edge-cached, so it is retried promptly.

## Data interpretation

This is an operational comparison rather than a formal benchmark of the forecasting model:
- WINDFOR forecasts wind farms with operational metering; FUELHH reports national outturn by fuel type. Their coverage can differ.
- In January 2026 the forecast sits on average about 1.75 GW above FUELHH. That offset should be explained before it is corrected.
- Demand and other supply are out of scope, so the pilot does not calculate a purchase quantity.

## Deployment

Docker Compose builds the React bundle into an Nginx image and runs FastAPI as a separate container. Nginx proxies `/api` to the backend, so the local app is served from one origin.

On Vercel, two projects are created from the same repository:
- a Python project for the FastAPI backend
- a Vite project for the frontend

The backend's allowed CORS origin and the frontend's API URL are set through environment variables.
