"""Opt-in live evidence, separate from deterministic CI tests.

Run from backend: python -m scripts.verify_january
"""

import asyncio
import json
from datetime import date, datetime, timezone
from pathlib import Path

from app.elexon import fetch_day
from app.service import DEFAULT_CUTOFF_HOUR, build_analysis


async def main():
    semaphore = asyncio.Semaphore(2)

    async def check(day):
        async with semaphore:
            result = await build_analysis(date(2026, 1, day), DEFAULT_CUTOFF_HOUR, fetch_day)
            assert len(result.periods) == 24
            assert all(p.publishTime is None or p.publishTime <= result.decisionTime for p in result.periods)
            return {
                "decisionDate": result.decisionDate.isoformat(),
                "deliveryDate": result.deliveryDate.isoformat(),
                "coverage": result.coverage.model_dump(),
                "metrics": result.metrics.model_dump(),
                "warnings": result.warnings,
            }

    days = await asyncio.gather(*(check(day) for day in range(1, 32)))
    report = {
        "checkedAtUtc": datetime.now(timezone.utc).isoformat(),
        "cutoffHourUtc": DEFAULT_CUTOFF_HOUR,
        "decisionDays": len(days),
        "matchedHours": sum(day["coverage"]["matchedPeriods"] for day in days),
        "expectedHours": 31 * 24,
        "completeDays": sum(day["coverage"]["matchedPeriods"] == 24 for day in days),
        "scope": f"Every January 2026 decision date at {DEFAULT_CUTOFF_HOUR:02d}:00 UTC; delivery 2 January through 1 February. Does not test every cutoff hour.",
        "days": days,
    }
    destination = Path(__file__).resolve().parents[2] / "docs" / "evidence" / "january-live-check.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "days"}, indent=2))
    print(f"Evidence saved to {destination}")


if __name__ == "__main__":
    asyncio.run(main())
