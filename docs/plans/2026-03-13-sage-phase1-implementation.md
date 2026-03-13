# Sage Phase 1: WhatsApp MVP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a working WhatsApp chatbot where UK gardeners can message Sage, set up their garden profile, track plants, receive proactive alerts (frost, watering, sowing windows), and get AI-powered gardening advice — all through WhatsApp.

**Architecture:** FastAPI async backend with PostgreSQL (JSONB for flexible state), Redis (Streams for queues, Pub/Sub for events), Claude API (Sonnet) as the AI brain with tool-use pattern for specialist agents, and Meta WhatsApp Cloud API for messaging. Event-driven: webhooks receive messages, ARQ workers process them asynchronously, outbound workers send responses.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2.0 (async/asyncpg), Alembic, PostgreSQL 16, Redis 7+, ARQ, Anthropic Python SDK, Meta WhatsApp Cloud API, Docker Compose, pytest + pytest-asyncio, httpx (async HTTP client).

---

## Task 1: Project Scaffolding & Docker Compose

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `docker-compose.yml`
- Create: `.gitignore`
- Create: `.env.example`

**Step 1: Create project directory structure**

```bash
cd "/Users/nickdavie/2026 Gardening App"
mkdir -p backend/app/core backend/app/models backend/app/api backend/app/agents backend/app/services backend/app/tasks backend/tests
touch backend/app/__init__.py backend/app/core/__init__.py backend/app/models/__init__.py backend/app/api/__init__.py backend/app/agents/__init__.py backend/app/services/__init__.py backend/app/tasks/__init__.py backend/tests/__init__.py
```

**Step 2: Write `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: sage
      POSTGRES_PASSWORD: sage_dev
      POSTGRES_DB: sage
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U sage"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

**Step 3: Write `backend/pyproject.toml`**

```toml
[project]
name = "sage-backend"
version = "0.1.0"
description = "Sage - AI Gardening Companion"
requires-python = ">=3.12"
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
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx>=0.28.0",
    "ruff>=0.8.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
target-version = "py312"
line-length = 120
```

**Step 4: Write `backend/app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://sage:sage_dev@localhost:5432/sage"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Anthropic
    anthropic_api_key: str = ""

    # WhatsApp
    whatsapp_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = "sage-verify-token"
    whatsapp_app_secret: str = ""

    # App
    app_name: str = "Sage"
    debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

**Step 5: Write `backend/app/main.py`**

```python
from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sage"}
```

**Step 6: Write `.env.example` and `.gitignore`**

`.env.example`:
```
DATABASE_URL=postgresql+asyncpg://sage:sage_dev@localhost:5432/sage
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=sk-ant-...
WHATSAPP_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_VERIFY_TOKEN=sage-verify-token
WHATSAPP_APP_SECRET=
```

`.gitignore`:
```
__pycache__/
*.pyc
.env
.venv/
*.egg-info/
dist/
.pytest_cache/
.ruff_cache/
```

**Step 7: Create venv, install deps, start Docker, verify**

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cd ..
docker compose up -d
cd backend
cp ../.env.example .env
uvicorn app.main:app --reload --port 8000 &
sleep 2
curl -s http://localhost:8000/health
kill %1
```

Expected: `{"status":"healthy","service":"sage"}`

**Step 8: Commit**

```bash
git init
git add -A
git commit -m "feat: project scaffolding with FastAPI, Docker Compose (Postgres + Redis)"
```

---

## Task 2: Database Models & Migrations

**Files:**
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/garden.py`
- Create: `backend/app/models/plant.py`
- Create: `backend/app/models/alert.py`
- Create: `backend/app/models/context_event.py`
- Create: `backend/app/models/conversation.py`
- Create: `backend/app/models/achievement.py`
- Create: `backend/app/models/photo_record.py`
- Create: `backend/app/models/plant_spec.py`
- Create: `backend/app/models/growing_calendar.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`

**Step 1: Write `backend/app/core/database.py`**

