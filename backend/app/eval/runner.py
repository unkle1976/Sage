"""Conversation runner for Sage evaluation.

Creates a synthetic user (via Claude), runs a multi-turn conversation through
the real Sage system (onboarding + orchestrator), and collects transcripts
for evaluation.
"""

from __future__ import annotations

import logging
import uuid

import anthropic
from sqlalchemy import delete, select

from app.agents.orchestrator import SageOrchestrator
from app.agents.tool_handlers import build_tool_handlers
from app.core.database import async_session
from app.models.alert import Alert
from app.models.context_event import ContextEvent
from app.models.conversation import ConversationMessage
from app.models.engagement_profile import EngagementProfile
from app.models.garden import Garden
from app.models.growing_plan_item import GrowingPlanItem
from app.models.growing_season import GrowingSeason
from app.models.plant import Plant
from app.models.user import User
from app.services.onboarding import OnboardingService
from app.services.postcode import PostcodeService
from app.services.soil import SoilService
from app.services.weather import WeatherService
from app.eval.personas import Persona
from app.eval.evaluator import EvalResult, run_rule_checks, judge_conversation

logger = logging.getLogger(__name__)

SYNTHETIC_MODEL = "claude-sonnet-4-20250514"
HISTORY_LIMIT = 20


async def _load_context(user: User, session) -> dict:
    """Load user context dict for the orchestrator (mirrors slack.py logic)."""
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
    """Load recent conversation history formatted for Claude API (mirrors slack.py)."""
    stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.user_id == user_id)
        .order_by(ConversationMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()
    messages.reverse()

    valid = [m for m in messages if m.content and m.content.strip()]

    merged: list[dict] = []
    for m in valid:
        if merged and merged[-1]["role"] == m.role:
            merged[-1]["content"] += "\n\n" + m.content
        else:
            merged.append({"role": m.role, "content": m.content})

    while merged and merged[0]["role"] != "user":
        merged.pop(0)

    return merged


class EvalRunner:
    """Runs synthetic conversations through the real Sage system."""

    def __init__(self, run_judge: bool = True):
        self._run_judge = run_judge
        from app.core.config import settings
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._weather_service = WeatherService()
        self._soil_service = SoilService()
        self._onboarding = OnboardingService(
            postcode_service=PostcodeService(),
            soil_service=self._soil_service,
        )

    async def run_persona(self, persona: Persona) -> EvalResult:
        """Run a single persona conversation end-to-end."""
        result = EvalResult(
            persona_name=persona.slug,
            turns_completed=0,
            transcript=[],
        )

        user_id = None
        try:
            async with async_session() as session:
                # 1. Create test user
                user = await self._create_test_user(session)
                user_id = user.id
                await session.commit()

                # 2. Get welcome message from onboarding (simulates first contact)
                welcome = await self._onboarding.get_welcome_message()
                session.add(ConversationMessage(
                    user_id=user.id, role="assistant", content=welcome, channel="eval",
                ))
                await session.commit()

                result.transcript.append({
                    "role": "sage", "content": welcome, "turn": 0,
                })
                logger.info("  Turn 0: [SAGE] %s", welcome[:80])

                # 3. Send persona's first_message through onboarding
                turn = 1
                sage_response = await self._process_message_onboarding(
                    user, persona.first_message, session
                )

                # Store both messages
                session.add(ConversationMessage(
                    user_id=user.id, role="user", content=persona.first_message, channel="eval",
                ))
                session.add(ConversationMessage(
                    user_id=user.id, role="assistant", content=sage_response, channel="eval",
                ))
                await session.commit()

                result.transcript.append({
                    "role": "user", "content": persona.first_message, "turn": turn,
                })
                result.transcript.append({
                    "role": "sage", "content": sage_response, "turn": turn,
                })
                logger.info("  Turn %d: [USER] %s", turn, persona.first_message[:80])
                logger.info("  Turn %d: [SAGE] %s", turn, sage_response[:80])
                result.turns_completed = turn

                # 4. Continue conversation — onboarding steps then orchestrator
                # Build conversation history for synthetic user (from its perspective)
                synth_history = [
                    {"role": "user", "content": welcome},  # Sage's welcome -> user role for synth
                    {"role": "assistant", "content": persona.first_message},  # Synth's reply
                    {"role": "user", "content": sage_response},  # Sage's response
                ]

                for turn in range(2, persona.turns + 1):
                    # Generate synthetic user's next message
                    user_message = await self._generate_synthetic_message(
                        persona, synth_history
                    )

                    if not user_message or not user_message.strip():
                        logger.warning("  Turn %d: synthetic user returned empty message, stopping", turn)
                        break

                    # Refresh user to get latest onboarding state
                    await session.refresh(user)

                    # Route through onboarding or orchestrator
                    if not user.onboarding_complete:
                        sage_response = await self._process_message_onboarding(
                            user, user_message, session
                        )
                    else:
                        sage_response = await self._process_message_orchestrator(
                            user, user_message, session
                        )

                    # Guard against empty responses
                    if not sage_response or not sage_response.strip():
                        sage_response = "Noted! What's next on the growing front?"

                    # Persist messages
                    session.add(ConversationMessage(
                        user_id=user.id, role="user", content=user_message, channel="eval",
                    ))
                    session.add(ConversationMessage(
                        user_id=user.id, role="assistant", content=sage_response, channel="eval",
                    ))
                    await session.commit()

                    result.transcript.append({
                        "role": "user", "content": user_message, "turn": turn,
                    })
                    result.transcript.append({
                        "role": "sage", "content": sage_response, "turn": turn,
                    })
                    logger.info("  Turn %d: [USER] %s", turn, user_message[:80])
                    logger.info("  Turn %d: [SAGE] %s", turn, sage_response[:80])
                    result.turns_completed = turn

                    # Update synthetic history
                    synth_history.append({"role": "assistant", "content": user_message})
                    synth_history.append({"role": "user", "content": sage_response})

                # 5. Run rule checks
                await session.refresh(user)
                result.rule_results = await run_rule_checks(
                    user, user.id, session, result.transcript, persona
                )
                result.rule_passed = all(
                    v for k, v in result.rule_results.items()
                    if k in (
                        "onboarding_complete", "plants_created",
                        "no_banned_words", "no_empty_responses", "response_length_ok",
                    )
                )

                # 6. Run judge evaluation
                if self._run_judge:
                    result.judge_scores = await judge_conversation(
                        result.transcript, persona, self._client
                    )
                    if result.judge_scores and "error" not in result.judge_scores:
                        score_keys = ["coaching_style", "tone", "specificity", "flow", "conciseness"]
                        scores = [
                            result.judge_scores.get(k, 0) for k in score_keys
                            if isinstance(result.judge_scores.get(k), (int, float))
                        ]
                        if scores:
                            result.judge_average = sum(scores) / len(scores)

        except Exception as e:
            logger.exception("Error running persona %s", persona.slug)
            result.errors.append(str(e))
        finally:
            # 7. Cleanup test data
            if user_id:
                try:
                    async with async_session() as session:
                        await self._cleanup_test_user(user_id, session)
                        await session.commit()
                except Exception:
                    logger.exception("Error cleaning up test user %s", user_id)

        return result

    async def _create_test_user(self, session) -> User:
        """Create a fresh test user for evaluation."""
        user = User(
            whatsapp_phone=f"eval-{uuid.uuid4().hex[:12]}",
            onboarding_step="awaiting_first_plant",
        )
        session.add(user)
        await session.flush()
        return user

    async def _cleanup_test_user(self, user_id, session) -> None:
        """Delete user and all related data."""
        # Delete in dependency order to avoid FK violations
        # First get garden IDs for this user
        garden_stmt = select(Garden.id).where(Garden.user_id == user_id)
        garden_result = await session.execute(garden_stmt)
        garden_ids = [row[0] for row in garden_result.all()]

        if garden_ids:
            # Delete plants (depend on gardens)
            await session.execute(
                delete(Plant).where(Plant.garden_id.in_(garden_ids))
            )
            # Delete context events referencing gardens
            await session.execute(
                delete(ContextEvent).where(ContextEvent.garden_id.in_(garden_ids))
            )

        # Delete remaining context events for user
        await session.execute(
            delete(ContextEvent).where(ContextEvent.user_id == user_id)
        )
        # Delete alerts
        await session.execute(
            delete(Alert).where(Alert.user_id == user_id)
        )
        # Delete growing plan items
        await session.execute(
            delete(GrowingPlanItem).where(GrowingPlanItem.user_id == user_id)
        )
        # Delete engagement profiles
        await session.execute(
            delete(EngagementProfile).where(EngagementProfile.user_id == user_id)
        )
        # Delete growing seasons
        await session.execute(
            delete(GrowingSeason).where(GrowingSeason.user_id == user_id)
        )
        # Delete conversation messages
        await session.execute(
            delete(ConversationMessage).where(ConversationMessage.user_id == user_id)
        )
        # Delete gardens
        if garden_ids:
            await session.execute(
                delete(Garden).where(Garden.id.in_(garden_ids))
            )
        # Delete user
        await session.execute(
            delete(User).where(User.id == user_id)
        )

    async def _generate_synthetic_message(
        self, persona: Persona, conversation_history: list[dict]
    ) -> str:
        """Call Claude to generate the synthetic user's next message.

        From the synthetic user's perspective:
        - Sage's messages are "user" role (input to respond to)
        - Synthetic user's messages are "assistant" role (what it generates)
        """
        try:
            response = await self._client.messages.create(
                model=SYNTHETIC_MODEL,
                max_tokens=256,
                system=persona.persona_prompt,
                messages=conversation_history,
            )
            text = response.content[0].text.strip()
            return text
        except Exception as e:
            logger.exception("Synthetic user generation failed")
            return ""

    async def _process_message_onboarding(
        self, user: User, message: str, session
    ) -> str:
        """Process a message through the onboarding service."""
        return await self._onboarding.process_step(user, message, session)

    async def _process_message_orchestrator(
        self, user: User, message: str, session
    ) -> str:
        """Process a message through the full Sage orchestrator."""
        tool_handlers = build_tool_handlers(
            user=user,
            session=session,
            weather_service=self._weather_service,
            soil_service=self._soil_service,
        )
        orchestrator = SageOrchestrator(
            client=self._client, tool_handlers=tool_handlers
        )
        user_context = await _load_context(user, session)
        history = await _load_history(user.id, session)
        return await orchestrator.chat(message, user_context, history)
