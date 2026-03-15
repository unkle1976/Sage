from datetime import date
from unittest.mock import MagicMock
from app.services.growing_plan import GrowingPlanService

def _make_calendar_entry(activity, month_start, month_end):
    entry = MagicMock()
    entry.activity = activity
    entry.month_start = month_start
    entry.month_end = month_end
    return entry

def test_check_timing_in_window():
    calendars = [_make_calendar_entry("sow_indoors", 3, 4)]
    result = GrowingPlanService.check_timing(calendars, date(2026, 3, 15))
    assert result["status"] == "ready"

def test_check_timing_too_late():
    calendars = [_make_calendar_entry("sow_indoors", 1, 2)]
    result = GrowingPlanService.check_timing(calendars, date(2026, 3, 15))
    assert result["status"] == "too_late"

def test_check_timing_future():
    calendars = [_make_calendar_entry("sow_indoors", 5, 6)]
    result = GrowingPlanService.check_timing(calendars, date(2026, 3, 15))
    assert result["status"] == "queued"

def test_check_timing_outdoor_sow():
    calendars = [_make_calendar_entry("sow_outdoors", 4, 6)]
    result = GrowingPlanService.check_timing(calendars, date(2026, 5, 1))
    assert result["status"] == "ready"

def test_check_timing_multiple_windows():
    calendars = [
        _make_calendar_entry("sow_indoors", 2, 3),
        _make_calendar_entry("sow_outdoors", 4, 5),
    ]
    result = GrowingPlanService.check_timing(calendars, date(2026, 4, 15))
    assert result["status"] == "ready"

def test_check_timing_no_sow_entries():
    calendars = [_make_calendar_entry("harvest_begin", 7, 9)]
    result = GrowingPlanService.check_timing(calendars, date(2026, 3, 15))
    assert result["status"] == "unknown"

def test_prioritise_orders_by_sow_date():
    items = [
        {"common_name": "Basil", "optimal_sow_start": date(2026, 5, 1)},
        {"common_name": "Tomato", "optimal_sow_start": date(2026, 3, 15)},
        {"common_name": "Strawberry", "optimal_sow_start": date(2026, 4, 1)},
    ]
    ordered = GrowingPlanService.prioritise(items)
    assert [i["common_name"] for i in ordered] == ["Tomato", "Strawberry", "Basil"]

def test_prioritise_handles_missing_date():
    items = [
        {"common_name": "Unknown", "optimal_sow_start": None},
        {"common_name": "Tomato", "optimal_sow_start": date(2026, 3, 15)},
    ]
    ordered = GrowingPlanService.prioritise(items)
    assert ordered[0]["common_name"] == "Tomato"