```python
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

**Step 2: Write all model files**

Each model file defines one SQLAlchemy 2.0 mapped class using `DeclarativeBase`. Follow the data model from the design doc (Section 3.2 — User, Garden, Plant, Alert, ContextEvent, Achievement, PhotoRecord) plus reference data (PlantSpec, GrowingCalendar).

Key conventions:
- All primary keys are UUID, generated server-side with `uuid4`
- All timestamps are `TIMESTAMPTZ`, defaulting to `func.now()`
- JSONB columns use `JSONB` type from `sqlalchemy.dialects.postgresql`
- Enums use `sa.Enum` with Python enum classes
- Foreign keys use `ondelete="CASCADE"` for child tables

The `models/__init__.py` must import all models so Alembic can detect them:

```python
from app.models.user import User
from app.models.garden import Garden
from app.models.plant import Plant
from app.models.alert import Alert
from app.models.context_event import ContextEvent
from app.models.conversation import ConversationMessage
from app.models.achievement import Achievement
from app.models.photo_record import PhotoRecord
from app.models.plant_spec import PlantSpec
from app.models.growing_calendar import GrowingCalendar
```

**Step 3: Initialise Alembic**

```bash
cd backend
source .venv/bin/activate
alembic init alembic
```

Edit `alembic/env.py` to use async engine and import models. Edit `alembic.ini` to reference `DATABASE_URL` from env.

**Step 4: Generate and run first migration**

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

**Step 5: Write a smoke test**

```python
# tests/test_db.py
import pytest
from sqlalchemy import text
from app.core.database import engine


@pytest.fixture
async def db_engine():
    yield engine
    await engine.dispose()


async def test_database_connection(db_engine):
    async with db_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
```

**Step 6: Run test**

```bash
pytest tests/test_db.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add -A
git commit -m "feat: database models and Alembic migrations for all core entities"
```

---

## Task 3: WhatsApp Webhook Endpoint

**Files:**
- Create: `backend/app/api/whatsapp.py`
- Create: `backend/app/services/whatsapp.py`
- Create: `backend/tests/test_whatsapp_webhook.py`
- Modify: `backend/app/main.py`

**Step 1: Write the failing test**

```python
# tests/test_whatsapp_webhook.py
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_webhook_verification(client):
    """Meta sends GET with hub.mode, hub.verify_token, hub.challenge"""
    response = await client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "sage-verify-token",
            "hub.challenge": "test_challenge_string",
        },
    )
    assert response.status_code == 200
    assert response.text == "test_challenge_string"


async def test_webhook_verification_rejects_bad_token(client):
    response = await client.get(
        "/webhook/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "test_challenge_string",
        },
    )
    assert response.status_code == 403


async def test_webhook_receives_message(client):
    """Meta sends POST with message payload. Should return 200 immediately."""
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "123456"},
                    "messages": [{
                        "from": "447700900000",
                        "id": "wamid.test123",
                        "timestamp": "1710000000",
                        "type": "text",
                        "text": {"body": "Hello Sage!"},
                    }],
                },
                "field": "messages",
            }],
        }],
    }
    response = await client.post("/webhook/whatsapp", json=payload)
    assert response.status_code == 200
```

**Step 2: Run tests to verify they fail**

```bash
pytest tests/test_whatsapp_webhook.py -v
```

Expected: FAIL (endpoints don't exist)

**Step 3: Write WhatsApp webhook endpoints**

`backend/app/api/whatsapp.py`:
```python
from fastapi import APIRouter, Query, Request, HTTPException

from app.core.config import settings

router = APIRouter()


@router.get("/webhook/whatsapp")
async def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
):
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return hub_challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhook/whatsapp")
async def receive_webhook(request: Request):
    body = await request.json()
    # Return 200 immediately per Meta's requirement (<15s)
    # Actual processing happens async via Redis queue
    # TODO: enqueue to Redis Streams in Task 5
    return {"status": "ok"}
```

Register in `main.py`:
```python
from app.api.whatsapp import router as whatsapp_router
app.include_router(whatsapp_router)
```

**Step 4: Run tests to verify they pass**

```bash
pytest tests/test_whatsapp_webhook.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: WhatsApp webhook verification and message ingestion endpoint"
```

---

## Task 4: WhatsApp Message Sender Service

**Files:**
- Create: `backend/app/services/whatsapp.py`
- Create: `backend/tests/test_whatsapp_service.py`

**Step 1: Write the failing test**

```python
# tests/test_whatsapp_service.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.whatsapp import WhatsAppService


