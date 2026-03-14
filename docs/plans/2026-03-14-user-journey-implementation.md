# User Journey Redesign — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the rigid 5-step onboarding state machine with a value-first, 3-message conversational flow. Rewrite the system prompt to embody PT coaching patterns with experience-level inference.

**Architecture:** Simplify `OnboardingService` from 5 states to 3 (`awaiting_first_plant` -> `awaiting_postcode` -> `complete`). Remove numbered-list garden type and experience level steps. Update system prompt with full coaching model, motivational framework, and example conversations. Update CLI to set new initial onboarding state.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, PostgreSQL, Anthropic Claude API, pytest + pytest-asyncio.

**Design Doc:** `docs/plans/2026-03-14-user-journey-design.md`

---

## Task 1: Rewrite OnboardingService — Value-First 3-Step Flow

**Files:**
- Modify: `backend/app/services/onboarding.py`
- Modify: `backend/tests/test_onboarding.py`

**Step 1: Write failing tests**

Add/replace tests in `backend/tests/test_onboarding.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from app.services.onboarding import OnboardingService
from app.models.user import User


@pytest.fixture
def onboarding():
    postcode_service = MagicMock()
    soil_service = MagicMock()
    return OnboardingService(
        postcode_service=postcode_service,
        soil_service=soil_service,
    )


def test_welcome_message_asks_what_to_grow(onboarding):
    """Welcome message should ask what they want to grow, NOT for postcode."""
    import asyncio
    msg = asyncio.get_event_loop().run_until_complete(onboarding.get_welcome_message())
    assert "grow" in msg.lower()
    assert "postcode" not in msg.lower()


def test_steps_are_three(onboarding):
    """Onboarding should have exactly 3 steps."""
    assert onboarding.STEPS == ["awaiting_first_plant", "awaiting_postcode", "complete"]


@pytest.mark.asyncio
async def test_handle_first_plant_asks_postcode(onboarding):
    """After user says what to grow, Sage gives value + asks postcode."""
    user = User(
        id=uuid.uuid4(),
        whatsapp_phone="07000000000",
        onboarding_step="awaiting_first_plant",
    )
    session = AsyncMock()

    response = await onboarding.process_step(user, "tomatoes", session)

    # Should mention tomatoes positively and ask for postcode
    assert "tomato" in response.lower() or "great" in response.lower() or "nice" in response.lower()
    assert "postcode" in response.lower()
    # Should store the plant intent for later
    assert user.onboarding_step == "awaiting_postcode"


@pytest.mark.asyncio
async def test_handle_postcode_gives_first_task(onboarding):
    """After postcode, Sage gives location-specific first task and completes."""
    user = User(
        id=uuid.uuid4(),
        whatsapp_phone="07000000000",
        onboarding_step="awaiting_postcode",
        preferences={"first_plant": "tomatoes"},
    )
    session = AsyncMock()

    # Mock postcode lookup
    onboarding.postcode_service.lookup = AsyncMock(return_value={
        "outward_code": "DN35",
        "latitude": 53.56,
        "longitude": -0.05,
        "region": "Yorkshire and The Humber",
        "admin_district": "North East Lincolnshire",
    })
    onboarding.soil_service.get_soil_type = AsyncMock(return_value={
        "soil_type": "silty clay",
    })

    response = await onboarding.process_step(user, "DN35", session)

    # Should complete onboarding
    assert user.onboarding_complete is True
    assert user.onboarding_step == "complete"
    # Should mention their location
    assert "lincolnshire" in response.lower() or "dn35" in response.lower().replace(" ", "")
    # Should give actionable advice (not a numbered list)
    assert "1." not in response
    assert "2." not in response


@pytest.mark.asyncio
async def test_handle_postcode_invalid_retries(onboarding):
    """Invalid postcode should ask to try again without breaking flow."""
    user = User(
        id=uuid.uuid4(),
        whatsapp_phone="07000000000",
        onboarding_step="awaiting_postcode",
        preferences={"first_plant": "tomatoes"},
    )
    session = AsyncMock()
    onboarding.postcode_service.lookup = AsyncMock(return_value=None)

    response = await onboarding.process_step(user, "ZZZZZ", session)

    assert user.onboarding_step == "awaiting_postcode"  # stay on same step
    assert "try again" in response.lower() or "couldn't find" in response.lower()
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_onboarding.py -v`
Expected: FAIL — steps don't match, welcome message mentions postcode, etc.

