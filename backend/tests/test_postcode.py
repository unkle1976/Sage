import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.postcode import PostcodeService


@pytest.fixture
def service():
    return PostcodeService()


async def test_lookup_success(service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "status": 200,
        "result": {
            "postcode": "SW1A 1AA",
            "outcode": "SW1A",
            "latitude": 51.501009,
            "longitude": -0.141588,
            "region": "London",
            "admin_district": "Westminster",
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.lookup("SW1A 1AA")

    assert result is not None
    assert result["postcode"] == "SW1A 1AA"
    assert result["latitude"] == 51.501009
    assert result["longitude"] == -0.141588
    assert result["region"] == "London"
    assert result["admin_district"] == "Westminster"
    assert result["outward_code"] == "SW1A"


async def test_lookup_not_found(service):
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.lookup("INVALID")

    assert result is None


async def test_validate_valid_postcode(service):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": 200, "result": True}

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.validate("SW1A 1AA")

    assert result is True


async def test_validate_invalid_postcode(service):
    mock_response = MagicMock()
    mock_response.json.return_value = {"status": 200, "result": False}

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        result = await service.validate("NOPE")

    assert result is False
