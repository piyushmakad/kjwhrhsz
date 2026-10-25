# Delivery plan

1. **Domain and data contract: done.** Decision cutoff aligned to GB day-ahead gate closures (default 09:00 UK). Elexon field shapes and January time resolution verified against live data.
2. **Backend: done.** No-lookahead day analysis, January-wide summary, cached Elexon provider, typed response contracts.
3. **Frontend: done.** January overview (headline metrics, buying implication, daily and hourly charts) and day replay with an audit table.
4. **Quality: done locally.** 37 backend tests and the frontend build pass. Live January check matches 744 of 744 hours. Re-run Docker Compose before recording.
5. **Publish: pending.** Public GitHub repository with a random name; Vercel backend and frontend; live URL added to the README.
6. **Record and submit: pending.** Two-part video per `docs/demo-script.md`, uploaded as unlisted; links checked in incognito; form submitted.
