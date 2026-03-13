import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.weather import WeatherService


@pytest.fixture
def service():
    return WeatherService()


async def test_get_forecast_success(service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "daily": {
            "temperature_2m_max": [15.0, 16.0],
            "temperature_2m_min": [5.0, 6.0],
            "precipitation_sum": [0.0, 2.5],
        },
        "hourly": {
            "temperature_2m": [10.0, 11.0],
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.get_forecast(51.5, -0.1)

    assert "daily" in result
    assert result["daily"]["temperature_2m_max"] == [15.0, 16.0]


async def test_check_frost_risk_detected(service):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "hourly": {
            "temperature_2m": [5.0, 1.5, -1.0, 3.0],
            "time": [
                "2026-03-13T00:00",
                "2026-03-13T03:00",
                "2026-03-13T06:00",
                "2026-03-13T09:00",
            ],
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.check_frost_risk(51.5, -0.1)

    assert result["frost_risk"] is True
    assert len(result["frost_hours"]) == 2  # 1.5 and -1.0
    assert result["min_temperature"] == -1.0


async def test_check_frost_risk_none(service):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "hourly": {
            "temperature_2m": [8.0, 10.0, 12.0],
            "time": [
                "2026-03-13T00:00",
                "2026-03-13T03:00",
                "2026-03-13T06:00",
            ],
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.check_frost_risk(51.5, -0.1)

    assert result["frost_risk"] is False
    assert result["frost_hours"] == []
    assert result["min_temperature"] == 8.0


async def test_watering_guidance_needs_water(service):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "daily": {
            "precipitation_sum": [0.0, 1.0, 0.5, 0.0, 0.0, 0.0],  # 3 past + 3 forecast
            "temperature_2m_max": [22.0, 21.0, 23.0, 24.0, 20.0, 19.0],
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.get_watering_guidance(51.5, -0.1)

    assert result["needs_watering"] is True
    assert result["recent_rainfall_mm"] == 1.5
    assert result["forecast_rainfall_mm"] == 0.0


async def test_watering_guidance_enough_rain(service):
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "daily": {
            "precipitation_sum": [5.0, 3.0, 4.0, 2.0, 1.0, 0.0],
            "temperature_2m_max": [18.0, 17.0, 16.0, 15.0, 14.0, 13.0],
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.get_watering_guidance(51.5, -0.1)

    assert result["needs_watering"] is False
    assert result["recent_rainfall_mm"] == 12.0
