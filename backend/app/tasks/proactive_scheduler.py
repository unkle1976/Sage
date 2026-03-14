"""Proactive engagement scheduler — runs hourly via ARQ cron.

Checks each active user for triggers (weather, care due, sporadic)
and sends a single bundled WhatsApp message if appropriate.
"""

import logging
from datetime import datetime, timezone

import anthropic
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.models.engagement_profile import EngagementProfile
from app.models.garden import Garden
from app.models.plant import Plant
from app.models.user import User
from app.services.engagement import EngagementService
from app.services.proactive import ProactiveMessageBuilder
from app.services.queue import MessageQueue
from app.services.weather import WeatherService

logger = logging.getLogger(__name__)


async def run_proactive_checks() -> None:
    """Hourly check: for each active user, evaluate triggers and send messages."""
    weather = WeatherService()
    queue = MessageQueue(settings.redis_url)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        await queue.connect()

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.onboarding_complete == True)  # noqa: E712
            )
            users = result.scalars().all()

            if not users:
                logger.info("No active users, skipping proactive checks")
                return

            now = datetime.now(timezone.utc)

            for user in users:
                try:
                    await _process_user(user, session, weather, queue, client, now)
                except Exception:
                    logger.exception("Failed proactive check for user %s", user.id)

    finally:
        await weather.close()
        await queue.close()
        await client.close()


async def _process_user(user, session, weather, queue, client, now):
    """Evaluate all triggers for a single user and send message if appropriate."""
    ep_result = await session.execute(
        select(EngagementProfile).where(EngagementProfile.user_id == user.id)
    )
    profile = ep_result.scalar_one_or_none()

    if not profile:
        return

    current_time = now.time()
    if EngagementService.is_quiet_hours(current_time, profile.quiet_hours_start, profile.quiet_hours_end):
        return

    last_contact = max(
        filter(None, [profile.last_sage_initiated_at, profile.last_user_message_at]),
        default=None,
    )
    days_since = (now - last_contact).days if last_contact else 999

    triggers = {"weather_alerts": [], "care_due": [], "growth_updates": []}

    if user.latitude and user.longitude:
        try:
            frost = await weather.check_frost_risk(float(user.latitude), float(user.longitude))
            if frost.get("frost_risk"):
                triggers["weather_alerts"].append({
                    "type": "frost",
                    "min_temp": frost.get("min_temperature"),
                })
        except Exception:
            logger.warning("Weather check failed for user %s", user.id)

    has_urgent = bool(triggers["weather_alerts"])
    has_timely = bool(triggers["care_due"] or triggers["growth_updates"])
    should_sporadic = EngagementService.should_send_sporadic(days_since, now.month)

    if not has_urgent and not has_timely and not should_sporadic:
        return

    if profile.notification_level == "alerts_only" and not has_urgent:
        return

    garden_result = await session.execute(
        select(Garden).where(Garden.user_id == user.id, Garden.is_primary.is_(True))
    )
    garden = garden_result.scalar_one_or_none()

    plants_data = []
    if garden:
        plants_result = await session.execute(
            select(Plant).where(Plant.garden_id == garden.id, Plant.is_active.is_(True))
        )
        plants = plants_result.scalars().all()
        plants_data = [
            {"variety": p.variety, "growth_stage": p.growth_stage, "planting_date": str(p.planting_date)}
            for p in plants
        ]

    plant_summary = ProactiveMessageBuilder.build_plant_summary(plants_data)
    trigger_context = ProactiveMessageBuilder.build_trigger_context(triggers)
    system_instruction = ProactiveMessageBuilder.build_system_instruction(
        trigger_context=trigger_context,
        plant_summary=plant_summary,
        user_name=user.display_name or "there",
        experience_level=user.experience_level or "beginner",
    )

    response = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=300,
        messages=[{"role": "user", "content": "Generate the proactive message now."}],
        system=system_instruction,
    )

    message_text = response.content[0].text

    await queue.enqueue_outbound({
        "to": user.whatsapp_phone,
        "text": message_text,
        "type": "text",
    })

    profile.last_sage_initiated_at = now
    await session.commit()

    logger.info("Sent proactive message to user %s", user.id)
