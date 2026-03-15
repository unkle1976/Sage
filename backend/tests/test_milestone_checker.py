from datetime import date, timedelta
from unittest.mock import MagicMock
from app.services.milestone_checker import MilestoneChecker

def _make_plant(planting_date, milestone_index=0, milestones=None, delayed=False):
    plant = MagicMock()
    plant.planting_date = planting_date
    plant.next_milestone_index = milestone_index
    plant.milestone_delayed = delayed
    plant.variety = "Test Plant"
    plant.growth_stage = "seed"
    spec = MagicMock()
    spec.growth_milestones = milestones or [
        {"day": 7, "stage": "sprouting", "check_in": "Should be sprouting"},
        {"day": 21, "stage": "seedling", "check_in": "Seedlings growing"},
    ]
    spec.common_name = "Tomato"
    plant.plant_spec = spec
    return plant

def test_milestone_due_today():
    checker = MilestoneChecker()
    plant = _make_plant(planting_date=date.today() - timedelta(days=7), milestone_index=0)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 1
    assert due[0]["stage"] == "sprouting"

def test_milestone_not_yet_due():
    checker = MilestoneChecker()
    plant = _make_plant(planting_date=date.today() - timedelta(days=3), milestone_index=0)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 0

def test_milestone_overdue_still_triggers():
    checker = MilestoneChecker()
    plant = _make_plant(planting_date=date.today() - timedelta(days=10), milestone_index=0)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 1

def test_weather_gate_blocks_milestone():
    checker = MilestoneChecker()
    milestones = [
        {"day": 7, "stage": "hardening_off", "check_in": "Put outside",
         "weather_gate": {"min_temp": 10, "no_frost": True}},
    ]
    plant = _make_plant(planting_date=date.today() - timedelta(days=7), milestones=milestones)
    weather = {"temp_min_c": 4, "frost": True}
    due = checker.get_due_milestones([plant], date.today(), weather=weather)
    assert len(due) == 1
    assert due[0]["delayed"] is True

def test_weather_gate_passes():
    checker = MilestoneChecker()
    milestones = [
        {"day": 7, "stage": "hardening_off", "check_in": "Put outside",
         "weather_gate": {"min_temp": 10}},
    ]
    plant = _make_plant(planting_date=date.today() - timedelta(days=7), milestones=milestones)
    weather = {"temp_min_c": 14, "frost": False}
    due = checker.get_due_milestones([plant], date.today(), weather=weather)
    assert len(due) == 1
    assert due[0]["delayed"] is False

def test_no_milestones_if_spec_has_none():
    checker = MilestoneChecker()
    plant = _make_plant(planting_date=date.today() - timedelta(days=7))
    plant.plant_spec.growth_milestones = None
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 0

def test_skips_already_passed_milestones():
    checker = MilestoneChecker()
    plant = _make_plant(planting_date=date.today() - timedelta(days=25), milestone_index=1)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 1
    assert due[0]["stage"] == "seedling"

def test_no_planting_date_skipped():
    checker = MilestoneChecker()
    plant = _make_plant(planting_date=None)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 0

def test_all_milestones_complete():
    checker = MilestoneChecker()
    plant = _make_plant(planting_date=date.today() - timedelta(days=30), milestone_index=2)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 0