async def test_send_text_message():
    service = WhatsAppService(token="test-token", phone_number_id="12345")
    with patch.object(service, "_client") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.sent123"}]}
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await service.send_text("447700900000", "Hello from Sage!")
        assert result["messages"][0]["id"] == "wamid.sent123"
        mock_client.post.assert_called_once()


async def test_send_button_message():
    service = WhatsAppService(token="test-token", phone_number_id="12345")
    with patch.object(service, "_client") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"messages": [{"id": "wamid.sent456"}]}
        mock_client.post = AsyncMock(return_value=mock_response)

        result = await service.send_buttons(
            to="447700900000",
            body="Did you cover the beans?",
            buttons=[
                {"id": "yes", "title": "Yes"},
                {"id": "no", "title": "No"},
            ],
        )
        assert result["messages"][0]["id"] == "wamid.sent456"
```

**Step 2: Run to verify failure**

```bash
pytest tests/test_whatsapp_service.py -v
```

**Step 3: Implement `WhatsAppService`**

```python
# backend/app/services/whatsapp.py
import httpx


class WhatsAppService:
    BASE_URL = "https://graph.facebook.com/v21.0"

    def __init__(self, token: str, phone_number_id: str):
        self._token = token
        self._phone_number_id = phone_number_id
        self._client = httpx.AsyncClient(
            base_url=f"{self.BASE_URL}/{phone_number_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def send_text(self, to: str, text: str) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        return response.json()

    async def send_buttons(self, to: str, body: str, buttons: list[dict]) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "button",
                "body": {"text": body},
                "action": {
                    "buttons": [
                        {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                        for b in buttons[:3]
                    ]
                },
            },
        }
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        return response.json()

    async def send_list(self, to: str, body: str, button_text: str, sections: list[dict]) -> dict:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": {
                "type": "list",
                "body": {"text": body},
                "action": {"button": button_text, "sections": sections},
            },
        }
        response = await self._client.post("/messages", json=payload)
        response.raise_for_status()
        return response.json()

    async def download_media(self, media_id: str) -> bytes:
        """Download media file from WhatsApp (for photo analysis)."""
        url_response = await self._client.get(
            f"{self.BASE_URL}/{media_id}",
            headers={"Authorization": f"Bearer {self._token}"},
        )
        url_response.raise_for_status()
        media_url = url_response.json()["url"]

        media_response = await self._client.get(
            media_url, headers={"Authorization": f"Bearer {self._token}"}
        )
        media_response.raise_for_status()
        return media_response.content

    async def close(self):
        await self._client.aclose()
```

**Step 4: Run tests**

```bash
pytest tests/test_whatsapp_service.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: WhatsApp message sending service (text, buttons, lists, media download)"
```

---

## Task 5: Redis Message Queue (Inbound/Outbound)

**Files:**
- Create: `backend/app/services/queue.py`
- Create: `backend/tests/test_queue.py`
- Modify: `backend/app/api/whatsapp.py` (enqueue inbound messages)

**Step 1: Write the failing test**

```python
# tests/test_queue.py
import pytest
import json
from app.services.queue import MessageQueue


@pytest.fixture
async def queue():
    q = MessageQueue(redis_url="redis://localhost:6379")
    await q.connect()
    # Clean test streams
    await q._redis.delete("test:inbound", "test:outbound")
    yield q
    await q.close()


async def test_enqueue_and_dequeue_inbound(queue):
    msg = {"from": "447700900000", "text": "Hello", "message_id": "wamid.123"}
    await queue.enqueue_inbound(msg, stream="test:inbound")

    messages = await queue.dequeue(stream="test:inbound", count=1)
    assert len(messages) == 1
    assert messages[0]["from"] == "447700900000"