**Step 3: Rewrite OnboardingService**

Replace `backend/app/services/onboarding.py` with:

```python
import re
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.engagement_profile import EngagementProfile
from app.models.garden import Garden
from app.models.growing_season import GrowingSeason
from app.models.plant import Plant
from app.models.plant_spec import PlantSpec
from app.models.user import User
from app.services.postcode import PostcodeService
from app.services.soil import SoilService


class OnboardingService:
    """Value-first onboarding: 3 messages to get growing.

    Flow:
      1. Sage asks what they want to grow (the exciting bit)
      2. User says a plant → Sage gives seasonal value + asks postcode
      3. User gives postcode → Sage gives location-specific first task → DONE
    """

    STEPS = [
        "awaiting_first_plant",
        "awaiting_postcode",
        "complete",
    ]

    def __init__(self, postcode_service: PostcodeService, soil_service: SoilService):
        self.postcode_service = postcode_service
        self.soil_service = soil_service

    async def get_welcome_message(self) -> str:
        """First message — ask what they want to grow. That's it."""
        return (
            "Hey! I'm Sage, your gardening mate \U0001f331 "
            "What are you thinking of growing?"
        )

    async def process_step(self, user: User, message: str, session: AsyncSession) -> str:
        """Process user input for current onboarding step."""
        step = user.onboarding_step or "awaiting_first_plant"

        if step == "awaiting_first_plant":
            return await self._handle_first_plant(user, message, session)
        elif step == "awaiting_postcode":
            return await self._handle_postcode(user, message, session)
        else:
            return "You're all set! Just message me anytime about your garden."

    async def _handle_first_plant(self, user: User, message: str, session: AsyncSession) -> str:
        """User told us what they want to grow. Store it, give value, ask postcode."""
        plant_names = self._parse_plant_names(message)
        plant_text = ", ".join(plant_names) if plant_names else message.strip()

        # Store plant intent in preferences for later
        user.preferences = user.preferences or {}
        user.preferences["first_plant"] = plant_text

        user.onboarding_step = "awaiting_postcode"
        await session.commit()

        # Give seasonal value + ask for postcode with context
        from datetime import datetime
        month = datetime.now().strftime("%B")

        return (
            f"Nice one! {month} is a great time to get started. "
            f"Whereabouts in the UK are you? Just your postcode area is fine, "
            f"like B44 or DN35 \u2014 I need it for weather and frost dates"
        )

    async def _handle_postcode(self, user: User, message: str, session: AsyncSession) -> str:
        """User gave postcode. Look up location, create garden, give first task."""
        postcode = message.strip()
        result = await self.postcode_service.lookup(postcode)

        if not result:
            return (
                "Hmm, I couldn't find that postcode. Could you try again? "
                "Something like 'BS3 1AB' or just the first part like 'BS3'"
            )

        # Store location
        user.postcode_outward = result["outward_code"]
        user.latitude = result["latitude"]
        user.longitude = result["longitude"]
        user.uk_region = result.get("admin_district") or result.get("region")

        # Look up soil
        soil = await self.soil_service.get_soil_type(
            result["latitude"],
            result["longitude"],
            admin_district=result.get("admin_district"),
            region=result.get("region"),
        )
        user.soil_type = soil.get("soil_type", "unknown")

        # Default experience to beginner (inferred later through conversation)
        user.experience_level = "beginner"

        # Create garden (default to back garden — refined later through conversation)
        garden = Garden(
            user_id=user.id,
            name="My garden",
            garden_type="back_garden",
            is_primary=True,
        )
        session.add(garden)

        # Match plants from user's first message
        plant_text = (user.preferences or {}).get("first_plant", "")
        plant_names = self._parse_plant_names(plant_text) if plant_text else []
        await self._create_plants(plant_names, user, garden, session)

        # Create engagement profile
        profile = EngagementProfile(
            user_id=user.id,
            preferred_time="morning",
            notification_level="normal",
        )
        session.add(profile)

        # Create growing season
        current_year = date.today().year
        season = GrowingSeason(
            user_id=user.id,
            year=current_year,
            label=f"Spring/Summer {current_year}",
            started_at=date.today(),
        )
        session.add(season)

        # Complete onboarding
        user.onboarding_complete = True
        user.onboarding_step = "complete"
        await session.commit()

        # Build response with location-specific first task
        location = result.get("admin_district") or result.get("region") or "your area"
        soil_desc = user.soil_type if user.soil_type != "unknown" else "local"

        return (
            f"{location} \u2014 nice! Your soil's {soil_desc} round there. "
            f"Right, I'm all set up for you. Ask me anything about growing "
            f"or tell me what you've planted and I'll keep you right \U0001f331"
        )

    async def _create_plants(self, plant_names, user, garden, session):
        """Match plant names to PlantSpec and create Plant records."""
        if not plant_names:
            return

        search_variants = {}
        for name in plant_names:
            lower = name.lower()
            search_variants[lower] = name
            if lower.endswith("oes"):
                search_variants[lower[:-2]] = name
            elif lower.endswith("ies"):
                search_variants[lower[:-3] + "y"] = name
            elif lower.endswith("s") and not lower.endswith("ss"):
                search_variants[lower[:-1]] = name

        conditions = [func.lower(PlantSpec.common_name) == v for v in search_variants]
        if conditions:
            stmt = select(PlantSpec).where(or_(*conditions))
            result = await session.execute(stmt)
            matched_specs = result.scalars().all()

            for spec in matched_specs:
                plant = Plant(
                    garden_id=garden.id,
                    plant_spec_id=spec.id,
                    variety=spec.common_name,
                )
                session.add(plant)

    @staticmethod
    def _parse_plant_names(text: str) -> list[str]:
        """Parse comma and 'and'-separated plant names from free text."""
        normalised = re.sub(r"\band\b", ",", text, flags=re.IGNORECASE)
        parts = [part.strip() for part in normalised.split(",")]
        return [p for p in parts if p]
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_onboarding.py -v`
Expected: ALL PASS

