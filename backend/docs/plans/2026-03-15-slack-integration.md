# Slack Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a Slack bot (Socket Mode) so Nick can chat with Sage from the Slack mobile app, using the same orchestrator and onboarding flow as the CLI.

**Architecture:** Slack Bolt app with Socket Mode connects outbound from the laptop to Slack's servers. Messages are routed through the existing SageOrchestrator. User records map via `slack_user_id` column. Conversation history gets a `channel` column so we can distinguish CLI/Slack/WhatsApp messages.

**Tech Stack:** slack-bolt (includes slack-sdk), SQLAlchemy 2.x async, Alembic, existing SageOrchestrator + OnboardingService

---

### Task 1: Add slack-bolt dependency

**Files:**
- Modify: `pyproject.toml:6-20`

**Step 1: Add slack-bolt to dependencies**

In `pyproject.toml`, add `"slack-bolt>=1.20.0"` to the `dependencies` list:

```toml
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "sqlalchemy[asyncio]>=2.0.36",
    "asyncpg>=0.30.0",
    "alembic>=1.14.0",
    "pydantic>=2.10.0",
    "pydantic-settings>=2.7.0",
    "redis>=5.2.0",
    "arq>=0.26.1",
    "anthropic>=0.42.0",
    "httpx>=0.28.0",
    "python-dotenv>=1.0.1",
    "greenlet>=3.1.0",
    "slack-bolt>=1.20.0",
]
```

**Step 2: Install**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && source .venv/bin/activate && pip install -e .`
Expected: slack-bolt and slack-sdk installed successfully

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat: add slack-bolt dependency for Slack channel integration"
```

---

### Task 2: Add Slack config settings

**Files:**
- Modify: `app/core/config.py:9-28`

**Step 1: Write the failing test**

Create `tests/test_slack_config.py`:

```python
"""Tests for Slack configuration settings."""
import os

def test_slack_settings_loaded_from_env(monkeypatch):
    """Slack tokens should be read from environment."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setenv("SLACK_APP_TOKEN", "xapp-test-token")

    # Re-import to pick up env vars
    from pydantic_settings import BaseSettings
    from app.core.config import Settings

    s = Settings()
    assert s.slack_bot_token == "xoxb-test-token"
    assert s.slack_app_token == "xapp-test-token"


def test_slack_settings_default_empty():
    """Slack tokens should default to empty strings."""
    # Clear any existing env vars
    from app.core.config import Settings

    # Create settings without slack env vars set
    s = Settings(slack_bot_token="", slack_app_token="")
    assert s.slack_bot_token == ""
    assert s.slack_app_token == ""
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && source .venv/bin/activate && python -m pytest tests/test_slack_config.py -v`
Expected: FAIL — `Settings` has no field `slack_bot_token`

**Step 3: Add Slack settings to config**

In `app/core/config.py`, add after the WhatsApp settings block:

```python
    # Slack
    slack_bot_token: str = ""
    slack_app_token: str = ""
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_slack_config.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/core/config.py tests/test_slack_config.py
git commit -m "feat: add Slack token settings to config"
```

---

### Task 3: Add `channel` column to ConversationMessage and `slack_user_id` to User

**Files:**
- Modify: `app/models/conversation.py`
- Modify: `app/models/user.py`
- Create: new Alembic migration

**Step 1: Write the failing test**

Create `tests/test_slack_models.py`:

```python
"""Tests for Slack-related model changes."""
import uuid
from app.models.conversation import ConversationMessage
from app.models.user import User


def test_conversation_message_has_channel_field():
    """ConversationMessage should have a channel column defaulting to 'cli'."""
    msg = ConversationMessage(
        user_id=uuid.uuid4(),
        role="user",
        content="hello",
    )
    assert msg.channel == "cli"


def test_conversation_message_channel_can_be_set():
    """ConversationMessage channel can be set to slack."""
    msg = ConversationMessage(
        user_id=uuid.uuid4(),
        role="user",
        content="hello",
        channel="slack",
    )
    assert msg.channel == "slack"


def test_user_has_slack_user_id_field():
    """User should have a slack_user_id column defaulting to None."""
    user = User(whatsapp_phone="00000000000")
    assert user.slack_user_id is None


def test_user_slack_user_id_can_be_set():
    """User slack_user_id can be set."""
    user = User(whatsapp_phone="00000000000", slack_user_id="U1234567890")
    assert user.slack_user_id == "U1234567890"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_slack_models.py -v`
Expected: FAIL — no `channel` attribute on ConversationMessage

**Step 3: Add channel column to ConversationMessage**

In `app/models/conversation.py`, add after the `whatsapp_message_id` line:

```python
    channel: Mapped[str] = mapped_column(String(20), default="cli")  # cli, slack, whatsapp
```

**Step 4: Add slack_user_id column to User**

In `app/models/user.py`, add after the `whatsapp_phone` line:

```python
    slack_user_id: Mapped[str | None] = mapped_column(String(30), unique=True, index=True)
```

**Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_slack_models.py -v`
Expected: PASS

**Step 6: Generate Alembic migration**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && source .venv/bin/activate && alembic revision --autogenerate -m "add channel to conversation_messages and slack_user_id to users"`
Expected: New migration file created

