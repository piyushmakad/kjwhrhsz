# Architecture and analytical contract

## System overview

```mermaid
flowchart LR
    User[Energy buyer<br/>browser] -->|HTTPS| Front

    subgraph Vercel["Vercel project: one domain"]
        Front["frontend service<br/>React + Vite static app"]
        Back["backend service<br/>FastAPI on Python"]
    end

    Front -->|"GET /api/summary<br/>GET /api/analysis"| Back
    Back -->|"WINDFOR stream<br/>forecasts, hourly"| Elexon[(Elexon BMRS API)]
    Back -->|"FUELHH stream<br/>WIND actuals, half-hourly"| Elexon
    CDN[[Vercel CDN<br/>Cache-Control s-maxage]] -.->|serves repeat responses| User
```

Everything is read-only, public data. There is no database or authentication. Elexon is the only source of truth, and the backend fetches it on demand and caches it.

## Backend layers

```mermaid
flowchart TD
    subgraph HTTP["HTTP layer"]
        Routes["routes.py<br/>validation · error mapping · Cache-Control"]
        Schemas["schemas.py<br/>Pydantic response contracts → OpenAPI"]
    end

    subgraph App["Application layer"]
        Service["service.py<br/>January date range · default 09:00 cutoff<br/>31-day fan-out, 4 at a time"]
    end

    subgraph Infra["Infrastructure"]
        Provider["elexon.cached_fetch_day<br/>injected via Depends(get_provider)"]
        Cache["cache.py<br/>AsyncTTLCache"]
        Adapter["elexon.fetch_day<br/>httpx · one retry"]
    end

    subgraph Domain["Pure domain: no I/O"]
        Analysis["analysis.py<br/>no-lookahead selection<br/>half-hour alignment · metrics"]
        Summary["summary.py<br/>pooled metrics · percentiles<br/>by hour · by day"]
    end

    Routes --> Service
    Routes -. response_model .-> Schemas
    Service --> Provider
    Provider --> Cache
    Cache -->|miss| Adapter
    Adapter --> Elexon[(Elexon BMRS)]
    Service --> Analysis
    Service --> Summary
    Summary --> Analysis
```

Dependencies point inward:
- The domain modules (`analysis.py`, `summary.py`) have no HTTP or I/O code and are tested with small in-memory records.
- The routes receive the data provider through FastAPI dependency injection, so API tests swap in a fake provider and never touch the network.
- A single Python service is enough for this read-only pilot. Splitting it into separate services would add operational cost without any benefit.

## Frontend structure

```mermaid
flowchart TD
    Page["WindReplayPage.tsx<br/>tabs · decision date · cutoff"]
    Page -->|January overview| Month["MonthOverview.tsx<br/>cards · buying guidance"]
    Page -->|Day replay| Day["MetricCards · TrendChart<br/>MethodNotes · ForecastTable"]
    Month --> Bars["BarChart.tsx<br/>daily MAE, click to replay · hourly bias"]
    Bars -->|select day| Page

    Page --> HookS["useSummary(cutoff)"]
    Page --> HookA["useAnalysis(date, cutoff)"]
    HookS --> Api["api.ts → lib/api-client.ts"]
    HookA --> Api
    Api -->|fetch /api/...| Backend[(FastAPI)]
    QC["lib/query-client.ts<br/>TanStack Query: browser cache, one retry on 5xx"] -.-> HookS
    QC -.-> HookA
```

## Request flow: January overview

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser
    participant R as routes.py
    participant S as service.py
    participant C as AsyncTTLCache
    participant E as Elexon
    participant D as analysis + summary

    B->>R: GET /api/summary?cutoff_hour=9
    R->>S: build_summary(9)
    loop 31 decision dates, 4 at a time
        S->>C: get_or_load(decision date)
        alt cached
            C-->>S: raw rows
        else first request
            C->>E: WINDFOR + FUELHH, in parallel
            E-->>C: raw rows, cached 6 h
            C-->>S: raw rows
        end
        S->>D: analyse(rows, cutoff 09:00)
        D-->>S: 24 hourly periods
    end
    S->>D: summarise(31 days)
    D-->>S: month statistics
    S-->>R: SummaryResponse
    R-->>B: 200 JSON + Cache-Control
