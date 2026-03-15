from __future__ import annotations
from datetime import date


class GrowingPlanService:

    @staticmethod
    def check_timing(calendar_entries: list, today: date) -> dict:
        current_month = today.month
        latest_end = 0
        earliest_start = 13

        for entry in calendar_entries:
            if entry.activity in ("sow_indoors", "sow_outdoors"):
                if entry.month_end > latest_end:
                    latest_end = entry.month_end
                if entry.month_start < earliest_start:
                    earliest_start = entry.month_start

        if latest_end == 0:
            return {"status": "unknown"}

        if current_month > latest_end:
            return {"status": "too_late", "last_month": latest_end}
        elif current_month >= earliest_start:
            return {"status": "ready", "sow_start": earliest_start, "sow_end": latest_end}
        else:
            return {"status": "queued", "sow_start": earliest_start}

    @staticmethod
    def prioritise(items: list[dict]) -> list[dict]:
        return sorted(items, key=lambda x: x.get("optimal_sow_start") or date.max)
