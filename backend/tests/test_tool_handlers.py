import uuid
from decimal import Decimal

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.tool_handlers import build_tool_handlers
from app.models.user import User


@pytest.fixture
def test_user():
    user = User(
        whatsapp_phone="447700900000",
        onboarding_step="complete",
        onboarding_complete=True,
        uk_region="Bristol",
        soil_type="clay loam",
        postcode_outward="BS3",
        experience_level="beginner",
        latitude=Decimal("51.438000"),
        longitude=Decimal("-2.604000"),
    )
    user.id = uuid.uuid4()
    return user


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def mock_weather():
    service = MagicMock()
    service.get_forecast = AsyncMock(return_value={
        "daily": {
            "time": ["2026-03-13", "2026-03-14"],
            "temperature_2m_max": [12.0, 14.0],
            "temperature_2m_min": [4.0, 6.0],
            "precipitation_sum": [0.5, 2.0],
        }
    })
    service.check_frost_risk = AsyncMock(return_value={
        "frost_risk": True,
        "frost_hours": [{"time": "2026-03-14T03:00", "temperature": 1.5}],
        "min_temperature": 1.5,
    })
    service.get_watering_guidance = AsyncMock(return_value={
        "needs_watering": False,
        "recent_rainfall_mm": 8.0,
        "forecast_rainfall_mm": 12.0,
        "max_temperature": 14,
    })
    return service


@pytest.fixture
def handlers(test_user, mock_session, mock_weather):
    return build_tool_handlers(
        user=test_user,
        session=mock_session,
        weather_service=mock_weather,
    )


# --- Weather tools ---

async def test_weather_forecast(handlers, mock_weather):
    result = await handlers["get_weather_forecast"]({})
    assert "forecast" in result
    assert len(result["forecast"]) == 2
    assert result["forecast"][0]["high_c"] == 12.0
    assert result["location"] == "Bristol"
    mock_weather.get_forecast.assert_awaited_once()


async def test_frost_risk(handlers, mock_weather):
    result = await handlers["check_frost_risk"]({})
    assert result["frost_risk"] is True
    mock_weather.check_frost_risk.assert_awaited_once()


async def test_watering_guidance(handlers, mock_weather):
    result = await handlers["get_watering_guidance"]({})
    assert result["needs_watering"] is False
    mock_weather.get_watering_guidance.assert_awaited_once()


# --- No location ---

async def test_weather_no_location(mock_session, mock_weather):
    user = User(whatsapp_phone="000", onboarding_complete=True)
    user.id = uuid.uuid4()
    h = build_tool_handlers(user=user, session=mock_session, weather_service=mock_weather)
    result = await h["get_weather_forecast"]({})
    assert "error" in result


# --- Soil profile ---

async def test_soil_profile(handlers):
    result = await handlers["get_soil_profile"]({})
    assert result["location"] == "Bristol"
    assert "soil_type" in result


# --- Plant search ---

async def test_search_plant_database(handlers, mock_session):
    tomato_spec = MagicMock()
    tomato_spec.common_name = "Tomato"
    tomato_spec.botanical_name = "Solanum lycopersicum"
    tomato_spec.category = "vegetable"
    tomato_spec.growing_difficulty = "beginner"
    tomato_spec.uk_hardiness = "half_hardy"
    tomato_spec.sun_requirements = "full_sun"
    tomato_spec.water_needs = "moderate"
    tomato_spec.spacing_cm = {"row": 60, "plant": 45}
    tomato_spec.days_to_harvest_min = 60
    tomato_spec.days_to_harvest_max = 85
    tomato_spec.soil_preferences = {"likes": ["well-drained"]}
    tomato_spec.common_pests = ["aphids"]
    tomato_spec.common_diseases = ["blight"]
    tomato_spec.companion_plants = ["basil"]
    tomato_spec.notes = "Great for beginners"

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [tomato_spec]
    mock_session.execute = AsyncMock(return_value=mock_result)

    result = await handlers["search_plant_database"]({"query": "tomatoes"})
    assert len(result["results"]) == 1
    assert result["results"][0]["common_name"] == "Tomato"


async def test_search_plant_empty_query(handlers):
    result = await handlers["search_plant_database"]({"query": ""})
    assert "error" in result


# --- Context event logging ---

async def test_log_context_event(handlers, mock_session):
    garden = MagicMock()
    garden.id = uuid.uuid4()
    mock_garden_result = MagicMock()
    mock_garden_result.scalar_one_or_none.return_value = garden
    mock_session.execute = AsyncMock(return_value=mock_garden_result)

    result = await handlers["log_context_event"]({
        "event_type": "planting",
        "summary": "Planted tomato seedlings in raised bed",
    })
    assert result["logged"] is True
    assert result["event_type"] == "planting"
    mock_session.add.assert_called_once()
    mock_session.commit.assert_awaited_once()