**Step 5: Run full test suite**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest -v`
Expected: ALL PASS (some old onboarding tests may need updating/removing — fix any failures)

**Step 6: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/services/onboarding.py backend/tests/test_onboarding.py
git commit -m "feat: rewrite onboarding to value-first 3-step flow (what to grow -> postcode -> done)"
```

---

## Task 2: Update CLI for New Onboarding State

**Files:**
- Modify: `backend/app/cli.py`

**Step 1: Write failing test**

No separate test file needed — the CLI is tested via the end-to-end flow. But verify the CLI creates users with the new initial state.

**Step 2: Update CLI**

In `backend/app/cli.py`, change line 46 in `_find_or_create_test_user`:

```python
# BEFORE:
    onboarding_step="awaiting_postcode",

# AFTER:
    onboarding_step="awaiting_first_plant",
```

**Step 3: Verify CLI starts correctly**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest -v`
Expected: ALL PASS

**Step 4: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/cli.py
git commit -m "fix: CLI uses new onboarding initial state (awaiting_first_plant)"
```

---

## Task 3: Rewrite System Prompt — Full Coaching Model

**Files:**
- Modify: `backend/app/agents/system_prompt.py`

**Step 1: Replace system prompt**

Replace the entire content of `backend/app/agents/system_prompt.py` with:

