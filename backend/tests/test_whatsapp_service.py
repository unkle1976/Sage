import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.whatsapp import WhatsAppService


@pytest.fixture
def service():
    return WhatsAppService(token="test-token", phone_number_id="12345")


async def test_send_text_message(service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"messages": [{"id": "wamid.sent123"}]}
    mock_response.raise_for_status = MagicMock()

    with patch.object(service, "_client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await service.send_text("447700900000", "Hello from Sage!")
        assert result["messages"][0]["id"] == "wamid.sent123"
        mock_client.post.assert_called_once()


async def test_send_button_message(service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"messages": [{"id": "wamid.sent456"}]}
    mock_response.raise_for_status = MagicMock()

    with patch.object(service, "_client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await service.send_buttons(
            to="447700900000",
            body="Did you cover the beans?",
            buttons=[
                {"id": "yes", "title": "Yes"},
                {"id": "no", "title": "No"},
            ],
        )
        assert result["messages"][0]["id"] == "wamid.sent456"


async def test_send_list_message(service):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"messages": [{"id": "wamid.sent789"}]}
    mock_response.raise_for_status = MagicMock()

    with patch.object(service, "_client") as mock_client:
        mock_client.post = AsyncMock(return_value=mock_response)
        result = await service.send_list(
            to="447700900000",
            body="What help do you need?",
            button_text="Choose",
            sections=[{
                "title": "Options",
                "rows": [
                    {"id": "sowing", "title": "Sowing guide"},
                    {"id": "pests", "title": "Pest help"},
                ],
            }],
        )
        assert result["messages"][0]["id"] == "wamid.sent789"
