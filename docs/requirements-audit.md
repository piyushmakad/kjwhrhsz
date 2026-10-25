# Requirements checklist

Last updated 25 October 2026. This file maps each challenge requirement to its evidence.

| Requirement | Status | Evidence or remaining work |
| --- | --- | --- |
| Latest renewable forecast available at the buying decision | Done | Latest WINDFOR publication at or before the cutoff, per delivery hour. The default cutoff of 09:00 sits before the GB day-ahead hourly gate closures. Tested at the exact cutoff boundary. |
| Quantitative forecast accuracy for decision-making | Done | Day view: MAE, bias, RMSE, coverage and a per-hour audit table. January overview: pooled metrics, P10/P50/P90 error, bias-corrected spread, by-hour bias and daily MAE. |
| Elexon data only (FUELHH `WIND`, WINDFOR) | Done | No other datasets are used. |
| Decisions made in January 2026 | Done | All 31 decision dates (delivery 2 Jan – 1 Feb). Live check: 744 of 744 hours matched at 09:00 (`evidence/january-live-check.json`). |
| React frontend, Python backend | Done | React + TypeScript (Vite); FastAPI. |
| Docker | Configured | `compose.yaml` with backend and Nginx frontend images. Re-run `docker compose up --build` before recording. |
| Vercel or Heroku deployment | **Pending** | Vercel configuration is in place. Add the live URL to the README. |
| AI usage disclosed in README | Done | See "AI tools" in the README. |
| Public GitHub repository with a random name | **Pending** | Rename the repository to a random string (e.g. `kjhwr`) when publishing. |
| README: files, startup, deployment link | Done except the link | The deployment URL is still pending. |
| Video: client pitch (≤5 min) and tech review (≤5 min), unlisted, ≤10 min total | **Pending** | Outline in `demo-script.md`. |
| Submission form; all URLs checked in incognito | **Pending** | |

## Automated checks

- Backend: `python -m pytest tests -q` runs 37 tests, all offline.
- Frontend: `npm run build` runs the TypeScript type-check and the production build.
- CI: `.github/workflows/verify.yml` runs both on every push.

## Analytical qualifications

1. Comparing each hourly forecast with the mean of the two half-hour actuals in that hour is an assumption to confirm with the client.
2. Accuracy figures are retrospective and based on one month, which is a small sample for setting a buying policy.
3. WINDFOR and FUELHH may cover different wind fleets. The January forecast averages about 1.75 GW above outturn, and this offset needs explaining before it is corrected.
4. Without demand and other supply data, the pilot cannot compute the purchase quantity.
