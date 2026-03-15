from datetime import date
from app.models.growing_plan_item import GrowingPlanItem


def test_growing_plan_item_creation():
    item = GrowingPlanItem()
    item.status = "queued"
    item.optimal_sow_start = date(2026, 3, 15)
    item.optimal_sow_end = date(2026, 4, 30)
    assert item.status == "queued"


def test_growing_plan_item_statuses():
    for status in ["queued", "ready", "active", "too_late", "skipped"]:
        item = GrowingPlanItem()
        item.status = status
        assert item.status == status


def test_growing_plan_item_has_alternative():
    item = GrowingPlanItem()
    item.suggested_alternative_id = None
    assert item.suggested_alternative_id is None
