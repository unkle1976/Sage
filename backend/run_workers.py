"""Worker script — runs inbound and outbound message workers as concurrent asyncio tasks.

Usage:
    python run_workers.py

Polls Redis queues for inbound (process) and outbound (send) messages.
Uses the configured ``whatsapp_provider`` setting to create the appropriate
WhatsApp service (Twilio or Meta).
"""

import asyncio
import logging

from app.core.config import settings
from app.services.queue import MessageQueue
from app.tasks.process_message import process_inbound_message
from app.tasks.send_message import send_outbound_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

POLL_INTERVAL = 1  # seconds between queue polls


def create_whatsapp_service():
    """Create the WhatsApp sending service based on config."""
    if settings.whatsapp_provider == "twilio":
        from app.services.twilio_whatsapp import TwilioWhatsAppService

        logger.info("Using Twilio WhatsApp provider (number: %s)", settings.twilio_whatsapp_number)
        return TwilioWhatsAppService(
            account_sid=settings.twilio_account_sid,
            auth_token=settings.twilio_auth_token,
            from_number=settings.twilio_whatsapp_number,
        )
    else:
        from app.services.whatsapp import WhatsAppService

        logger.info("Using Meta WhatsApp provider (phone_number_id: %s)", settings.whatsapp_phone_number_id)
        return WhatsAppService(
            token=settings.whatsapp_token,
            phone_number_id=settings.whatsapp_phone_number_id,
        )


async def inbound_worker(queue: MessageQueue):
    """Poll the inbound queue and process each message."""
    logger.info("Inbound worker started")
    while True:
        try:
            messages = await queue.dequeue(stream=MessageQueue.INBOUND_STREAM, block=2000)
            for msg in messages:
                try:
                    await process_inbound_message(msg)
                except Exception:
                    logger.exception("Error processing inbound message: %s", msg)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Inbound worker error")
            await asyncio.sleep(POLL_INTERVAL)


async def outbound_worker(queue: MessageQueue, whatsapp_service):
    """Poll the outbound queue and send each message."""
    logger.info("Outbound worker started")
    while True:
        try:
            messages = await queue.dequeue(stream=MessageQueue.OUTBOUND_STREAM, block=2000)
            for msg in messages:
                try:
                    result = await send_outbound_message(msg, whatsapp_service)
                    logger.info("Outbound result for %s: %s", msg.get("to"), result["status"])
                except Exception:
                    logger.exception("Error sending outbound message: %s", msg)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Outbound worker error")
            await asyncio.sleep(POLL_INTERVAL)


async def main():
    """Connect to Redis and run both workers concurrently."""
    queue = MessageQueue(redis_url=settings.redis_url)
    await queue.connect()
    logger.info("Connected to Redis at %s", settings.redis_url)

    whatsapp_service = create_whatsapp_service()

    try:
        await asyncio.gather(
            inbound_worker(queue),
            outbound_worker(queue, whatsapp_service),
        )
    finally:
        await whatsapp_service.close()
        await queue.close()
        logger.info("Workers shut down")


if __name__ == "__main__":
    asyncio.run(main())
