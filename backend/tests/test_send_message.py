import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.tasks.send_message import send_outbound_message, process_outbound_queue


@pytest.fixture
def whatsapp_service():
    service = AsyncMock()
    service.send_text = AsyncMock(
        return_value={"messages": [{"id": "wamid.sent123"}]}
    )
    return service


@pytest.fixture
def queue():
    return AsyncMock()


# --- send_outbound_message tests ---


async def test_send_text_message_success(whatsapp_service):
    message = {"to": "447700900000", "text": "Hello from Sage!", "type": "text"}
    result = await send_outbound_message(message, whatsapp_service)

    assert result["status"] == "sent"
    whatsapp_service.send_text.assert_called_once_with("447700900000", "Hello from Sage!")


async def test_send_returns_api_response(whatsapp_service):
    message = {"to": "447700900000", "text": "Hi!", "type": "text"}
    result = await send_outbound_message(message, whatsapp_service)

    assert result["status"] == "sent"
    assert result["response"]["messages"][0]["id"] == "wamid.sent123"


async def test_retry_on_500_error(whatsapp_service):
    """Transient 5xx errors should be retried with exponential backoff."""
    error_response = MagicMock()
    error_response.status_code = 500
    error_response.request = MagicMock()
    error = httpx.HTTPStatusError("Server error", request=error_response.request, response=error_response)

    # Fail twice, then succeed
    whatsapp_service.send_text = AsyncMock(
        side_effect=[error, error, {"messages": [{"id": "wamid.retry_ok"}]}]
    )

    message = {"to": "447700900000", "text": "Retry me", "type": "text"}

    with patch("app.tasks.send_message.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await send_outbound_message(message, whatsapp_service)

    assert result["status"] == "sent"
    assert whatsapp_service.send_text.call_count == 3
    # Exponential backoff: 1s then 2s
    assert mock_sleep.call_count == 2
    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


async def test_no_retry_on_4xx_error(whatsapp_service):
    """Client errors (4xx) should not be retried — they won't succeed on retry."""
    error_response = MagicMock()
    error_response.status_code = 400
    error_response.request = MagicMock()
    error = httpx.HTTPStatusError("Bad request", request=error_response.request, response=error_response)

    whatsapp_service.send_text = AsyncMock(side_effect=error)

    message = {"to": "447700900000", "text": "Bad", "type": "text"}
    result = await send_outbound_message(message, whatsapp_service)

    assert result["status"] == "failed"
    # Only called once — no retries for 4xx
    assert whatsapp_service.send_text.call_count == 1


async def test_dead_letter_after_max_retries(whatsapp_service):
    """After 5 failed attempts, message should be logged as dead letter."""
    error_response = MagicMock()
    error_response.status_code = 503
    error_response.request = MagicMock()
    error = httpx.HTTPStatusError("Unavailable", request=error_response.request, response=error_response)

    whatsapp_service.send_text = AsyncMock(side_effect=error)

    message = {"to": "447700900000", "text": "Will fail", "type": "text"}

    with patch("app.tasks.send_message.asyncio.sleep", new_callable=AsyncMock):
        with patch("app.tasks.send_message.logger") as mock_logger:
            result = await send_outbound_message(message, whatsapp_service)

    assert result["status"] == "dead_letter"
    assert whatsapp_service.send_text.call_count == 5
    # Verify dead letter was logged
    mock_logger.error.assert_called()
    log_msg = mock_logger.error.call_args[0][0]
    assert "dead letter" in log_msg.lower() or "Dead letter" in log_msg


# --- process_outbound_queue tests ---


async def test_process_queue_sends_batch(whatsapp_service, queue):
    queue.dequeue = AsyncMock(
        return_value=[
            {"to": "447700900001", "text": "Msg 1", "type": "text", "_stream_id": "1-0"},
            {"to": "447700900002", "text": "Msg 2", "type": "text", "_stream_id": "2-0"},
        ]
    )

    results = await process_outbound_queue(queue, whatsapp_service)

    assert len(results) == 2
    assert all(r["status"] == "sent" for r in results)
    assert whatsapp_service.send_text.call_count == 2


async def test_process_queue_empty(whatsapp_service, queue):
    queue.dequeue = AsyncMock(return_value=[])

    results = await process_outbound_queue(queue, whatsapp_service)

    assert results == []
    whatsapp_service.send_text.assert_not_called()


async def test_process_queue_partial_failure(whatsapp_service, queue):
    """One message fails but others still send."""
    error_response = MagicMock()
    error_response.status_code = 400
    error_response.request = MagicMock()
    error = httpx.HTTPStatusError("Bad", request=error_response.request, response=error_response)

    whatsapp_service.send_text = AsyncMock(
        side_effect=[
            {"messages": [{"id": "wamid.ok1"}]},
            error,
        ]
    )

    queue.dequeue = AsyncMock(
        return_value=[
            {"to": "447700900001", "text": "OK msg", "type": "text", "_stream_id": "1-0"},
            {"to": "447700900002", "text": "Bad msg", "type": "text", "_stream_id": "2-0"},
        ]
    )

    results = await process_outbound_queue(queue, whatsapp_service)

    assert len(results) == 2
    assert results[0]["status"] == "sent"
    assert results[1]["status"] == "failed"
