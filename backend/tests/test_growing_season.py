import uuid
from datetime import date

from app.models.growing_season import GrowingSeason


def test_growing_season_model_fields():
    season = GrowingSeason(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        year=2026,
        label="Spring/Summer 2026",
        started_at=date(2026, 3, 1),
    )
    assert season.year == 2026
    assert season.label == "Spring/Summer 2026"
    assert season.ended_at is None
    assert season.season_summary is None
    assert season.weather_summary is None
