from datetime import date, timedelta
from unittest.mock import MagicMock
from app.services.milestone_checker import MilestoneChecker
from app.services.engagement import EngagementService
from app.services.proactive import ProactiveMessageBuilder
from app.services.growing_plan import GrowingPlanService
from app.data.plant_milestones import PLANT_MILESTONES

def test_full_milestone_flow():
    """Simulate: user plants tomatoes -> 10 days pass -> milestone triggers -> message built"""
    tomato_data = PLANT_MILESTONES["tomato"]
    plant = MagicMock()
    plant.planting_date = date.today() - timedelta(days=10)
    plant.next_milestone_index = 0
    plant.milestone_delayed = False
    plant.variety = "Gardener's Delight"
    plant.growth_stage = "seed"
    spec = MagicMock()
    spec.growth_milestones = tomato_data["milestones"]
    spec.common_name = "Tomato"
    plant.plant_spec = spec

    checker = MilestoneChecker()
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 1
    assert due[0]["stage"] == tomato_data["milestones"][0]["stage"]

    ctx = ProactiveMessageBuilder.build_milestone_context(due)
    assert "Tomato" in ctx
    assert "Gardener's Delight" in ctx

    freq = EngagementService.get_frequency_for_unanswered(0)
    assert freq == "normal"
    assert EngagementService.min_days_between(freq) == 3

def test_weather_delayed_milestone_flow():
    """Milestone due but weather too cold -> delayed message"""
    tomato_data = PLANT_MILESTONES["tomato"]
    # Find a milestone with a weather gate
    gated_idx = None
    for i, m in enumerate(tomato_data["milestones"]):
        if "weather_gate" in m:
            gated_idx = i
            break

    if gated_idx is None:
        return  # No weather-gated milestones to test

    gated = tomato_data["milestones"][gated_idx]
    plant = MagicMock()
    plant.planting_date = date.today() - timedelta(days=gated["day"])
    plant.next_milestone_index = gated_idx
    plant.milestone_delayed = False
    plant.variety = None
    plant.growth_stage = "seedling"
    spec = MagicMock()
    spec.growth_milestones = tomato_data["milestones"]
    spec.common_name = "Tomato"
    plant.plant_spec = spec

    checker = MilestoneChecker()
    weather = {"temp_min_c": 2, "frost": True}
    due = checker.get_due_milestones([plant], date.today(), weather=weather)
    assert len(due) == 1
    assert due[0]["delayed"] is True

    ctx = ProactiveMessageBuilder.build_milestone_context(due)
    assert "delay" in ctx.lower() or "DELAY" in ctx

def test_growing_plan_timing_check():
    cal = MagicMock()
    cal.activity = "sow_indoors"
    cal.month_start = 3
    cal.month_end = 4
    result = GrowingPlanService.check_timing([cal], date(2026, 3, 15))
    assert result["status"] == "ready"

def test_silence_handling_flow():
    assert EngagementService.get_frequency_for_unanswered(0) == "normal"
    assert EngagementService.should_nudge(0) is False
    assert EngagementService.should_nudge(2) is True
    assert EngagementService.get_frequency_for_unanswered(2) == "normal"
    assert EngagementService.get_frequency_for_unanswered(3) == "reduced"
    assert EngagementService.min_days_between("reduced") == 7
    assert EngagementService.get_frequency_for_unanswered(5) == "minimal"
    assert EngagementService.min_days_between("minimal") == 14

def test_multiple_plants_milestone_check():
    """Multiple plants with different milestone states"""
    checker = MilestoneChecker()

    tomato = MagicMock()
    tomato.planting_date = date.today() - timedelta(days=10)
    tomato.next_milestone_index = 0
    tomato.variety = "Moneymaker"
    tomato.growth_stage = "seed"
    tomato_spec = MagicMock()
    tomato_spec.growth_milestones = PLANT_MILESTONES["tomato"]["milestones"]
    tomato_spec.common_name = "Tomato"
    tomato.plant_spec = tomato_spec

    lettuce = MagicMock()
    lettuce.planting_date = date.today() - timedelta(days=60)
    lettuce.next_milestone_index = 0
    lettuce.variety = "Little Gem"
    lettuce.growth_stage = "seed"
    lettuce_spec = MagicMock()
    lettuce_spec.growth_milestones = PLANT_MILESTONES["lettuce"]["milestones"]
    lettuce_spec.common_name = "Lettuce"
    lettuce.plant_spec = lettuce_spec

    radish = MagicMock()
    radish.planting_date = date.today() - timedelta(days=2)
    radish.next_milestone_index = 1  # "planted" check-in already done, next is germination (day 5)
    radish.variety = None
    radish.growth_stage = "seed"
    radish_spec = MagicMock()
    radish_spec.growth_milestones = PLANT_MILESTONES["radish"]["milestones"]
    radish_spec.common_name = "Radish"
    radish.plant_spec = radish_spec

    due = checker.get_due_milestones([tomato, lettuce, radish], date.today())

    # Tomato should have sprouting milestone due (day 10)
    # Lettuce should have multiple milestones overdue
    # Radish should have nothing yet (only 2 days)
    plant_names = [d["plant_name"] for d in due]
    assert "Tomato" in plant_names
    assert "Lettuce" in plant_names
    assert "Radish" not in plant_names

    ctx = ProactiveMessageBuilder.build_milestone_context(due)
    assert "Tomato" in ctx
    assert "Lettuce" in ctx
