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


async def test_normalise_postcode_uppercase(service):
    """Lowercase input gets uppercased."""
    assert service.normalise("dn35 8lz") == "DN35 8LZ"


async def test_normalise_postcode_no_space(service):
    """'dn358lz' gets space inserted → 'DN35 8LZ'."""
    assert service.normalise("dn358lz") == "DN35 8LZ"


async def test_normalise_postcode_strip(service):
    """Whitespace stripped."""
    assert service.normalise("  DN35  ") == "DN35"


async def test_normalise_outcode_inner_space(service):
    """'DN 35' → 'DN35' (remove inner space for outcodes)."""
    assert service.normalise("DN 35") == "DN35"


async def test_lookup_outcode_fallback(service):
    """When full postcode lookup returns 404, fall back to /outcodes/ endpoint."""
    full_404 = MagicMock()
    full_404.status_code = 404

    outcode_200 = MagicMock()
    outcode_200.status_code = 200
    outcode_200.raise_for_status = MagicMock()
    outcode_200.json.return_value = {
        "status": 200,
        "result": {
            "outcode": "DN35",
            "latitude": 53.5596,
            "longitude": -0.0480,
            "admin_district": ["North East Lincolnshire"],
            "country": ["England"],
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(side_effect=[full_404, outcode_200])
        result = await service.lookup("DN35")

    assert result is not None
    assert result["outward_code"] == "DN35"
    assert result["latitude"] == 53.5596
    assert result["admin_district"] == "North East Lincolnshire"


async def test_lookup_outcode_both_fail(service):
    """When both /postcodes/ and /outcodes/ return 404, return None."""
    response_404 = MagicMock()
    response_404.status_code = 404

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=response_404)
        result = await service.lookup("ZZZZZ")

    assert result is None
