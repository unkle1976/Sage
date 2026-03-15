from sqlalchemy import inspect as sa_inspect

from app.models.plant_spec import PlantSpec
from app.models.plant import Plant
from app.models.engagement_profile import EngagementProfile


def _has_column(model_class, column_name: str) -> bool:
    """Check if a SQLAlchemy model has a mapped column (not just a Python attr)."""
    mapper = sa_inspect(model_class)
    return column_name in mapper.columns


def test_plant_spec_has_growth_milestones():
    assert _has_column(PlantSpec, "growth_milestones"), "PlantSpec missing growth_milestones column"
    ps = PlantSpec(common_name="Tomato", category="vegetable")
    ps.growth_milestones = [{"day": 7, "stage": "sprouting", "check_in": "Seeds should be germinating"}]
    assert ps.growth_milestones[0]["day"] == 7


def test_plant_spec_has_interesting_facts():
    assert _has_column(PlantSpec, "interesting_facts"), "PlantSpec missing interesting_facts column"
    ps = PlantSpec(common_name="Tomato", category="vegetable")
    ps.interesting_facts = ["Tomatoes are technically a fruit"]
    assert len(ps.interesting_facts) == 1


def test_plant_has_milestone_tracking():
    assert _has_column(Plant, "next_milestone_index"), "Plant missing next_milestone_index column"
    assert _has_column(Plant, "milestone_delayed"), "Plant missing milestone_delayed column"
    p = Plant()
    p.next_milestone_index = 2
    assert p.next_milestone_index == 2
    p.milestone_delayed = True
    assert p.milestone_delayed is True


def test_plant_has_next_milestone_date():
    from datetime import date
    assert _has_column(Plant, "next_milestone_date"), "Plant missing next_milestone_date column"
    p = Plant()
    p.next_milestone_date = date(2026, 4, 1)
    assert p.next_milestone_date == date(2026, 4, 1)


def test_engagement_profile_has_unanswered_count():
    assert _has_column(EngagementProfile, "unanswered_count"), "EngagementProfile missing unanswered_count column"
    ep = EngagementProfile()
    ep.unanswered_count = 3
    assert ep.unanswered_count == 3


def test_engagement_profile_has_current_frequency():
    assert _has_column(EngagementProfile, "current_frequency"), "EngagementProfile missing current_frequency column"
    ep = EngagementProfile()
    ep.current_frequency = "reduced"
    assert ep.current_frequency == "reduced"
