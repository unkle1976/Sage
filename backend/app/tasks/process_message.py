"""Inbound message processing pipeline.

Flow: inbound message → find/create user → route (onboarding or orchestrator) → store
conversation → enqueue outbound response.
"""

import logging

import anthropic
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.models.conversation import ConversationMessage
from app.models.garden import Garden
from app.models.plant import Plant
from app.models.user import User
from app.services.onboarding import OnboardingService
from app.services.postcode import PostcodeService
from app.services.queue import MessageQueue
from app.services.soil import SoilService
from app.agents.orchestrator import SageOrchestrator

logger = logging.getLogger(__name__)

# Max recent messages to load as conversation context
HISTORY_LIMIT = 20


def get_onboarding_service() -> OnboardingService:
    """Create an OnboardingService instance."""
    return OnboardingService(
        postcode_service=PostcodeService(),
        soil_service=SoilService(),
    )


def get_orchestrator() -> SageOrchestrator:
    """Create a SageOrchestrator instance."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return SageOrchestrator(client=client)


def get_message_queue() -> MessageQueue:
    """Create a connected MessageQueue instance."""
    return MessageQueue(redis_url=settings.redis_url)


async def process_inbound_message(message_data: dict) -> None:
    """Process a single inbound WhatsApp message through the full pipeline.

    Args:
        message_data: Dict with keys ``from`` (phone), ``text`` (body), ``message_id``.
    """
    phone = message_data["from"]
    text = message_data["text"]
    wa_message_id = message_data.get("message_id")

    queue = get_message_queue()

    async with async_session() as session:
        # 1. Find or create user
        user, is_new = await _find_or_create_user(session, phone)

        # 2. Route based on onboarding state
        if is_new:
            onboarding = get_onboarding_service()
            response_text = await onboarding.get_welcome_message()
        elif not user.onboarding_complete:
            onboarding = get_onboarding_service()
            response_text = await onboarding.process_step(user, text, session)
        else:
            response_text = await _handle_chat(user, text, session)

        # 3. Store conversation messages
        user_msg = ConversationMessage(
            user_id=user.id,
            role="user",
            content=text,
            whatsapp_message_id=wa_message_id,
        )
        session.add(user_msg)

        assistant_msg = ConversationMessage(
            user_id=user.id,
            role="assistant",
            content=response_text,
        )
        session.add(assistant_msg)

        await session.commit()

    # 4. Enqueue outbound response
    await queue.enqueue_outbound({
        "to": phone,
        "text": response_text,
        "type": "text",
    })


async def _find_or_create_user(session, phone: str) -> tuple[User, bool]:
    """Look up a user by phone number, creating one if not found.

    Returns:
        Tuple of (user, is_new).
    """
    stmt = select(User).where(User.whatsapp_phone == phone)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is not None:
        return user, False

    user = User(whatsapp_phone=phone, onboarding_step="awaiting_postcode")
    session.add(user)
    await session.flush()  # Assign id
    return user, True


async def _handle_chat(user: User, text: str, session) -> str:
    """Load context and route to the SageOrchestrator."""
    # Load garden
    garden_stmt = select(Garden).where(Garden.user_id == user.id, Garden.is_primary.is_(True))
    garden_result = await session.execute(garden_stmt)
    garden = garden_result.scalars().first()

    # Load plants
    plants_summary = "none yet"
    if garden:
        plants_stmt = select(Plant).where(Plant.garden_id == garden.id, Plant.is_active.is_(True))
        plants_result = await session.execute(plants_stmt)
        plants = plants_result.scalars().all()
        if plants:
            plants_summary = ", ".join(p.variety for p in plants if p.variety)
    # Load recent conversation history
    conv_stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.user_id == user.id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    conv_result = await session.execute(conv_stmt)
    recent_messages = conv_result.scalars().all()
    # Reverse so oldest first
    recent_messages.reverse()

    conversation_history = [
        {"role": msg.role, "content": msg.content} for msg in recent_messages
    ]

    user_context = {
        "display_name": user.display_name or "there",
        "experience_level": user.experience_level or "beginner",
        "region": user.uk_region or "the UK",
        "postcode": user.postcode_outward or "",
        "soil_type": user.soil_type or "unknown",
        "garden_type": garden.garden_type if garden else "garden",
        "plants_summary": plants_summary,
    }

    orchestrator = get_orchestrator()
    return await orchestrator.chat(text, user_context, conversation_history)
