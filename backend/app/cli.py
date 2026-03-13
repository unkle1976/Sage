"""Interactive terminal chat with Sage — bypasses WhatsApp for local dev/demo.

Usage:
    cd backend && python -m app.cli
"""

import asyncio
import logging
import sys

import anthropic
from sqlalchemy import select

from app.agents.orchestrator import SageOrchestrator
from app.core.config import settings
from app.core.database import async_session
from app.models.conversation import ConversationMessage
from app.models.garden import Garden
from app.models.plant import Plant
from app.models.user import User
from app.services.onboarding import OnboardingService
from app.services.postcode import PostcodeService
from app.services.soil import SoilService

logger = logging.getLogger(__name__)

TEST_PHONE = "00000000000"
HISTORY_LIMIT = 20


async def _find_or_create_test_user(session) -> tuple[User, bool]:
    """Find the CLI test user by phone, or create one."""
    stmt = select(User).where(User.whatsapp_phone == TEST_PHONE)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is not None:
        return user, False

    user = User(
        whatsapp_phone=TEST_PHONE,
        display_name="CLI Tester",
        onboarding_step="awaiting_postcode",
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
    """Load recent conversation history formatted for Claude API."""
    stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.user_id == user_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages]


async def main() -> None:
    """Run the interactive Sage terminal chat."""
    if not settings.anthropic_api_key:
        print("Error: ANTHROPIC_API_KEY is not set. Add it to backend/.env")
        sys.exit(1)

    print("\U0001f331 Sage Terminal Chat (type 'quit' to exit)\n")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    orchestrator = SageOrchestrator(client=client)
    onboarding = OnboardingService(
        postcode_service=PostcodeService(),
        soil_service=SoilService(),
    )

    async with async_session() as session:
        user, is_new = await _find_or_create_test_user(session)

        # Show welcome for brand-new users
        if is_new:
            welcome = await onboarding.get_welcome_message()
            print(f"Sage: {welcome}\n")

            # Store the welcome message
            session.add(ConversationMessage(
                user_id=user.id, role="assistant", content=welcome,
            ))
            await session.commit()

        # Main input loop
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                break

            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                print("Bye!")
                break

            # Refresh user from DB (onboarding may have changed fields)
            await session.refresh(user)

            # Route: onboarding or orchestrator
            if not user.onboarding_complete:
                response_text = await onboarding.process_step(user, user_input, session)
            else:
                user_context = await _load_context(user, session)
                history = await _load_history(user.id, session)
                response_text = await orchestrator.chat(
                    user_input, user_context, history,
                )

            print(f"Sage: {response_text}\n")

            # Persist both messages
            session.add(ConversationMessage(
                user_id=user.id, role="user", content=user_input,
            ))
            session.add(ConversationMessage(
                user_id=user.id, role="assistant", content=response_text,
            ))
            await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
