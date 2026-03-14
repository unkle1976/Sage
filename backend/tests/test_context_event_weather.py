import uuid

from app.models.context_event import ContextEvent


def test_context_event_has_weather_snapshot():
    event = ContextEvent(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_type="care_watering",
        summary="Watered tomatoes",
        weather_snapshot={"temp_c": 22, "rainfall_last_24h_mm": 0},
    )
    assert event.weather_snapshot["temp_c"] == 22
