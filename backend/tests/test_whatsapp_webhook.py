import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_webhook_verification(client):
    """Meta sends GET with hub.mode, hub.verify_token, hub.challenge"""
    response = await client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "sage-verify-token",
            "hub.challenge": "test_challenge_string",
        },
    )
    assert response.status_code == 200
    assert response.text == "test_challenge_string"


@pytest.mark.asyncio
async def test_webhook_verification_rejects_bad_token(client):
    response = await client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "test_challenge_string",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_webhook_receives_text_message(client):
    """Meta POST with text message. Should return 200 immediately."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "123456"},
                    "messages": [{
                        "from": "447700900000",
                        "id": "wamid.test123",
                        "timestamp": "1710000000",
                        "type": "text",
                        "text": {"body": "Hello Sage!"},
                    }],
                },
                "field": "messages",
            }],
        }],
    }
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_webhook_handles_status_update(client):
    """Meta POST with delivery status. Should return 200."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "123456"},
                    "statuses": [{
                        "id": "wamid.test123",
                        "status": "delivered",
                        "timestamp": "1710000000",
                        "recipient_id": "447700900000",
                    }],
                },
                "field": "messages",
            }],
        }],
    }
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_webhook_ignores_non_whatsapp(client):
    """POST with wrong object type."""
    payload = {"object": "not_whatsapp", "entry": []}
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200  # Still return 200 (Meta requirement)
