import logging

from fastapi import APIRouter, Query, Request, HTTPException
from fastapi.responses import PlainTextResponse

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
) -> PlainTextResponse:
    """Meta webhook verification — returns the challenge as plain text."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(content=hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def receive_webhook(request: Request):
    """Receive incoming WhatsApp messages and status updates.

    Must return 200 immediately per Meta's requirement (<15s).
    """
    body = await request.json()

    if body.get("object") == "whatsapp_business_account":
        for entry in body.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for msg in messages:
                    logger.info(
                        "Received message from %s: type=%s",
                        msg.get("from"),
                        msg.get("type"),
                    )
                    # TODO: enqueue to Redis in Task 5

                statuses = value.get("statuses", [])
                for status in statuses:
                    logger.debug(
                        "Status update: %s -> %s",
                        status.get("id"),
                        status.get("status"),
                    )

    return {"status": "ok"}
