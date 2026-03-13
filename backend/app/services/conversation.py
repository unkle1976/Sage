"""Conversation persistence and context loading for agent memory.

Stores messages, loads chat history formatted for the Claude API,
and assembles user context for the SageOrchestrator.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import ConversationMessage
from app.models.context_event import ContextEvent
from app.models.garden import Garden
from app.models.plant import Plant
from app.models.user import User


class ConversationService:
    """Manages conversation persistence and user context assembly."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def store_message(
        self,
        user_id: uuid.UUID,
        role: str,
        content: str,
        metadata: dict | None = None,
        whatsapp_message_id: str | None = None,
    ) -> ConversationMessage:
        """Store a conversation message and return it."""
        msg = ConversationMessage(
            user_id=user_id,
            role=role,
            content=content,
            metadata_=metadata,
            whatsapp_message_id=whatsapp_message_id,
        )
        self._session.add(msg)
        await self._session.commit()
        return msg

    async def load_conversation_history(
        self,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> list[dict]:
        """Load the last N messages formatted for the Claude API.

        Returns a list of dicts: [{"role": "user", "content": "..."}, ...]
        ordered chronologically (oldest first).
        """
        stmt = (
            select(ConversationMessage)
            .where(ConversationMessage.user_id == user_id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        messages = result.scalars().all()

        # Reverse to chronological order (query fetched newest first)
        return [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]

    async def load_user_context(self, user_id: uuid.UUID) -> dict:
        """Load user profile, garden, plants, and recent context events.

        Returns the dict expected by SageOrchestrator.chat() as user_context.
        """
        # Fetch user
        user_result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if user is None:
            return {}

        # Fetch primary garden
        garden_result = await self._session.execute(
            select(Garden)
            .where(Garden.user_id == user_id, Garden.is_primary.is_(True))
        )
        garden = garden_result.scalar_one_or_none()

        # Fetch active plants (across all user gardens)
        plants_result = await self._session.execute(
            select(Plant)
            .join(Garden, Plant.garden_id == Garden.id)
            .where(Garden.user_id == user_id, Plant.is_active.is_(True))
        )
        plants = plants_result.scalars().all()

        # Fetch recent context events (last 10)
        events_result = await self._session.execute(
            select(ContextEvent)
            .where(ContextEvent.user_id == user_id)
            .order_by(ContextEvent.created_at.desc())
            .limit(10)
        )
        events = events_result.scalars().all()

        return {
            "display_name": user.display_name,
            "experience_level": user.experience_level,
            "region": user.uk_region,
            "postcode": user.postcode_outward,
            "soil_type": user.soil_type,
            "garden_type": garden.garden_type if garden else None,
            "plants_summary": [
                {
                    "variety": p.variety,
                    "growth_stage": p.growth_stage,
                    "health_status": p.health_status,
                }
                for p in plants
            ],
            "recent_context": [
                {
                    "event_type": e.event_type,
                    "summary": e.summary,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ],
        }
