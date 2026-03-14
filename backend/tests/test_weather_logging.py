import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.weather import WeatherService


@pytest.mark.asyncio
async def test_get_weather_snapshot():
    """get_weather_snapshot returns a dict suitable for ContextEvent.weather_snapshot."""
    service = WeatherService()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "current_weather": {
            "temperature": 18.5,
            "windspeed": 12.0,
        },
        "daily": {
            "temperature_2m_max": [18.5],
            "temperature_2m_min": [8.2],
            "precipitation_sum": [1.5],
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        snapshot = await service.get_weather_snapshot(53.56, -0.05)

    assert "temp_c" in snapshot
    assert "temp_max_c" in snapshot
    assert "rainfall_mm" in snapshot
    assert snapshot["temp_c"] == 18.5
