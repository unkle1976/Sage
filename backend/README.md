# Sage Backend

FastAPI backend for Sage, the AI gardening coach. Handles message processing, AI orchestration, weather intelligence, and proactive scheduling.

## Setup

### 1. Infrastructure

```bash
# From the repo root
docker compose up -d
```

This starts:
- **PostgreSQL 16** on port 5432 (user: `sage`, password: `sage_dev`, database: `sage`)
- **Redis 7** on port 6379

### 2. Python Environment

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires Python 3.12+.

### 3. Environment Variables

Copy and edit the environment file:

```bash
cp .env.example .env
```

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `REDIS_URL` | Yes | Redis connection string |
| `ANTHROPIC_API_KEY` | Yes | Claude API key from Anthropic |
| `WHATSAPP_TOKEN` | For WhatsApp | Meta WhatsApp Business API token |
| `WHATSAPP_PHONE_NUMBER_ID` | For WhatsApp | WhatsApp phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | For WhatsApp | Webhook verification token (you choose this) |
| `WHATSAPP_APP_SECRET` | For WhatsApp | Meta app secret for signature verification |
| `SLACK_BOT_TOKEN` | For Slack | Slack bot OAuth token (xoxb-...) |
| `SLACK_APP_TOKEN` | For Slack | Slack app-level token for Socket Mode (xapp-...) |
| `SQL_ECHO` | No | Set to `true` to log SQL queries (default: false) |
| `DEBUG` | No | Debug mode (default: false) |

### 4. Database

```bash
# Run migrations
alembic upgrade head

# Seed the plant database (50 UK edible plants with growing calendars)
python -m app.data.seed_plants
```

### 5. Run

**API server:**
```bash
uvicorn app.main:app --reload
```

**CLI chat** (no WhatsApp/Slack needed):
```bash
python -m app.cli
```

**Slack bot:**
```bash
python -m app.slack_bot
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/webhook/whatsapp` | Meta webhook verification |
| `POST` | `/webhook/whatsapp` | Receive WhatsApp messages |

## Architecture

### Models (13)

| Model | Description |
|-------|-------------|
| `User` | Gardener profile — location, soil type, experience level, subscription tier |
| `Garden` | Physical garden — type (back garden, allotment, balcony), size, orientation |
| `Plant` | Individual plant instance — growth stage, health, milestone tracking |
| `PlantSpec` | Species reference — 50 UK edibles with growing requirements and milestones |
| `GrowingCalendar` | Regional sowing/harvest windows per plant (South, Midlands, North, Scotland) |
| `GrowingPlanItem` | User's seasonal wishlist — queued, ready, active, or skipped |
| `GrowingSeason` | Annual season record with weather summary |
| `ConversationMessage` | Chat history — role, content, channel (cli/slack/whatsapp) |
| `ContextEvent` | Decision traces — event type, reasoning, weather snapshot, confidence |
| `Alert` | Proactive notifications — frost, watering, sowing reminders |
| `EngagementProfile` | Notification preferences — quiet hours, frequency, unanswered count |
| `WeatherLog` | Daily weather cache per postcode |
| `Achievement` | Badges and rewards (bronze/silver/gold) |

### Services (11)

| Service | What It Does |
|---------|-------------|
| `OnboardingService` | 3-step signup: what to grow → postcode → ready |
| `ConversationService` | Stores messages, loads history formatted for Claude API |
| `WeatherService` | Open-Meteo API — forecast, frost risk, watering guidance |
| `AlertService` | Generates frost, watering, and sowing window alerts |
| `GrowingPlanService` | Checks sowing window timing, prioritises by date |
| `MilestoneChecker` | Evaluates which plants are due for their next growth milestone |
| `EngagementService` | Calculates message frequency and respects quiet hours |
| `ProactiveMessageBuilder` | Assembles context for proactive Claude messages |
| `PostcodeService` | UK postcode → lat/lon, region, admin district |
| `SoilService` | Regional soil type lookup |
| `MessageQueue` | Redis Streams for async message processing |

### Agent Tools (9)

The SageOrchestrator gives Claude access to these tools during conversation:

| Tool | Description |
|------|-------------|
| `get_weather_forecast` | 7-day forecast for user's location |
| `check_frost_risk` | Next 72-hour frost detection |
| `get_watering_guidance` | Should they water today? |
| `get_soil_profile` | Soil composition for their area |
| `search_plant_database` | Full-text search across 50 plant species |
| `get_growing_calendar` | What to sow/harvest this month regionally |
| `log_context_event` | Record a significant gardening event |
| `manage_growing_plan` | Add/list/activate items in seasonal wishlist |
| `advance_milestone` | Record plant reaching next growth stage |

### Background Tasks

