from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

class SlackOutboundSender:
    def __init__(self, client):
        self.client = client

    async def send(self, slack_user_id: str, text: str) -> bool:
        try:
            dm = await self.client.conversations_open(users=slack_user_id)
            channel_id = dm["channel"]["id"]
            await self.client.chat_postMessage(channel=channel_id, text=text)
            return True
        except Exception:
            logger.exception("Failed to send Slack message to %s", slack_user_id)
            return False