```

**Day replay** (`/api/analysis`) follows the same path for one decision date, without the loop or `summarise()`.

If Elexon fails for some dates, those dates are excluded and named in a warning, and the response is not edge-cached. The request fails with a 502 only if every date fails.

## Forecast selection and alignment

```mermaid
flowchart TD
    W["WINDFOR rows<br/>many publications per target hour"] --> F1{"publishTime ≤ cutoff<br/>and target in delivery day?"}
    F1 -- no --> X1[Ignored: later revisions can't leak in]
    F1 -- yes --> F2["Latest publishTime per target hour"]
    F2 --> F3{"Two values at the same<br/>latest publishTime?"}
    F3 -- yes --> X2[Hour marked missing + warning]
    F3 -- no --> FC[Forecast MW for the hour]

    A["FUELHH rows"] --> A1{"fuelType = WIND?"}
    A1 -- no --> X3[Ignored]
    A1 -- yes --> A2{"Both half-hours present?<br/>HH:00 and HH:30"}
    A2 -- no --> X4[Hour left unscored]
    A2 -- yes --> AC["Actual MW = mean of the two halves"]

    FC --> E["Error = forecast − actual<br/>positive = wind overestimated"]
    AC --> E
    E --> M["MAE · bias · RMSE<br/>over matched hours only"]
```

Rules behind the diagram:
1. All timestamps are parsed as UTC.
2. Input order never decides between conflicting values.
3. Missing data is reported as missing and counted in coverage; it is never scored as zero error.

Month statistics are recomputed from unrounded forecast and actual values:
- pooled MAE, bias and RMSE, and MAE as a percentage of mean actual output
- signed error percentiles (P10, P50, P90): P90 is the shortfall band a buyer may want covered by other supply
- absolute-error percentiles
- the standard deviation of the error (the uncertainty left once the persistent bias is removed)
- by-hour and by-day breakdowns

## Decision cutoff

```mermaid
flowchart LR
    subgraph D1["Decision day D-1 · UK time = UTC in January"]
        C["09:00<br/>default cutoff<br/>latest forecast published by now"] --> E1["09:20<br/>EPEX hourly<br/>auction closes"]
        E1 --> E2["09:50<br/>N2EX hourly<br/>auction closes"]
        E2 --> E3["15:30<br/>EPEX half-hourly<br/>auction closes"]
    end
    E3 --> DD["Delivery day D<br/>actual wind measured<br/>error scored"]
```

The default cutoff is 09:00, the last whole hour before the hourly gate closures. The user can choose any whole hour.

All supported decisions are in January, so UK time equals UTC for every decision and delivery timestamp. Supporting a wider date range would require explicit daylight-saving handling.

## Caching

```mermaid
flowchart LR
    Req[Request for a decision date] --> Hit{"Fresh entry<br/>in cache?"}
    Hit -- yes --> Ret[Return cached rows]
    Hit -- no --> Fly{"Load already<br/>in flight?"}
    Fly -- yes --> Wait[Await the same task]
    Fly -- no --> Load[Fetch from Elexon]
    Load --> OK{Succeeded?}
    OK -- yes --> Store["Store for 6 h<br/>LRU, max 64 dates"] --> Ret
    OK -- no --> Err[Raise; nothing stored]
    Wait --> Ret
```

- **One fetch serves all cutoffs.** `elexon.fetch_day` reads WINDFOR publications through the end of the decision day, and the domain layer applies the exact cutoff. So one cached fetch per decision date serves all 24 cutoff hours.
- **Configurable expiry.** Set `ELEXON_CACHE_TTL_SECONDS` to change the default of 6 hours.
- **HTTP cache.** Successful responses carry `Cache-Control: public, max-age=300, s-maxage=86400, stale-while-revalidate=86400`.
  - Vercel's CDN can then serve repeat requests without invoking a serverless function. This matters because the in-process cache does not survive cold starts.
  - A summary with failed days is not edge-cached, so it is retried promptly.
- **Measured locally:**
  - A cold month makes 62 Elexon calls and takes about 15 s.
  - After that, any cutoff takes under 1 s.

## Deployment

```mermaid
flowchart LR
    subgraph Local["Docker Compose: localhost:8080"]
        N["frontend container<br/>Nginx: static bundle"] -->|"proxy /api"| P["backend container<br/>uvicorn + FastAPI :8000"]
    end

    subgraph Cloud["Vercel: one project, root vercel.json"]
        VF["frontend service<br/>Vite build"]
        VB["backend service<br/>FastAPI, backend/index.py"]
        RW{{"rewrites<br/>/api/* → backend<br/>/* → frontend"}} --> VF
        RW --> VB
    end

    GH[GitHub push] --> CI["GitHub Actions<br/>pytest + tsc/vite build"]
    GH --> Cloud
```

Both setups serve the frontend and the API from one origin, so the frontend always calls a relative `/api` path and no CORS configuration is needed. `FRONTEND_ORIGIN` and `VITE_API_BASE_URL` are only needed if the backend is ever hosted on a separate domain.

## Data interpretation

This is an operational comparison rather than a formal benchmark of the forecasting model:
- WINDFOR forecasts wind farms with operational metering; FUELHH reports national outturn by fuel type. Their coverage can differ.
- In January 2026 the forecast sits on average about 1.75 GW above FUELHH. That offset should be explained before it is corrected.
- Demand and other supply are out of scope, so the pilot does not calculate a purchase quantity.