async def test_enqueue_outbound(queue):
    msg = {"to": "447700900000", "text": "Hi from Sage!", "type": "text"}
    await queue.enqueue_outbound(msg, stream="test:outbound")

    messages = await queue.dequeue(stream="test:outbound", count=1)
    assert len(messages) == 1
    assert messages[0]["to"] == "447700900000"
```

**Step 2: Run to verify failure**

```bash
pytest tests/test_queue.py -v
```

**Step 3: Implement MessageQueue**

```python
# backend/app/services/queue.py
import json
import redis.asyncio as redis


class MessageQueue:
    INBOUND_STREAM = "sage:inbound"
    OUTBOUND_STREAM = "sage:outbound"

    def __init__(self, redis_url: str):
        self._redis_url = redis_url
        self._redis: redis.Redis | None = None

    async def connect(self):
        self._redis = redis.from_url(self._redis_url, decode_responses=True)

    async def enqueue_inbound(self, message: dict, stream: str | None = None):
        await self._redis.xadd(stream or self.INBOUND_STREAM, {"data": json.dumps(message)})

    async def enqueue_outbound(self, message: dict, stream: str | None = None):
        await self._redis.xadd(stream or self.OUTBOUND_STREAM, {"data": json.dumps(message)})

    async def dequeue(self, stream: str, count: int = 10, block: int = 0) -> list[dict]:
        entries = await self._redis.xread({stream: "0-0"}, count=count, block=block)
        results = []
        for _stream_name, messages in entries:
            for msg_id, fields in messages:
                data = json.loads(fields["data"])
                data["_stream_id"] = msg_id
                results.append(data)
                await self._redis.xdel(stream, msg_id)
        return results

    async def close(self):
        if self._redis:
            await self._redis.aclose()
```

**Step 4: Update webhook to enqueue messages**

In `backend/app/api/whatsapp.py`, update the POST endpoint to parse WhatsApp message format and enqueue.

**Step 5: Run tests**

```bash
pytest tests/test_queue.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: Redis Streams message queue for inbound/outbound WhatsApp messages"
```

---

## Task 6: External API Clients (Weather, Soil, Postcode)

**Files:**
- Create: `backend/app/services/weather.py`
- Create: `backend/app/services/soil.py`
- Create: `backend/app/services/postcode.py`
- Create: `backend/tests/test_weather.py`
- Create: `backend/tests/test_postcode.py`

**Step 1: Write failing tests**

```python
# tests/test_postcode.py
import pytest
from unittest.mock import AsyncMock, patch
from app.services.postcode import PostcodeService


async def test_lookup_postcode():
    service = PostcodeService()
    with patch.object(service, "_client") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "result": {
                "postcode": "BS3 1AB",
                "latitude": 51.4380,
                "longitude": -2.6040,
                "region": "South West",
                "admin_district": "Bristol, City of",
            }
        }
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await service.lookup("BS3 1AB")
        assert result["latitude"] == 51.4380
        assert result["region"] == "South West"
```

**Step 2: Implement all three API clients**

- `PostcodeService`: calls `postcodes.io/postcodes/{postcode}`, returns lat/lng/region
- `WeatherService`: calls Open-Meteo API with lat/lng, returns 7-day forecast, frost risk, rainfall
- `SoilService`: calls BGS API with lat/lng, returns soil type (cached permanently)

Each uses `httpx.AsyncClient`, returns typed dicts, handles errors gracefully.

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: external API clients for weather (Open-Meteo), soil (BGS), postcode (postcodes.io)"
```

---

## Task 7: User Onboarding Service

**Files:**
- Create: `backend/app/services/onboarding.py`
- Create: `backend/tests/test_onboarding.py`
- Modify: `backend/app/models/user.py` (add onboarding_step field)

**Step 1: Write failing tests**

Test the onboarding state machine: new user → ask postcode → ask garden type → ask experience → ask what to grow → complete. Each step validates input and transitions state.

**Step 2: Implement onboarding service**