**Step 7: Apply migration**

Run: `alembic upgrade head`
Expected: Migration applied successfully

**Step 8: Run full test suite**

Run: `python -m pytest -v`
Expected: All tests pass (existing + new)

**Step 9: Commit**

```bash
git add app/models/conversation.py app/models/user.py alembic/versions/ tests/test_slack_models.py
git commit -m "feat: add channel column to messages, slack_user_id to users"
```

---

### Task 4: Build the Slack channel adapter

This is the core of the integration. It mirrors the CLI's message loop but receives from Slack instead of stdin.

**Files:**
- Create: `app/channels/__init__.py`
- Create: `app/channels/slack.py`

**Step 1: Write the failing test**

Create `tests/test_slack_channel.py`:

```python
"""Tests for the Slack channel adapter."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.channels.slack import _find_or_create_slack_user, _load_context, _load_history


@pytest.fixture
def mock_session():
    """Create a mock async session."""
    session = AsyncMock()
    return session


class TestFindOrCreateSlackUser:
    """Tests for Slack user lookup/creation."""

    @pytest.mark.asyncio
    async def test_returns_existing_user(self, mock_session):
        """Should return existing user when slack_user_id matches."""
        existing_user = MagicMock()
        existing_user.slack_user_id = "U123"
        existing_user.onboarding_step = "complete"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute.return_value = mock_result

        user, is_new = await _find_or_create_slack_user("U123", mock_session)

        assert user == existing_user
        assert is_new is False

    @pytest.mark.asyncio
    async def test_creates_new_user_when_not_found(self, mock_session):
        """Should create a new user when no slack_user_id match."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        user, is_new = await _find_or_create_slack_user("U999", mock_session)

        assert is_new is True
        assert user.slack_user_id == "U999"
        assert user.onboarding_step == "awaiting_first_plant"
        mock_session.add.assert_called_once()
        mock_session.flush.assert_awaited_once()
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_slack_channel.py -v`
Expected: FAIL — cannot import `app.channels.slack`

**Step 3: Create the channel adapter**

Create `app/channels/__init__.py` (empty file).

Create `app/channels/slack.py`:

```python
"""Slack channel adapter for Sage — Socket Mode bot.

Usage:
    cd backend && python -m app.slack_bot
"""

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


# ── User lookup ──────────────────────────────────────────────────────────

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


# ── Context loading (same as CLI) ───────────────────────────────────────

HISTORY_LIMIT = 20


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


# ── Slack app factory ────────────────────────────────────────────────────

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

        async with async_session() as session:
            user, is_new = await _find_or_create_slack_user(slack_user_id, session)

            # Welcome new users
            if is_new:
                welcome = await onboarding.get_welcome_message()
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

            # Persist both messages
            session.add(ConversationMessage(
                user_id=user.id, role="user", content=user_text, channel="slack",
            ))
            session.add(ConversationMessage(
                user_id=user.id, role="assistant", content=response_text, channel="slack",
            ))
            await session.commit()

            await say(response_text)

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
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_slack_channel.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/channels/__init__.py app/channels/slack.py tests/test_slack_channel.py
git commit -m "feat: add Slack channel adapter with Socket Mode"
```

---

### Task 5: Create the Slack bot entry point

**Files:**
- Create: `app/slack_bot.py`

**Step 1: Create the entry point**

Create `app/slack_bot.py`:

```python
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
```

**Step 2: Verify it starts (manual test)**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && source .venv/bin/activate && python -m app.slack_bot`
Expected: "Sage Slack Bot starting (Socket Mode)..." printed, bot connects to Slack. Then Ctrl+C to stop.

**Step 3: Commit**

```bash
git add app/slack_bot.py
git commit -m "feat: add Slack bot entry point (python -m app.slack_bot)"
```

---

### Task 6: Run full test suite and verify

**Step 1: Run all tests**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && source .venv/bin/activate && python -m pytest -v`
Expected: All tests pass (existing 131 + new Slack tests)

**Step 2: Fix any failures**

If any existing tests fail due to the new `channel` or `slack_user_id` columns, update them to account for the new defaults.

**Step 3: Commit any fixes**

```bash
git add -A
git commit -m "fix: update tests for Slack integration model changes"
```

---

### Task 7: Manual end-to-end test

**Step 1: Ensure PostgreSQL is running**

Run: `brew services start postgresql@15`

**Step 2: Apply migration**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && source .venv/bin/activate && alembic upgrade head`

**Step 3: Start the Slack bot**

Run: `python -m app.slack_bot`

**Step 4: Test from Slack**

1. Open Slack (phone or desktop)
2. Find the Sage bot in DMs
3. Send "hello" — should get the welcome message
4. Send "tomatoes" — should get the seasonal value + postcode question
5. Send "DN35" — should complete onboarding with location info
6. Send "I've got some tomato seeds" — should get coaching response from Sage
7. Check PostgreSQL: `SELECT * FROM conversation_messages WHERE channel = 'slack';`

**Step 5: Final commit if needed**

```bash
git add -A
git commit -m "feat: Slack integration complete — Phase 1"
```