| Task | Frequency | Description |
|------|-----------|-------------|
| `run_proactive_checks` | Hourly | Check all users for milestone due dates, weather alerts, care tasks |
| `run_alert_checks` | Hourly | Generate frost/watering/sowing alerts |
| `run_weather_logger` | Daily | Cache weather data from Open-Meteo for all active postcodes |
| `process_inbound_message` | On demand | Process queued WhatsApp messages |
| `send_message` | On demand | Send queued outbound messages via WhatsApp API |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run a specific test file
pytest tests/test_onboarding.py

# Run tests matching a pattern
pytest -k "milestone"
```

198 tests across 36 test files. Tests use async fixtures and mock the Claude API.

## Project Layout

```
backend/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py      # Claude AI with tool-use loop
│   │   ├── system_prompt.py     # Sage personality, rules, guardrails
│   │   ├── tools.py             # Tool definitions (JSON schemas)
│   │   └── tool_handlers.py     # Tool implementations
│   ├── api/
│   │   └── whatsapp.py          # WhatsApp webhook (GET verify + POST messages)
│   ├── channels/
│   │   ├── slack.py             # Slack Socket Mode listener
│   │   └── slack_sender.py      # Outbound Slack DMs for proactive messages
│   ├── core/
│   │   ├── config.py            # Pydantic settings from .env
│   │   └── database.py          # Async SQLAlchemy engine + session factory
│   ├── data/
│   │   ├── plants.json          # 50 UK edible plants with full growing data
│   │   ├── plant_milestones.py  # Growth stage timelines with weather gates
│   │   └── seed_plants.py       # Database seeder
│   ├── models/
│   │   ├── user.py              # User profile
│   │   ├── garden.py            # Garden instances
│   │   ├── plant.py             # Plant instances with milestone tracking
│   │   ├── plant_spec.py        # Species reference data
│   │   ├── growing_calendar.py  # Regional sowing/harvest windows
│   │   ├── growing_plan_item.py # Seasonal wishlist
│   │   ├── growing_season.py    # Annual season tracking
│   │   ├── conversation.py      # Chat messages
│   │   ├── context_event.py     # Decision trace / context graph
│   │   ├── alert.py             # Proactive notifications
│   │   ├── engagement_profile.py # Notification preferences
│   │   ├── weather_log.py       # Daily weather cache
│   │   └── achievement.py       # Badges and rewards
│   ├── services/
│   │   ├── onboarding.py        # 3-step value-first signup
│   │   ├── conversation.py      # Message persistence + history loading
│   │   ├── weather.py           # Open-Meteo API client
│   │   ├── alert.py             # Alert generation logic
│   │   ├── growing_plan.py      # Sowing window checks + prioritisation
│   │   ├── milestone_checker.py # Growth milestone evaluation
│   │   ├── engagement.py        # Frequency + quiet hours
│   │   ├── proactive.py         # Context builder for proactive messages
│   │   ├── postcode.py          # UK postcode lookup
│   │   ├── soil.py              # Regional soil data
│   │   └── queue.py             # Redis Streams message queue
│   ├── tasks/
│   │   ├── proactive_scheduler.py # Hourly proactive check-ins
│   │   ├── alert_scheduler.py     # Alert generation scheduler
│   │   ├── weather_logger.py      # Daily weather caching
│   │   ├── process_message.py     # Inbound message processor
│   │   └── send_message.py        # Outbound message sender
│   ├── cli.py                   # Terminal chat interface
│   ├── main.py                  # FastAPI app entry point
│   └── slack_bot.py             # Slack Socket Mode entry point
├── tests/                       # 36 test files
├── alembic/                     # Database migrations (5 versions)
├── pyproject.toml               # Dependencies and tool config
└── .env                         # Environment variables (not committed)
```

## Database Migrations

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description of changes"

# Check current migration state
alembic current

# Rollback one migration
alembic downgrade -1
```

## WhatsApp Setup

See [docs/whatsapp-setup.md](docs/whatsapp-setup.md) for Meta Business Platform configuration including:
- App creation and webhook setup
- Phone number registration
- Token generation
- Webhook URL configuration (requires HTTPS — use ngrok for local dev)

## Slack Setup

1. Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps)
2. Enable **Socket Mode** and generate an app-level token (`xapp-...`)
3. Add bot scopes: `chat:write`, `im:history`, `im:read`, `im:write`
4. Install to workspace and copy the bot token (`xoxb-...`)
5. Add both tokens to `.env`
6. Run `python -m app.slack_bot`

## Channel Architecture

All channels (WhatsApp, Slack, CLI) feed into the same orchestrator:

```
Channel → find_or_create_user → route (onboarding or orchestrator) → store messages → respond
```

Each channel adapter handles:
- User identity mapping (phone number, Slack user ID, or CLI session)
- Message format conversion
- Response delivery

The `ConversationMessage` model tracks which channel each message came from.
