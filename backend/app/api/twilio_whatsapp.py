"""Twilio WhatsApp webhook handler.

Twilio delivers inbound WhatsApp messages as form-encoded POST requests.
This module parses them and enqueues to the same Redis inbound queue used
by the Meta webhook handler, so the downstream processing pipeline is shared.
"""

import logging

from fastapi import APIRouter, Request, Response

from app.core.config import settings
from app.services.queue import MessageQueue

logger = logging.getLogger(__name__)

router = APIRouter()

# Module-level queue instance — connected during app startup via lifespan
message_queue: MessageQueue | None = None


def _strip_whatsapp_prefix(number: str) -> str:
    """Remove the ``whatsapp:`` prefix that Twilio includes on phone numbers."""
    if number.startswith("whatsapp:"):
        return number[len("whatsapp:"):]
    return number


def _validate_twilio_signature(request: Request, form_data: dict) -> bool:
    """Optionally validate the Twilio request signature.

    Returns True if validation passes or if auth token is not configured
    (i.e. validation is skipped in development).
    """
    auth_token = settings.twilio_auth_token
    if not auth_token:
        return True

    try:
        from twilio.request_validator import RequestValidator

        validator = RequestValidator(auth_token)
        signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)
        return validator.validate(url, form_data, signature)
    except Exception:
        logger.exception("Error validating Twilio signature")
        return False


@router.post("/webhook/twilio-whatsapp")
async def receive_twilio_webhook(request: Request):
    """Receive incoming WhatsApp messages via Twilio.

    Twilio sends form-encoded POST data with fields like ``From``, ``Body``,
    ``MessageSid``, ``To``, etc.  Returns a 200 with empty TwiML to acknowledge.
    """
    form_data = await request.form()
    form_dict = dict(form_data)

    if not _validate_twilio_signature(request, form_dict):
        logger.warning("Invalid Twilio signature — rejecting webhook")
        return Response(status_code=403)

    sender = form_dict.get("From", "")
    body = form_dict.get("Body", "")
    message_sid = form_dict.get("MessageSid", "")

    # Normalise the phone number to plain E.164 (no whatsapp: prefix)
    phone = _strip_whatsapp_prefix(sender)

    logger.info("Twilio inbound from %s: sid=%s body=%s", phone, message_sid, body[:80])

    if message_queue and body:
        await message_queue.enqueue_inbound(
            {
                "from": phone,
                "message_id": message_sid,
                "type": "text",
                "text": body,
                "timestamp": None,  # Twilio doesn't include a Unix timestamp
            }
        )

    # Return empty TwiML response — Twilio expects 200 with optional TwiML
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
    )
