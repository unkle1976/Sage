import pytest
from unittest.mock import AsyncMock
from app.channels.slack_sender import SlackOutboundSender

@pytest.fixture
def sender():
    client = AsyncMock()
    return SlackOutboundSender(client)

@pytest.mark.asyncio
async def test_send_message(sender):
    sender.client.conversations_open = AsyncMock(return_value={"ok": True, "channel": {"id": "D12345"}})
    sender.client.chat_postMessage = AsyncMock(return_value={"ok": True})
    result = await sender.send("U12345", "Hello from Sage!")
    sender.client.conversations_open.assert_called_once_with(users="U12345")
    sender.client.chat_postMessage.assert_called_once()
    assert result is True

@pytest.mark.asyncio
async def test_send_opens_dm_channel(sender):
    sender.client.conversations_open = AsyncMock(return_value={"ok": True, "channel": {"id": "D99999"}})
    sender.client.chat_postMessage = AsyncMock(return_value={"ok": True})
    await sender.send("U12345", "Test")
    call_args = sender.client.chat_postMessage.call_args
    assert call_args.kwargs.get("channel") == "D99999" or call_args[1].get("channel") == "D99999"

@pytest.mark.asyncio
async def test_send_handles_error(sender):
    sender.client.conversations_open = AsyncMock(side_effect=Exception("Slack error"))
    result = await sender.send("U12345", "Hello!")
    assert result is False

@pytest.mark.asyncio
async def test_send_passes_text(sender):
    sender.client.conversations_open = AsyncMock(return_value={"ok": True, "channel": {"id": "D12345"}})
    sender.client.chat_postMessage = AsyncMock(return_value={"ok": True})
    await sender.send("U12345", "Your tomatoes should be sprouting!")
    call_args = sender.client.chat_postMessage.call_args
    assert "Your tomatoes should be sprouting!" in str(call_args)
