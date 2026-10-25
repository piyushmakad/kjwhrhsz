# Recording outline (target: about 9 minutes in total)

## Part 1: client pilot presentation (≤5 minutes)

**Show:** the January overview at the 09:00 cutoff.

"Your desk has to bid into the day-ahead auctions by 09:20 or 09:50, while wind output for tomorrow is still uncertain. This pilot replays exactly what your team could have known at 09:00 on every January day, then measures how far wind actually missed it."

**Show:** the four headline cards and the 'What this means for buying' panel.

"Across January the typical miss was about 2 GW, roughly 18% of average wind output. More importantly, it was mostly one-directional: the forecast ran about 1.75 GW high on average. In 9 hours out of 10, wind fell short by less than about 4.1 GW. That is the band you would want covered by other supply. If the persistent offset is understood and corrected, the remaining hour-to-hour uncertainty is about ±1.8 GW."

**Show:** the daily MAE bars and the hour-of-day bias chart. Click a bad day.

"Some days were far worse than others, and the error has a clear time-of-day shape. Clicking a day opens its replay."

**Show:** the day replay chart and audit table. Change the cutoff to 15:00.

"Here is the forecast that was available at decision time against what actually happened. Every row shows when its forecast was published. If I move the cutoff to 15:00, ahead of the half-hourly auction, the newer forecasts become eligible and the error shrinks. You can quantify what waiting buys you."

"Next steps: confirm the forecast your desk trades on, extend to more months, and add demand and other supply data to turn this into a purchase-volume view."

## Part 2: technical lead review (≤5 minutes)

**Show:** `docs/architecture.md`.

"The React feature calls two endpoints through TanStack Query. FastAPI routes handle validation, error mapping and cache headers. A service layer coordinates each use case. The Elexon adapter is the only code that knows the upstream API. Day analysis and month aggregation are pure functions with no I/O."

**Show:** `backend/app/analysis.py`, then `backend/app/summary.py`.

"This is the no-lookahead rule: for each delivery hour, take the newest publication at or before the cutoff. Forecasts are hourly and outturn is half-hourly, so I average the two half-hours. If either is missing, the hour is left unscored rather than guessed. The month summary pools the unrounded errors into MAE, bias, RMSE, percentiles and a standard deviation."

**Show:** `backend/app/elexon.py` and `backend/app/cache.py`.

"January data does not change, so I fetch a whole decision day once and let the domain apply any cutoff. One cache entry therefore serves all 24 cutoffs. Concurrent requests share one in-flight load and failures are never cached. Responses also carry CDN cache headers, because Vercel functions lose their memory on a cold start."

**Show:** the `backend/tests/` folder, the test run and the CI workflow.

"There are 37 offline tests covering the cutoff boundary, alignment, missing and conflicting data, percentiles, cache behaviour and partial upstream failure. A separate script checks all of January live against Elexon."

**Show:** the README and Docker Compose.

"Docker runs the backend and an Nginx frontend. Vercel runs them as two projects. The main open questions are the WINDFOR versus FUELHH coverage offset and the half-hour alignment assumption; both are documented."

Before uploading: keep the recording under 10 minutes, set it to YouTube **Unlisted**, and open every submitted link in an incognito window.