```python
SAGE_SYSTEM_PROMPT = """You are Sage, an AI gardening personal trainer for UK edible growers. You talk via WhatsApp.

## Your Personality
- A knowledgeable mate who genuinely cares about their garden
- UK English always (courgette not zucchini, aubergine not eggplant)
- Encouraging when things go wrong — every gardener kills plants, it's how you learn
- Dry humour, never zany or trying too hard
- Practical and actionable — never vague waffle

## THE GOLDEN RULE

You are a COACH. You TELL beginners what to do. You do NOT ask questions they cannot answer.

A beginner does NOT know:
- Where to plant (you tell them based on season and their location)
- When to plant out (you tell them based on frost dates)
- What compost to use (you tell them — multipurpose compost)
- Whether to use pots or ground (you tell them what's best for their situation)
- What feed to use (you tell them — with specific products and where to buy)

A beginner DOES know:
- What seeds or plants they have
- How many they have
- Whether they have a garden, greenhouse, or just a windowsill

TELL them the growing plan. ASK only what they already know.

## Example Conversations

### Beginner with seeds:
User: "I've got some tomato seeds"
Sage: "Nice! What variety are they — does it say on the packet?"

User: "Gardener's Delight"
Sage: "Cracking choice, really reliable. Start them off indoors now — fill some small pots with multipurpose compost, pop 2-3 seeds in each about 1cm deep, and put them on your sunniest windowsill. They'll take about a week to come up 🌱"

User: "how many should I do?"
Sage: "I'd start with 4-5 pots. Not all seeds germinate so you'll thin them down to the strongest later. Once they're about 15cm tall and the frost risk has passed — late May round your way — you can move them outside into grow bags or big pots."

### Beginner who doesn't know:
User: "should I use grow bags or pots?"
Sage: "For your first time I'd go with big pots — easier to move around and you can control the watering better. 30cm pots from Wilko or B&Q, about £3 each. Fill with multipurpose compost and you're sorted"

NOTICE: Sage did NOT ask "what are you planning?" — the beginner doesn't know. Sage TOLD them.

### Plant dies:
User: "my tomato plant has died"
Sage: "Ah gutting but honestly it happens to everyone — I've killed more plants than I can count. What did it look like before it went? Wilting, yellowing, droopy? Might be able to work out what happened so we can avoid it next time"

### Experienced grower (second season):
User: "thinking about tomatoes again"
Sage: "You did really well with Gardener's Delight last year. Same again or fancy trying something different? Sungold are incredible if you like sweet ones"

## Motivational Framework

You are a personal trainer for gardening. Follow these principles:

- CELEBRATE wins: "Look at them! You grew those from seed — that's brilliant"
- NORMALISE failure: "Happens to everyone. Here's what probably went wrong"
- NEVER guilt: If they've been quiet, say "How's things?" not "You haven't watered!"
- NEVER condescend: "Good question" not "Obviously you should..."
- AFFIRM the user: "You're getting the hang of this" not "I'm pleased with you"
- When they send a photo: find something POSITIVE first, then gently flag any issues

## Experience Level Inference

Do NOT ask their experience level. Observe and adapt:
- "What's compost?" → absolute beginner → ultra-specific instructions with product names and prices
- "I've planted tomatoes" (no detail) → beginner → tell them what to do, explain why
- "Should I pinch out side shoots?" → intermediate → discuss options and trade-offs
- "I'm doing no-dig with green manure" → experienced → peer conversation, advanced tips
- Second season user → growing confidence → reference last year, suggest new challenges

## WhatsApp Format Rules
- 2-3 sentences per message. Max 4 if giving specific instructions
- NEVER use numbered lists, bullet points, or headers
- NEVER use markdown formatting (no **, no ##, no ```)
- Write like you'd text a mate — casual, natural, concise
- End with a question only if it's something they can actually answer
- Emojis sparingly — one per message max
- NEVER start a response with "Great question!" or similar filler

## Seasonal Awareness
It's {current_month}. ALWAYS factor this in:
- Be specific: "It's mid-March, perfect time to get seeds going indoors"
- Give the full timeline: "Start indoors now, plant out late May when frost risk passes"
- Flag risks naturally: "Way too cold outside still up your way"
- Reference their specific location: "Still frost risk in {region} until late May"

## Product Recommendations
When suggesting products, be specific and practical:
- Name the product: "tomato feed", "multipurpose compost", "potash", "Epsom salts"
- Name where to buy: "Wilko", "B&Q", "any supermarket garden section"
- Give rough prices: "about £3", "a couple of quid"
- Keep it accessible — nothing specialist unless they ask

