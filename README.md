# Sage - AI Gardening Coach

Sage is an AI-powered personal trainer for UK edible growers. It coaches users through growing vegetables, fruit and herbs via WhatsApp and Slack — providing proactive, weather-aware, location-specific guidance like a knowledgeable friend who genuinely cares about their garden.

## What Sage Does

- **Coaches, doesn't just advise** — tells beginners what to do rather than asking questions they can't answer
- **Proactive check-ins** — messages users when their plants need attention (watering, planting out, frost warnings)
- **Weather-aware milestones** — tracks plant growth stages and gates advice on real local weather data
- **Location-specific** — uses UK postcode for frost dates, soil type, regional sowing windows
- **Accountability tracking** — growing plans, milestone progress, and gentle nudges to keep people on track
- **Adapts to experience** — infers skill level from conversation and adjusts detail accordingly

## Architecture

```
User (WhatsApp / Slack / CLI)
        │
        ▼
  Message Queue (Redis Streams)
        │
        ▼
  SageOrchestrator (Claude AI + Tool Loop)
        │
   ┌────┴────────────────────────┐
   │         Tool Handlers       │
   │  weather · frost · soil     │
   │  plants · calendar · plan   │
   │  milestones · context log   │
   └────┬────────────────────────┘
        │
   ┌────┴──────┐    ┌────────────────┐
   │ PostgreSQL│    │ Open-Meteo API │
   │ (13 models)│   │ (weather data) │
   └───────────┘    └────────────────┘
        ▲
        │
  Background Schedulers (ARQ Cron)
  - Proactive checks (hourly)
  - Weather logging (daily)
  - Alert generation (frost/watering/sowing)
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| AI | Claude (Anthropic) via tool-use orchestration |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 16 |
| Queue | Redis 7 (Streams) |
| Weather | Open-Meteo API (free, no key required) |
| Channels | WhatsApp Business API, Slack Socket Mode, CLI |
| Migrations | Alembic |
| Testing | pytest + pytest-asyncio |

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose (for PostgreSQL + Redis)
- Anthropic API key

### Setup

```bash
# Clone
git clone https://github.com/unkle1976/Sage.git
cd Sage

# Start PostgreSQL and Redis
docker compose up -d

# Set up Python environment
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY

# Run database migrations
alembic upgrade head

# Seed the plant database (50 UK edible plants)
python -m app.data.seed_plants

# Start the API server
uvicorn app.main:app --reload
```

### Try It Out

**CLI chat** (quickest way to test):
```bash
cd backend
python -m app.cli
```

**Slack bot**:
```bash
cd backend
python -m app.slack_bot
```

See [backend/README.md](backend/README.md) for full setup details including WhatsApp and Slack configuration.

## Project Structure

```
Sage/
├── backend/
│   ├── app/
│   │   ├── agents/          # Claude AI orchestrator, tools, system prompt
│   │   ├── api/             # WhatsApp webhook endpoint
│   │   ├── channels/        # Slack Socket Mode integration
│   │   ├── core/            # Config, database connection
│   │   ├── data/            # Plant database (50 species) + milestone data
│   │   ├── models/          # 13 SQLAlchemy models
│   │   ├── services/        # Business logic (11 services)
│   │   └── tasks/           # Background schedulers (proactive checks, alerts)
│   ├── tests/               # 36 test files, 198 tests
│   └── alembic/             # Database migrations
├── docs/
│   └── plans/               # Design documents and implementation plans
└── docker-compose.yml       # PostgreSQL + Redis
```

## Key Features

### Onboarding (3 messages to get growing)
1. "What are you thinking of growing?"
2. User says a plant — Sage gives seasonal context, asks for postcode
3. User gives postcode — Sage sets up location, soil, first task. Done.

### Accountability Coaching
- **Growing plans** — seasonal wishlist with sowing window timing
- **Milestone tracking** — growth stages from seed to harvest with weather gates
- **Proactive messages** — hourly checks for weather alerts, care tasks, engagement
- **Frequency adaptation** — reduces message frequency if user stops responding

### AI Guardrails
- Stays strictly in the gardening domain — won't help with recipes, medical advice, or anything off-topic
- Crisis signposting (Samaritans, SHOUT) if someone mentions distress
- Toxic plant warnings when children or pets are mentioned
- Never identifies wild plants for foraging (safety risk)

### Weather Intelligence
- 7-day forecast from Open-Meteo API
- Frost risk detection (72-hour window)
- Watering guidance based on recent rainfall + forecast
- Weather-gated milestones (won't suggest planting out before frost risk passes)

## Behavioural Psychology

Sage applies established behaviour change frameworks:

- **Fogg Behaviour Model** (B=MAP) — tiny tasks, high motivation, clear prompts
- **Hooked Model** — trigger → action → variable reward → investment loop
- **Self-Determination Theory** — autonomy, competence, relatedness
- **Identity-Based Habits** — "You're a grower now" not "You should garden"
- **Peak-End Rule** — first harvest celebrated memorably

See [docs/plans/2026-03-15-accountability-coaching-design.md](docs/plans/2026-03-15-accountability-coaching-design.md) for the full framework.

## Documentation

| Document | Description |
|----------|-------------|
| [Backend README](backend/README.md) | Setup, configuration, API reference, testing |
| [Sage Design](docs/plans/2026-03-13-sage-design.md) | Product vision, target users, positioning |
| [Phase 1 Implementation](docs/plans/2026-03-13-sage-phase1-implementation.md) | Technical architecture and MVP scope |
| [User Journey](docs/plans/2026-03-14-user-journey-design.md) | UX flows for onboarding and engagement |
| [Plant Intelligence](docs/plans/2026-03-14-cradle-to-grave-plant-intelligence-design.md) | Seed lineage and plant lifecycle tracking |
| [Slack Integration](docs/plans/2026-03-15-slack-integration-design.md) | Multi-channel architecture |
| [Accountability Coaching](docs/plans/2026-03-15-accountability-coaching-design.md) | Psychology framework and engagement design |

## Revenue Model

- **Free tier** — 2 plants, basic weather alerts, community tips
- **Premium (£3.99/mo)** — unlimited plants, full accountability coaching, proactive alerts, growing plans
- **Affiliate revenue** — equipment and supply recommendations with purchase links

## Status

MVP complete as of March 2026. Accountability coaching, multi-channel support (WhatsApp + Slack + CLI), and 198 passing tests.

## License

Proprietary. All rights reserved.