A state machine that tracks `onboarding_step` (enum: `awaiting_postcode`, `awaiting_garden_type`, `awaiting_experience`, `awaiting_plants`, `complete`). Each step:
1. Validates user input
2. Calls relevant service (postcode lookup, soil lookup)
3. Updates user/garden record
4. Returns Sage's next message

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: user onboarding state machine (postcode → garden → experience → plants)"
```

---

## Task 8: Sage Orchestrator Agent (Claude API + Tool Use)

**Files:**
- Create: `backend/app/agents/orchestrator.py`
- Create: `backend/app/agents/tools.py`
- Create: `backend/app/agents/system_prompt.py`
- Create: `backend/tests/test_orchestrator.py`

**Step 1: Write failing tests**

```python
# tests/test_orchestrator.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.orchestrator import SageOrchestrator


async def test_orchestrator_returns_response():
    """Orchestrator should call Claude API and return a text response."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Happy to help with your tomatoes!")]
    mock_response.stop_reason = "end_turn"
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    orchestrator = SageOrchestrator(client=mock_client)
    result = await orchestrator.chat(
        user_message="When should I plant tomatoes?",
        user_context={"postcode": "BS3", "experience": "beginner", "region": "South West"},
        conversation_history=[],
    )
    assert "tomatoes" in result.lower() or len(result) > 0
```

**Step 2: Implement Sage Orchestrator**

`backend/app/agents/orchestrator.py`:
- Takes user message + context + conversation history
- Builds Claude API call with system prompt (Sage personality) and tool definitions
- Handles tool use loop: if Claude calls a tool, execute it and feed result back
- Returns final text response

`backend/app/agents/system_prompt.py`:
- Sage's personality and instructions (from UX Design doc Section 1)
- UK English, warm, knowledgeable, adaptive to experience level
- Instructions for when to use tools vs answer directly

`backend/app/agents/tools.py`:
- Tool definitions for Claude's tool use: `get_weather_forecast`, `check_frost_risk`, `get_soil_profile`, `get_watering_guidance`, `search_plant_database`, `get_user_garden_state`, `log_context_event`
- Each tool maps to a Python function calling the relevant service

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: Sage orchestrator with Claude API tool use and personality system prompt"
```

---

## Task 9: Message Processing Worker

**Files:**
- Create: `backend/app/tasks/worker.py`
- Create: `backend/app/tasks/process_message.py`
- Create: `backend/tests/test_process_message.py`

**Step 1: Write failing tests**

Test the full pipeline: inbound message → load user → check onboarding state → route to onboarding or orchestrator → generate response → enqueue outbound.

**Step 2: Implement message processing**

`backend/app/tasks/process_message.py`:
1. Parse inbound message from queue
2. Find or create user by phone number
3. If not onboarded → route to onboarding service
4. If onboarded → load context (garden, plants, recent conversations) → call orchestrator
5. Store conversation messages in DB
6. Log context events
7. Enqueue outbound response

`backend/app/tasks/worker.py`:
- ARQ worker config
- Connects to Redis, registers task functions
- Startup/shutdown hooks for DB connections

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: message processing worker (inbound → orchestrator → outbound pipeline)"
```

---

## Task 10: Outbound Message Worker

**Files:**
- Create: `backend/app/tasks/send_message.py`
- Create: `backend/tests/test_send_message.py`

**Step 1: Write failing tests**

Test that outbound worker reads from Redis stream, calls WhatsApp service, handles rate limits and failures with retry.

**Step 2: Implement outbound worker**

Reads from `sage:outbound` stream, formats messages for WhatsApp API, sends via WhatsAppService, handles:
- Rate limiting (token bucket in Redis)
- Retry with exponential backoff (1s, 2s, 4s, max 5 attempts)
- Dead letter queue after max retries
- Delivery status tracking

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: outbound message worker with rate limiting and retry logic"
```

---

## Task 11: Plant Database Seed Data

**Files:**
- Create: `backend/app/data/seed_plants.py`
- Create: `backend/app/data/plants.json`
- Create: `backend/tests/test_seed_data.py`

**Step 1: Create `plants.json`**

JSON file with 50 most popular UK edible plants. Each entry includes:
- common_name, botanical_name, category (vegetable/herb/fruit)
- uk_hardiness, growing_difficulty, soil_preferences
- sun_requirements, water_needs, spacing
- days_to_germination, days_to_harvest
- common_pests, common_diseases
- Regional growing calendar (sow_indoors, sow_outdoors, transplant, harvest months for 4 UK regions: South, Midlands, North, Scotland)

Start with the 20 Tier 1 crops from the QA spec: tomato, courgette, runner bean, broad bean, lettuce, radish, beetroot, carrot, potato, onion, garlic, pea, kale, spinach, chard, strawberry, raspberry, basil, parsley, rosemary.

Plus 30 more: cucumber, pepper, chilli, squash, pumpkin, sweetcorn, leek, spring onion, rocket, French bean, broccoli, cabbage, cauliflower, Brussels sprouts, turnip, parsnip, celeriac, fennel, asparagus, rhubarb, blueberry, gooseberry, blackcurrant, apple (dwarf), mint, thyme, oregano, sage (the herb!), chives, dill.

**Step 2: Write seed script**

`backend/app/data/seed_plants.py`:
- Reads `plants.json`
- Creates PlantSpec records
- Creates GrowingCalendar entries for each plant × region
- Idempotent (skip if already exists)

**Step 3: Write test that seed runs without error**

**Step 4: Run seed**

```bash
python -m app.data.seed_plants
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: seed data for 50 UK edible plants with regional growing calendars"
```

---

## Task 12: Proactive Alert Scheduler

**Files:**
- Create: `backend/app/tasks/alert_scheduler.py`
- Create: `backend/app/services/alerts.py`
- Create: `backend/tests/test_alert_scheduler.py`

**Step 1: Write failing tests**

Test that the scheduler:
- Checks weather for all active users
- Generates frost alerts when temp < 2°C
- Generates watering reminders when no rain forecast and temp > 20°C
- Generates sowing window alerts when plants are due
- Respects user notification preferences (time window)
- Doesn't duplicate alerts

**Step 2: Implement alert scheduler**

`backend/app/services/alerts.py`:
- `check_frost_alerts(users)`: Query weather for each user, create Alert records for those at risk
- `check_watering_reminders(users)`: Based on rainfall and temperature
- `check_sowing_windows(users)`: Compare growing calendar with current month and user's plants
- Each alert generates a context event for the trace

`backend/app/tasks/alert_scheduler.py`:
- ARQ cron job running every 6 hours
- Calls alert services
- Composes messages via Claude (short, personality-consistent)
- Queues to outbound stream

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: proactive alert scheduler (frost, watering, sowing window alerts)"
```

---

## Task 13: Conversation Persistence & Context Loading

**Files:**
- Create: `backend/app/services/conversation.py`
- Create: `backend/tests/test_conversation.py`

**Step 1: Write failing tests**

Test that:
- Messages are stored in ConversationMessage table
- Last 20 messages are loaded for context
- Older messages are available but not loaded by default
- Context loading includes user profile, garden state, active plants, recent alerts

**Step 2: Implement conversation service**

- `store_message(user_id, role, content, metadata)`
- `load_conversation_history(user_id, limit=20)` → returns messages formatted for Claude
- `load_user_context(user_id)` → returns dict with user profile, gardens, plants, recent context events

**Step 3: Run tests, verify pass**

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: conversation persistence and context loading for agent memory"
```

---

## Task 14: Integration Test — Full Message Round-Trip

**Files:**
- Create: `backend/tests/test_integration.py`

**Step 1: Write integration test**

End-to-end test that:
1. Simulates a WhatsApp webhook POST (new user says "Hello")
2. Verifies user record created in DB
3. Verifies onboarding message queued (asks for postcode)
4. Simulates user sends postcode "BS3"
5. Verifies postcode lookup called, soil lookup called
6. Simulates remaining onboarding steps
7. Verifies user marked as onboarded
8. Simulates a garden question
9. Verifies orchestrator called with correct context
10. Verifies response queued

Uses real PostgreSQL and Redis (from Docker Compose), mocks external APIs (Claude, Open-Meteo, BGS, Postcodes.io).

**Step 2: Run integration test**

```bash
pytest tests/test_integration.py -v
```

**Step 3: Commit**

```bash
git add -A
git commit -m "test: full integration test for WhatsApp message round-trip"
```

---

## Task 15: CLI Runner & Local Dev Tooling

**Files:**
- Create: `backend/run.py`
- Create: `backend/app/cli.py`
- Modify: `docker-compose.yml` (add backend service option)
- Create: `Makefile`

**Step 1: Create CLI runner**

```python
# backend/run.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

**Step 2: Create Makefile**

```makefile
.PHONY: dev test migrate seed worker

dev:
	cd backend && source .venv/bin/activate && python run.py

worker:
	cd backend && source .venv/bin/activate && arq app.tasks.worker.WorkerSettings

test:
	cd backend && source .venv/bin/activate && pytest tests/ -v --tb=short

migrate:
	cd backend && source .venv/bin/activate && alembic upgrade head

seed:
	cd backend && source .venv/bin/activate && python -m app.data.seed_plants

up:
	docker compose up -d

down:
	docker compose down
```

**Step 3: Create CLI tool for testing without WhatsApp**

`backend/app/cli.py`:
- Interactive terminal chat with Sage (bypasses WhatsApp, talks directly to orchestrator)
- Creates a test user, simulates conversation
- Useful for development and demo

```bash
python -m app.cli
# > Hello, I want to grow tomatoes in Bristol
# Sage: Welcome! Let's get your garden set up...
```

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: CLI runner, Makefile, and terminal chat for local development"
```

---

## Task 16: Ngrok Setup & WhatsApp Live Test

**Files:**
- Create: `docs/whatsapp-setup.md`

**Step 1: Document WhatsApp Business setup**

Write `docs/whatsapp-setup.md` covering:
1. Create Meta Business account
2. Create WhatsApp Business app
3. Get test phone number and token
4. Set up ngrok tunnel: `ngrok http 8000`
5. Configure webhook URL in Meta dashboard: `https://<ngrok-url>/webhook/whatsapp`
6. Set verify token to match `.env`
7. Send test message from WhatsApp test number

**Step 2: Run live test**

```bash
# Terminal 1: Start services
docker compose up -d
cd backend && source .venv/bin/activate && python run.py

# Terminal 2: Start worker
cd backend && source .venv/bin/activate && arq app.tasks.worker.WorkerSettings

# Terminal 3: Start ngrok
ngrok http 8000
```

Configure Meta webhook with ngrok URL. Send "Hello" from test WhatsApp number. Verify Sage responds with onboarding flow.

**Step 3: Commit**

```bash
git add -A
git commit -m "docs: WhatsApp Business API setup guide for local development"
```

---

## Summary

| Task | What It Builds | Estimated Time |
|------|---------------|----------------|
| 1 | Project scaffolding, Docker Compose | 15 min |
| 2 | Database models, Alembic migrations | 30 min |
| 3 | WhatsApp webhook endpoints | 15 min |
| 4 | WhatsApp message sender service | 20 min |
| 5 | Redis message queue | 20 min |
| 6 | Weather, soil, postcode API clients | 30 min |
| 7 | User onboarding state machine | 30 min |
| 8 | Sage orchestrator (Claude + tools) | 45 min |
| 9 | Inbound message processing worker | 30 min |
| 10 | Outbound message worker | 20 min |
| 11 | Plant database seed data (50 plants) | 45 min |
| 12 | Proactive alert scheduler | 30 min |
| 13 | Conversation persistence & context | 20 min |
| 14 | Integration test (full round-trip) | 30 min |
| 15 | CLI runner & dev tooling | 15 min |
| 16 | WhatsApp live test & docs | 20 min |

**Total estimated: ~6.5 hours of implementation**

After Phase 1 is complete, a UK gardener can:
1. Message Sage on WhatsApp
2. Set up their garden profile through natural conversation
3. Add plants they're growing (up to 5 on free tier)
4. Receive frost warnings, watering reminders, and sowing window alerts
5. Ask any gardening question and get personalised, context-aware advice
6. Have all their interactions, decisions, and observations stored in the context graph

---

*This plan is the single source of truth for Phase 1 implementation. Each task is independent enough to be worked on by a subagent, with integration tests in Task 14 validating the full system.*
