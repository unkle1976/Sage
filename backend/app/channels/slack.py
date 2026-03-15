"""Slack channel adapter for Sage — Socket Mode bot."""

from __future__ import annotations

import logging

import anthropic
from slack_bolt.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from sqlalchemy import select

from app.agents.orchestrator import SageOrchestrator
from app.agents.tool_handlers import build_tool_handlers
from app.core.config import settings
from app.core.database import async_session
from app.models.conversation import ConversationMessage
from app.models.garden import Garden
from app.models.plant import Plant
from app.models.user import User
from app.services.onboarding import OnboardingService
from app.services.postcode import PostcodeService
from app.services.soil import SoilService
from app.services.weather import WeatherService

logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20


async def _find_or_create_slack_user(slack_user_id: str, session) -> tuple[User, bool]:
    """Find user by Slack ID, or create a new one for onboarding."""
    stmt = select(User).where(User.slack_user_id == slack_user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is not None:
        return user, False

    user = User(
        whatsapp_phone=f"slack-{slack_user_id}",  # placeholder — not a real phone
        slack_user_id=slack_user_id,
        onboarding_step="awaiting_first_plant",
    )
    session.add(user)
    await session.flush()
    return user, True


async def _load_context(user: User, session) -> dict:
    """Load user context dict for the orchestrator."""
    garden_stmt = select(Garden).where(
        Garden.user_id == user.id, Garden.is_primary.is_(True)
    )
    garden_result = await session.execute(garden_stmt)
    garden = garden_result.scalar_one_or_none()

    plants_summary = "none yet"
    if garden:
        plants_stmt = select(Plant).where(
            Plant.garden_id == garden.id, Plant.is_active.is_(True)
        )
        plants_result = await session.execute(plants_stmt)
        plants = plants_result.scalars().all()
        if plants:
            plants_summary = ", ".join(p.variety for p in plants if p.variety)

    return {
        "display_name": user.display_name or "there",
        "experience_level": user.experience_level or "beginner",
        "region": user.uk_region or "the UK",
        "postcode": user.postcode_outward or "",
        "soil_type": user.soil_type or "unknown",
        "garden_type": garden.garden_type if garden else "garden",
        "plants_summary": plants_summary,
    }


async def _load_history(user_id, session) -> list[dict]:
    """Load recent conversation history formatted for Claude API.

    Merges consecutive same-role messages to avoid Claude API validation errors.
    """
    stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.user_id == user_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()
    messages.reverse()

    # Filter out messages with empty/whitespace-only content (prevents Claude API 400)
    valid = [m for m in messages if m.content and m.content.strip()]

    # Merge consecutive same-role messages (Claude requires alternating roles)
    merged: list[dict] = []
    for m in valid:
        if merged and merged[-1]["role"] == m.role:
            merged[-1]["content"] += "\n\n" + m.content
        else:
            merged.append({"role": m.role, "content": m.content})

    # Claude API requires first message to be role "user" — trim leading assistant messages
    while merged and merged[0]["role"] != "user":
        merged.pop(0)

    return merged


def create_slack_app() -> AsyncApp:
    """Create and configure the Slack Bolt async app."""
    app = AsyncApp(token=settings.slack_bot_token)

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    soil_service = SoilService()
    weather_service = WeatherService()
    onboarding = OnboardingService(
        postcode_service=PostcodeService(),
        soil_service=soil_service,
    )

    @app.event("message")
    async def handle_message(event, say):
        """Handle incoming DM messages."""
        # Ignore bot messages (prevent loops)
        if event.get("bot_id") or event.get("subtype"):
            return

        slack_user_id = event["user"]
        user_text = event.get("text", "").strip()

        if not user_text:
            return

        try:
            async with async_session() as session:
                user, is_new = await _find_or_create_slack_user(slack_user_id, session)

                # Welcome new users — store their triggering message too
                if is_new:
                    welcome = await onboarding.get_welcome_message()
                    session.add(ConversationMessage(
                        user_id=user.id, role="user", content=user_text, channel="slack",
                    ))
                    session.add(ConversationMessage(
                        user_id=user.id, role="assistant", content=welcome, channel="slack",
                    ))
                    await session.commit()
                    await say(welcome)
                    return

                # Refresh user state
                await session.refresh(user)

                # Route: onboarding or orchestrator
                if not user.onboarding_complete:
                    response_text = await onboarding.process_step(user, user_text, session)
                else:
                    tool_handlers = build_tool_handlers(
                        user=user,
                        session=session,
                        weather_service=weather_service,
                        soil_service=soil_service,
                    )
                    orchestrator = SageOrchestrator(client=client, tool_handlers=tool_handlers)
                    user_context = await _load_context(user, session)
                    history = await _load_history(user.id, session)
                    response_text = await orchestrator.chat(user_text, user_context, history)

                # Guard against empty responses (tool-only turns with no text)
                if not response_text or not response_text.strip():
                    response_text = "Got it! 👍"

                # Persist both messages
                session.add(ConversationMessage(
                    user_id=user.id, role="user", content=user_text, channel="slack",
                ))
                session.add(ConversationMessage(
                    user_id=user.id, role="assistant", content=response_text, channel="slack",
                ))
                await session.commit()

                await say(response_text)

        except Exception:
            logger.exception("Error handling Slack message")
            await say("Sorry, I had a bit of a wobble there. Try again? 🌱")

    return app


async def start_slack_bot() -> None:
    """Start the Slack bot with Socket Mode."""
    if not settings.slack_bot_token or not settings.slack_app_token:
        raise RuntimeError(
            "SLACK_BOT_TOKEN and SLACK_APP_TOKEN must be set in .env"
        )

    app = create_slack_app()
    handler = AsyncSocketModeHandler(app, settings.slack_app_token)

    logger.info("Starting Sage Slack bot (Socket Mode)...")
    await handler.start_async()
