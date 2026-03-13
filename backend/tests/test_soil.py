import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from app.services.soil import SoilService


@pytest.fixture
def service():
    return SoilService()


async def test_get_soil_type_success(service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "properties": {
            "soilType": "loam",
            "texture": "medium",
            "drainage": "well-drained",
            "phRange": "6.0-7.0",
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.get_soil_type(51.5, -0.1)

    assert result["soil_type"] == "loam"
    assert result["texture"] == "medium"
    assert result["drainage"] == "well-drained"
    assert result["ph_range"] == "6.0-7.0"
    assert result["source"] == "bgs"


async def test_get_soil_type_api_error_returns_default(service):
    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(side_effect=httpx.ConnectTimeout("timeout"))
        result = await service.get_soil_type(51.5, -0.1)

    assert result["soil_type"] == "unknown"
    assert result["source"] == "default"


async def test_get_soil_type_non_200_returns_default(service):
    mock_response = MagicMock()
    mock_response.status_code = 500

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.get_soil_type(52.0, -1.0)

    assert result["soil_type"] == "unknown"
    assert result["source"] == "default"


async def test_get_soil_type_uses_cache(service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "properties": {
            "soilType": "clay",
            "texture": "heavy",
            "drainage": "poor",
            "phRange": "6.5-7.5",
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result1 = await service.get_soil_type(51.5, -0.1)
        result2 = await service.get_soil_type(51.5, -0.1)

    # Second call should use cache, so get is called only once
    assert mock_client.get.call_count == 1
    assert result1 == result2
    assert result1["soil_type"] == "clay"
