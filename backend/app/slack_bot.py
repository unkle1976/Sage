"""Run the Sage Slack bot.

Usage:
    cd backend && python -m app.slack_bot
"""

import asyncio
import logging
import sys

from app.core.config import settings
from app.channels.slack import start_slack_bot

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


def main():
    if not settings.slack_bot_token:
        print("Error: SLACK_BOT_TOKEN is not set. Add it to backend/.env")
        sys.exit(1)
    if not settings.slack_app_token:
        print("Error: SLACK_APP_TOKEN is not set. Add it to backend/.env")
        sys.exit(1)

    print("\U0001f331 Sage Slack Bot starting (Socket Mode)...")
    print("Send a DM to the Sage bot in Slack to chat.\n")

    asyncio.run(start_slack_bot())


if __name__ == "__main__":
    main()
