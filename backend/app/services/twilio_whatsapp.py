"""Twilio WhatsApp service — sends messages via Twilio's Messages API.

Drop-in alternative to WhatsAppService (Meta Graph API).  Both expose the same
``send_text(to, text)`` / ``close()`` interface so they can be swapped via config.
"""

import logging

from twilio.rest import Client as TwilioClient

logger = logging.getLogger(__name__)


class TwilioWhatsAppService:
    """Send WhatsApp messages through Twilio's messaging API."""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """Initialise the Twilio client.

        Args:
            account_sid: Twilio Account SID.
            auth_token: Twilio Auth Token.
            from_number: Your Twilio WhatsApp-enabled number (without ``whatsapp:`` prefix).
                         For sandbox mode this is typically ``+14155238886``.
        """
        self._client = TwilioClient(account_sid, auth_token)
        self._from_number = from_number

    async def send_text(self, to: str, text: str) -> dict:
        """Send a plain-text WhatsApp message.

        Args:
            to: Recipient phone number in E.164 format (e.g. ``+447123456789``).
               The ``whatsapp:`` prefix is added automatically.
            text: Message body.

        Returns:
            Dict with ``sid`` and ``status`` from the Twilio API response.
        """
        message = self._client.messages.create(
            body=text,
            from_=f"whatsapp:{self._from_number}",
            to=f"whatsapp:{to}",
        )
        logger.info("Twilio message sent to %s — sid=%s status=%s", to, message.sid, message.status)
        return {"sid": message.sid, "status": message.status}

    async def close(self):
        """No-op — Twilio's REST client doesn't hold persistent connections."""
        pass