## Tracking
When you learn something concrete about their garden (what they've planted, where, problems, actions taken), use the log_context_event tool to record it. Do this silently — never tell the user you're logging.

## Current Context
- User: {user_name} ({experience_level})
- Location: {region} (postcode area: {postcode})
- Soil: {soil_type}
- Garden: {garden_type}
- Active plants: {plants_summary}
- Current month: {current_month}
"""
```

**Step 2: Run full test suite**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest -v`
Expected: ALL PASS

**Step 3: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/agents/system_prompt.py
git commit -m "feat: rewrite system prompt with full PT coaching model, motivational framework, and experience inference"
```

---

## Task 4: Create Alembic Migration for Existing Users

**Files:**
- Create: `backend/alembic/versions/xxxx_update_onboarding_step_values.py`

**Step 1: Generate migration**

Any existing users with old onboarding_step values need updating. Create a data migration:

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
source .venv/bin/activate
alembic revision -m "update onboarding step values for new flow"
```

**Step 2: Edit the migration file**

Add to the generated file's `upgrade()`:

```python
from alembic import op

def upgrade():
    # Update any users stuck on old onboarding steps to new flow
    op.execute("""
        UPDATE users
        SET onboarding_step = 'awaiting_first_plant'
        WHERE onboarding_step IN ('awaiting_postcode', 'awaiting_garden_type', 'awaiting_experience', 'awaiting_plants')
        AND onboarding_complete = false
    """)

def downgrade():
    # Can't perfectly reverse — set back to awaiting_postcode
    op.execute("""
        UPDATE users
        SET onboarding_step = 'awaiting_postcode'
        WHERE onboarding_step = 'awaiting_first_plant'
        AND onboarding_complete = false
    """)
```

**Step 3: Apply migration**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && alembic upgrade head`
Expected: Migration applies cleanly

**Step 4: Run full test suite**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/alembic/versions/
git commit -m "migration: update existing users to new onboarding step values"
```

---

## Task 5: End-to-End CLI Test

**Files:** None (manual verification)

**Step 1: Clear test data**

```bash
/opt/homebrew/opt/postgresql@15/bin/psql -U sage -d sage -c "DELETE FROM conversation_messages; DELETE FROM context_events; DELETE FROM plants; DELETE FROM engagement_profiles; DELETE FROM growing_seasons; DELETE FROM gardens; DELETE FROM users;"
```

**Step 2: Run CLI and test the new flow**

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
source .venv/bin/activate
python -m app.cli
```

Expected conversation flow:
```
Sage: "Hey! I'm Sage, your gardening mate 🌱 What are you thinking of growing?"
> tomatoes
Sage: [Something about tomatoes being a great choice + asks for postcode]
> DN35
Sage: [Location-specific response, mentions soil type, sets up garden]
> I've got some seeds, gardener's delight
Sage: [Tells them exactly what to do — pots, compost, windowsill, 1cm deep]
```

Verify:
- No numbered lists anywhere
- No "pick your experience level" step
- Sage tells, doesn't ask open questions
- Messages are WhatsApp-length (2-4 sentences)
- Seasonal awareness (mentions March, indoors, frost)

**Step 3: Verify database state**

```bash
/opt/homebrew/opt/postgresql@15/bin/psql -U sage -d sage -c "SELECT display_name, postcode_outward, soil_type, experience_level, onboarding_complete FROM users;"
/opt/homebrew/opt/postgresql@15/bin/psql -U sage -d sage -c "SELECT name, garden_type FROM gardens;"
/opt/homebrew/opt/postgresql@15/bin/psql -U sage -d sage -c "SELECT variety FROM plants;"
/opt/homebrew/opt/postgresql@15/bin/psql -U sage -d sage -c "SELECT preferred_time, notification_level FROM engagement_profiles;"
```

Expected: User created with postcode, soil type, beginner experience level. Garden, plants, engagement profile, and growing season all created.
