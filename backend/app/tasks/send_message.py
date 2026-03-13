"""Outbound message worker — reads from Redis outbound stream and sends via WhatsApp API.

Handles retry with exponential backoff for transient (5xx) errors and logs
dead-lettered messages after max retries.
"""

import asyncio
import logging

import httpx

from app.services.queue import MessageQueue
from app.services.whatsapp import WhatsAppService

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
BASE_DELAY = 1  # seconds


async def send_outbound_message(
    message_data: dict,
    whatsapp_service: WhatsAppService,
) -> dict:
    """Send a single outbound message via WhatsApp with retry logic.

    Args:
        message_data: Dict with keys ``to``, ``text``, ``type``.
        whatsapp_service: Configured WhatsAppService instance.

    Returns:
        Dict with ``status`` ("sent", "failed", or "dead_letter") and optional ``response``.
    """
    to = message_data["to"]
    text = message_data["text"]

    attempt = 0
    last_error: Exception | None = None

    while attempt < MAX_RETRIES:
        attempt += 1
        try:
            response = await whatsapp_service.send_text(to, text)
            logger.info("Message sent to %s (attempt %d)", to, attempt)
            return {"status": "sent", "response": response}

        except httpx.HTTPStatusError as exc:
            last_error = exc
            status_code = exc.response.status_code

            # 4xx errors are client errors — retrying won't help
            if 400 <= status_code < 500:
                logger.warning(
                    "Client error %d sending to %s — not retrying: %s",
                    status_code, to, exc,
                )
                return {"status": "failed", "error": str(exc)}

            # 5xx errors are transient — retry with exponential backoff
            if attempt < MAX_RETRIES:
                delay = BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Transient error %d sending to %s (attempt %d/%d), retrying in %ds",
                    status_code, to, attempt, MAX_RETRIES, delay,
                )
                await asyncio.sleep(delay)
            # else fall through to dead-letter below

    # Exhausted all retries
    logger.error(
        "Dead letter: message to %s failed after %d attempts. Last error: %s. Message: %s",
        to, MAX_RETRIES, last_error, message_data,
    )
    return {"status": "dead_letter", "error": str(last_error)}


async def process_outbound_queue(
    queue: MessageQueue,
    whatsapp_service: WhatsAppService,
) -> list[dict]:
    """Dequeue a batch of outbound messages and send each one.

    Returns:
        List of result dicts from ``send_outbound_message``.
    """
    messages = await queue.dequeue(stream=MessageQueue.OUTBOUND_STREAM)

    if not messages:
        return []

    results = []
    for msg in messages:
        result = await send_outbound_message(msg, whatsapp_service)
        results.append(result)

    return results
