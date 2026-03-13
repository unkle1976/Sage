"""Proactive alert scheduler — runs periodic checks and enqueues outbound messages."""

import logging

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.models.user import User
from app.services.alerts import AlertService
from app.services.queue import MessageQueue
from app.services.weather import WeatherService

logger = logging.getLogger(__name__)


async def run_alert_checks() -> None:
    """Get all active users, run all alert checks, enqueue outbound messages.

    Can be called by ARQ cron or manually.
    """
    weather = WeatherService()
    queue = MessageQueue(settings.redis_url)

    try:
        await queue.connect()

        async with async_session() as session:
            # Get all onboarded users
            result = await session.execute(
                select(User).where(User.onboarding_complete == True)  # noqa: E712
            )
            users = result.scalars().all()

            if not users:
                logger.info("No active users found, skipping alert checks")
                return

            logger.info("Running alert checks for %d users", len(users))

            svc = AlertService(session, weather)

            # Run all alert check types
            frost_alerts = await svc.check_frost_alerts(users)
            watering_alerts = await svc.check_watering_reminders(users)
            sowing_alerts = await svc.check_sowing_windows(users)

            all_alerts = frost_alerts + watering_alerts + sowing_alerts

            # Build a phone lookup from user_id
            user_phones = {u.id: u.whatsapp_phone for u in users}

            # Enqueue outbound messages for each alert
            for alert in all_alerts:
                phone = user_phones.get(alert.user_id)
                if not phone or not alert.message_content:
                    continue

                await queue.enqueue_outbound({
                    "to": phone,
                    "text": alert.message_content,
                    "type": "text",
                })

            logger.info(
                "Alert checks complete: %d frost, %d watering, %d sowing",
                len(frost_alerts),
                len(watering_alerts),
                len(sowing_alerts),
            )

    finally:
        await weather.close()
        await queue.close()
