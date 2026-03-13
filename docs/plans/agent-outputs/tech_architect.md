

# Sage — Technical Architecture

## 1. System Architecture Overview

Sage is a multi-layered, event-driven system built around a conversational AI core. The architecture separates concerns cleanly: message ingestion, agent orchestration, domain intelligence, and data persistence each operate independently, connected through an asynchronous message broker.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                    │
│                                                                         │
│   ┌──────────────┐              ┌──────────────────────┐               │
│   │   WhatsApp    │              │  React Native App    │               │
│   │  (Phase 1)    │              │     (Phase 2)        │               │
│   └──────┬───────┘              └──────────┬───────────┘               │
│          │                                  │                           │
│          │  Webhooks                        │  REST + WebSocket         │
└──────────┼──────────────────────────────────┼───────────────────────────┘
           │                                  │
           ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                                    │
│                                                                         │
│   ┌──────────────────────────────────────────────────────────┐         │
│   │              FastAPI Gateway                              │         │
│   │  • WhatsApp webhook verification & message parsing        │         │
│   │  • REST API for mobile app (Phase 2)                      │         │
│   │  • WebSocket for real-time chat (Phase 2)                 │         │
│   │  • Rate limiting, authentication, request validation      │         │
│   └──────────────────────┬───────────────────────────────────┘         │
│                          │                                              │
│                          ▼                                              │
│   ┌──────────────────────────────────────────────────────────┐         │
│   │              Message Broker (Redis Streams)               │         │
│   │  • Inbound message queue                                  │         │
│   │  • Agent task queue                                       │         │
│   │  • Outbound message queue                                 │         │
│   │  • Scheduled alert queue                                  │         │
│   └──────────────────────┬───────────────────────────────────┘         │
└──────────────────────────┼──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   AGENT ORCHESTRATION LAYER                             │
│                                                                         │
│   ┌──────────────────────────────────────────────────────────┐         │
│   │            Sage Orchestrator (Claude API)                 │         │
│   │  • Conversational interface & personality                 │         │
│   │  • Intent classification & routing                        │         │
│   │  • Response synthesis from specialist agents              │         │
│   │  • Context management & memory                            │         │
│   └────────────┬─────────────────────────────────────────────┘         │
│                │                                                        │
│                ▼                                                        │
│   ┌────────┐ ┌────────┐ ┌────────┐ ┌─────────┐ ┌──────────┐          │
│   │Weather │ │  Soil  │ │  Pest/ │ │ Harvest │ │ Planning │          │
│   │ Agent  │ │ Agent  │ │Disease │ │  Agent  │ │  Agent   │          │
│   │        │ │        │ │ Agent  │ │         │ │          │          │
│   └───┬────┘ └───┬────┘ └───┬────┘ └────┬────┘ └────┬─────┘          │
│       │          │          │            │           │                  │
│       ▼          ▼          ▼            ▼           ▼                  │
│   ┌──────────────────────────────────────────────────────────┐         │
│   │           Agent Communication Bus (Redis Pub/Sub)         │         │
│   │  • Inter-agent event broadcasting                         │         │
│   │  • Cascading trigger protocol                             │         │
│   │  • Shared context read/write                              │         │
│   └──────────────────────────────────────────────────────────┘         │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   INTELLIGENCE LAYER                                    │
│                                                                         │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐       │
│   │  Computer     │  │  UK Plant    │  │   Context Graph       │       │
│   │  Vision       │  │  Knowledge   │  │   Engine              │       │
│   │  Pipeline     │  │  Base        │  │   (Decision Traces)   │       │
│   └──────────────┘  └──────────────┘  └───────────────────────┘       │
│                                                                         │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐       │
│   │  Gamification │  │  Scheduling  │  │   Community           │       │
│   │  Engine       │  │  Engine      │  │   Intelligence        │       │
│   └──────────────┘  └──────────────┘  └───────────────────────┘       │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   EXTERNAL INTEGRATIONS                                 │
│                                                                         │
│   ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐       │
│   │  Met Office / │  │  British     │  │   Postcodes.io        │       │
│   │  Open-Meteo   │  │  Geological  │  │   (UK Postcode        │       │
│   │  Weather API  │  │  Survey      │  │    Lookup)            │       │
│   └──────────────┘  └──────────────┘  └───────────────────────┘       │
│                                                                         │
│   ┌──────────────┐  ┌──────────────┐                                   │
│   │  WhatsApp     │  │  Claude API  │                                   │
│   │  Cloud API    │  │  (Anthropic) │                                   │
│   └──────────────┘  └──────────────┘                                   │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   DATA LAYER                                            │
│                                                                         │
│   ┌──────────────────────┐  ┌────────────────────────────────┐         │
│   │  PostgreSQL           │  │  Object Storage (S3/R2)        │         │
│   │  • User & garden state│  │  • Plant photos                │         │
│   │  • Plant records      │  │  • Growth comparison images    │         │
│   │  • Context graph      │  │  • Report/chart exports        │         │
│   │  • Achievements       │  │                                │         │
│   │  • Conversations      │  │                                │         │
│   └──────────────────────┘  └────────────────────────────────┘         │
│                                                                         │
│   ┌──────────────────────┐  ┌────────────────────────────────┐         │
│   │  Redis                │  │  UK Plant Knowledge Store      │         │
│   │  • Session cache      │  │  (PostgreSQL tables +          │         │
│   │  • Agent state        │  │   embedded search)             │         │
│   │  • Rate limit counters│  │                                │         │
│   └──────────────────────┘  └────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Key architectural principles:**

- **Event-driven:** All agent work is triggered by events (user messages, scheduled timers, weather changes, photo submissions), not request-response cycles. This keeps WhatsApp webhook responses fast and agent processing decoupled.
- **Agent-first:** The conversational agent is the primary interface. The database, APIs, and knowledge base exist to serve the agents, not the other way round.
- **Context accumulation:** Every interaction, decision, and observation feeds the context graph. The system gets smarter about each individual garden over time, and smarter about gardening in aggregate.
- **Channel-agnostic core:** The agent engine knows nothing about WhatsApp. A message adapter translates WhatsApp-specific formats into a canonical internal format. This makes adding the React Native app (Phase 2) or future channels (Telegram, email digests) straightforward.

---

## 2. Technology Stack

### 2.1 Backend

| Component | Choice | Justification |
|-----------|--------|---------------|
| **Language** | Python 3.12+ | Best ecosystem for AI/ML workloads. Native async support. Anthropic SDK is Python-first. Founder familiarity. |
| **Framework** | FastAPI | Async-native, automatic OpenAPI docs, Pydantic validation, WebSocket support for Phase 2, excellent performance for an async Python framework. |
| **ASGI Server** | Uvicorn with Gunicorn process manager | Production-grade async serving. Gunicorn manages worker processes; Uvicorn handles async I/O within each worker. |
| **Task Processing** | ARQ (async Redis queue) | Lightweight async task queue built on Redis. Simpler than Celery for our scale, native async/await support, cron-style scheduling for alerts. Falls back to Celery if we outgrow it. |
| **Message Broker** | Redis 7+ (Streams + Pub/Sub) | Streams for durable task queues (guaranteed delivery for outbound WhatsApp messages). Pub/Sub for inter-agent event broadcasting. Single dependency for caching, queuing, and pub/sub. |

**Why not Celery?** Celery is battle-tested but heavyweight for an MVP. ARQ gives us async task processing with Redis as the sole broker dependency. If we reach a scale where ARQ's limitations matter (complex routing, priority queues, multi-broker), migrating to Celery is straightforward since both use Redis.

### 2.2 Database

| Component | Choice | Justification |
|-----------|--------|---------------|
| **Primary Database** | PostgreSQL 16 | JSONB for flexible plant/garden state that evolves without migrations. Full-text search for plant knowledge base. Row-level security for multi-tenancy. Mature ecosystem. |
| **ORM** | SQLAlchemy 2.0 (async) | Async support via `asyncpg`. Type-safe query building. Alembic for migrations. |
| **Migrations** | Alembic | Standard for SQLAlchemy. Auto-generates migration scripts from model changes. |
| **Caching** | Redis | Session state, conversation context window, rate limit counters, frequently accessed plant data. |
| **Object Storage** | Cloudflare R2 (or AWS S3) | Plant photos, growth comparison composites. R2 is S3-compatible with zero egress fees — important when serving photos back through the app in Phase 2. |
| **Vector Search** | pgvector extension | Semantic search over plant knowledge base and context graph entries. Avoids adding a separate vector database dependency. Adequate performance for our scale. |

### 2.3 AI & Machine Learning

| Component | Choice | Justification |
|-----------|--------|---------------|
| **Conversational AI** | Claude API (Anthropic) — claude-sonnet for Sage brain | Best reasoning capability for nuanced gardening advice. Tool use support for multi-agent orchestration. Strong at maintaining personality and context over long conversations. |
| **Agent Orchestration** | Custom Python orchestration layer | Purpose-built for our multi-agent pattern. Simpler and more controllable than LangChain/LangGraph for a well-defined agent topology. Uses Claude's native tool use. |
| **Computer Vision** | Claude's vision capabilities (primary) + fine-tuned classifier (secondary) | Claude's multimodal input handles plant identification and general health assessment. A lightweight fine-tuned classifier (MobileNetV3 or EfficientNet-Lite) handles specific disease/pest detection with higher accuracy for common UK conditions. |
| **Embeddings** | Anthropic Embeddings API (or `all-MiniLM-L6-v2` via sentence-transformers) | For semantic search over plant knowledge and context graph. Local model preferred to avoid per-query API costs at scale. |

**Why Claude over GPT-4?** Claude's tool use pattern maps cleanly to our multi-agent design. Its ability to maintain a consistent personality ("Sage") across long conversations is superior for a companion-style product. The extended thinking capability is valuable for complex gardening decisions that require reasoning across weather, soil, timing, and companion planting simultaneously.

### 2.4 WhatsApp Integration

| Component | Choice | Justification |
|-----------|--------|---------------|
| **WhatsApp Provider** | Meta Cloud API (direct) | No intermediary costs. Full control over message types and templates. Official support for all rich message features. Twilio adds a per-message markup that compounds at scale. |
| **Webhook Processing** | FastAPI endpoint with signature verification | Validates Meta webhook signatures. Parses message types (text, image, button response, list selection). |
| **Template Management** | Meta Business Manager | Required for proactive outbound messages (alerts, reminders). Templates must be pre-approved by Meta. |

**Why direct Meta Cloud API over Twilio?** At MVP scale, the complexity difference is minimal. Twilio adds roughly £0.005-0.01 per message on top of Meta's conversation pricing. For a product sending daily alerts to thousands of users, this adds up. Going direct also gives us full control over rich message formatting and avoids vendor lock-in on a critical channel.

### 2.5 External APIs

| Integration | Provider | Usage Pattern |
|-------------|----------|---------------|
| **Weather** | Open-Meteo (primary), Met Office DataHub (secondary) | Open-Meteo: free, no API key required, hourly/daily forecasts, reliable. Met Office: more accurate UK-specific data, but requires registration and has rate limits. Use Open-Meteo for routine checks; Met Office for severe weather alerts. |
| **Soil Data** | British Geological Survey (BGS) API | Soil type by location. Cached aggressively — soil doesn't change. One-time lookup per user postcode area, stored permanently. |
| **Postcode Lookup** | Postcodes.io | Free, open-source UK postcode API. Returns latitude/longitude, region, and administrative area. Used to determine growing zone, local weather station, and soil data lookup. |
| **Sunrise/Sunset** | Calculated locally | Python `astral` library. Determines daylight hours for the user's location. No API dependency. |

### 2.6 Infrastructure & Deployment

| Component | Choice | Justification |
|-----------|--------|---------------|
| **Hosting** | Railway (MVP) → AWS ECS Fargate (scale) | Railway: simple deployment from Git, managed PostgreSQL and Redis, reasonable pricing, good DX for a small team. Migrate to AWS when we need fine-grained control, VPC isolation, or multi-region. |
| **Container Runtime** | Docker | Consistent environments. Single Dockerfile for the backend. Docker Compose for local development (PostgreSQL, Redis, backend). |
| **CI/CD** | GitHub Actions | Automated tests on PR. Deploy to Railway on merge to `main`. |
| **Monitoring** | Sentry (errors) + Axiom (logs) + Uptime Robot (availability) | Sentry: excellent Python support, captures full stack traces with context. Axiom: structured log aggregation with generous free tier. Uptime Robot: simple webhook endpoint monitoring with SMS alerts. |
| **APM** | OpenTelemetry → Axiom | Distributed tracing across agent calls. Critical for debugging multi-agent decision chains. Understand latency breakdown: how much time in Claude API vs database vs external APIs. |

### 2.7 Phase 2 Additions (React Native App)

| Component | Choice | Justification |
|-----------|--------|---------------|
| **Mobile Framework** | React Native (Expo) | Cross-platform from a single codebase. Expo simplifies build/deploy. Large ecosystem. Founder preference. |
| **State Management** | Zustand | Lightweight, minimal boilerplate. Sufficient for a companion app that is primarily read-heavy with occasional interactions. |
| **Real-time** | WebSocket (via FastAPI) | Live chat with Sage. Push notifications for alerts. Garden state sync. |
| **Push Notifications** | Expo Notifications → APNs/FCM | Supplements WhatsApp alerts. Users choose preferred channel. |
| **Image Handling** | Expo Camera + Image Picker | In-app photo capture and gallery selection for plant health check-ins. |

---

## 3. Data Model

### 3.1 Entity Relationship Overview

```
┌──────────┐       ┌──────────┐       ┌──────────────┐
│   User   │──1:N──│  Garden  │──1:N──│    Plant     │
└────┬─────┘       └────┬─────┘       └──┬───────┬───┘
     │                  │                 │       │
     │                  │                 │       │
     │  1:N             │  1:N            │1:N    │1:N
     ▼                  ▼                 ▼       ▼
┌──────────┐   ┌────────────┐  ┌─────────┐  ┌────────────┐
│  Alert   │   │  Context   │  │  Photo  │  │  Health    │
│          │   │  Event     │  │  Record │  │  Check     │
└──────────┘   └────────────┘  └─────────┘  └────────────┘
     │                                              │
     │                                              │
     │  1:N (user)                                  │
     ▼                                              ▼
┌──────────────┐                          ┌──────────────┐
│ Achievement  │                          │  CV Analysis │
│ / Badge      │                          │  Result      │
└──────────────┘                          └──────────────┘

┌───────────────────────────────────────────────────┐
│  REFERENCE DATA (read-only, seeded)               │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐ │
│  │ PlantSpec  │  │ GrowingCal │  │ Companion   │ │
│  │ (species   │  │ (region +  │  │ Planting    │ │
│  │  database) │  │  month)    │  │ Rules       │ │
│  └────────────┘  └────────────┘  └─────────────┘ │
│  ┌────────────┐  ┌────────────┐                   │
│  │ SoilType   │  │ UK Region  │                   │
│  │ Profiles   │  │ Zones      │                   │
│  └────────────┘  └────────────┘                   │
└───────────────────────────────────────────────────┘
```

### 3.2 Core Entities

**User**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | Primary key |
| `whatsapp_phone` | VARCHAR(20) | E.164 format, unique, indexed |
| `display_name` | VARCHAR(100) | From WhatsApp profile or user-provided |
| `postcode_outward` | VARCHAR(4) | First part of postcode only (e.g., "BS3") — sufficient for weather/soil, avoids storing full address |
| `latitude` | DECIMAL(8,6) | Derived from postcode, used for weather lookups |
| `longitude` | DECIMAL(9,6) | Derived from postcode |
| `uk_region` | VARCHAR(50) | E.g., "South West England" — determines growing calendar |
| `soil_type` | VARCHAR(50) | From BGS lookup: clay, sandy, loam, chalk, peat, silt |
| `experience_level` | ENUM | novice, intermediate, experienced |
| `subscription_tier` | ENUM | free, grower (paid), market_gardener (paid) |
| `onboarding_complete` | BOOLEAN | Has the user completed the initial Sage conversation? |
| `preferences` | JSONB | Notification times, preferred alert frequency, units, interests |
| `timezone` | VARCHAR(50) | Always "Europe/London" for UK users, but stored for correctness |
| `created_at` | TIMESTAMPTZ | |
| `last_active_at` | TIMESTAMPTZ | Updated on every interaction |

**Garden**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `user_id` | UUID | FK to User |
| `name` | VARCHAR(100) | "Back Garden", "Allotment Plot 7" |
| `size_sqm` | DECIMAL(8,2) | Approximate — Sage helps estimate during onboarding |
| `orientation` | ENUM | north, south, east, west, mixed |
| `garden_type` | ENUM | back_garden, front_garden, allotment, balcony, windowsill, community_garden |
| `growing_method` | ENUM[] | Array: raised_beds, ground, containers, greenhouse, polytunnel |
| `microclimate_notes` | JSONB | Free-form observations: "south wall is a sun trap", "frost pocket in the corner", "exposed to north wind" |
| `water_source` | ENUM | mains, water_butt, both, none |
| `is_primary` | BOOLEAN | Default garden for alerts |
| `created_at` | TIMESTAMPTZ | |

**Plant**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `garden_id` | UUID | FK to Garden |
| `plant_spec_id` | UUID | FK to PlantSpec (reference data) |
| `variety` | VARCHAR(100) | Specific cultivar: "Gardeners Delight", "Purple Sprouting" |
| `location_description` | VARCHAR(200) | "Raised bed 2, back row" — free text, Sage remembers |
| `planting_date` | DATE | When sown/planted |
| `planting_method` | ENUM | direct_sow, transplant, bought_seedling, cutting |
| `growth_stage` | ENUM | seed, germinating, seedling, vegetative, flowering, fruiting, harvesting, dormant, removed |
| `health_status` | ENUM | thriving, healthy, fair, struggling, diseased, dead |
| `health_score` | SMALLINT | 0-100, updated by CV analysis and agent assessments |
| `notes` | JSONB | Running observations, stored as timestamped entries |
| `harvest_log` | JSONB | Array of {date, quantity, quality_notes} |
| `is_active` | BOOLEAN | False when season ends or plant removed |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**Alert**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `user_id` | UUID | FK to User |
| `plant_id` | UUID | FK to Plant (nullable — some alerts are garden-wide) |
| `alert_type` | ENUM | frost_warning, watering_reminder, sow_window, harvest_ready, pest_risk, health_check_due, feeding_reminder, succession_sowing |
| `priority` | ENUM | low, medium, high, urgent |
| `scheduled_for` | TIMESTAMPTZ | When to send |
| `sent_at` | TIMESTAMPTZ | When actually sent (nullable if pending) |
| `delivery_status` | ENUM | pending, sent, delivered, read, failed |
| `whatsapp_message_id` | VARCHAR(100) | For delivery status tracking |
| `message_content` | TEXT | The actual message sent |
| `user_response` | JSONB | What the user did: acknowledged, snoozed, asked follow-up |
| `source_agent` | VARCHAR(50) | Which agent generated this alert |
| `reasoning` | TEXT | Why this alert was triggered — feeds context graph |
| `created_at` | TIMESTAMPTZ | |

**ContextEvent** (The Compound Intelligence Moat)

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `user_id` | UUID | FK to User |
| `garden_id` | UUID | FK to Garden (nullable) |
| `plant_id` | UUID | FK to Plant (nullable) |
| `event_type` | VARCHAR(50) | decision, observation, alert_outcome, weather_event, health_change, harvest, user_feedback, agent_reasoning |
| `source_agent` | VARCHAR(50) | Which agent generated this event |
| `summary` | TEXT | Human-readable summary |
| `detail` | JSONB | Structured event data — varies by type |
| `reasoning_trace` | TEXT | The agent's reasoning chain — why this conclusion was reached |
| `related_events` | UUID[] | Links to prior context events that influenced this one |
| `confidence` | DECIMAL(3,2) | Agent's confidence in the assessment (0.00-1.00) |
| `outcome_tracked` | BOOLEAN | Has the outcome of this event/decision been verified? |
| `outcome_notes` | TEXT | What actually happened — did the prediction/advice prove correct? |
| `embedding` | VECTOR(384) | For semantic search over context history |
| `created_at` | TIMESTAMPTZ | |

The context graph is the most important table in the system. It accumulates every significant event, decision, observation, and outcome. Over time, it enables Sage to say things like: "Last year when we had a cold snap in late April, your runner beans suffered — this year, let's wait until mid-May" or "Based on your soil and the drainage issues you mentioned in October, I'd suggest raised beds for your carrots this time."

**Achievement**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `user_id` | UUID | FK to User |
| `badge_type` | VARCHAR(50) | first_harvest, week_streak_7, photo_regular, companion_planter, frost_survivor, soil_improver, seed_saver |
| `badge_tier` | ENUM | bronze, silver, gold |
| `earned_at` | TIMESTAMPTZ | |
| `season` | VARCHAR(20) | "spring_2026" — for seasonal challenges |
| `metadata` | JSONB | Context: which plant, what streak count, etc. |

**PhotoRecord**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `plant_id` | UUID | FK to Plant |
| `user_id` | UUID | FK to User |
| `storage_key` | VARCHAR(255) | Object storage path |
| `thumbnail_key` | VARCHAR(255) | Resized version for quick loading |
| `taken_at` | TIMESTAMPTZ | When the photo was submitted |
| `cv_analysis` | JSONB | Computer vision results: health assessment, detected issues, growth stage estimate |
| `cv_model_version` | VARCHAR(20) | Which model version produced the analysis |
| `whatsapp_media_id` | VARCHAR(100) | Original WhatsApp media reference |
| `created_at` | TIMESTAMPTZ | |

### 3.3 Reference Data (Seeded, Read-Only in Normal Operation)

**PlantSpec** — the UK edible plant database

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `common_name` | VARCHAR(100) | "Tomato", "Runner Bean", "Rosemary" |
| `botanical_name` | VARCHAR(150) | "Solanum lycopersicum" |
| `category` | ENUM | vegetable, herb, fruit, edible_flower |
| `uk_hardiness` | ENUM | hardy, half_hardy, tender |
| `growing_difficulty` | ENUM | beginner, intermediate, advanced |
| `soil_preferences` | JSONB | Preferred soil types, pH range, drainage needs |
| `sun_requirements` | ENUM | full_sun, partial_shade, full_shade, any |
| `water_needs` | ENUM | low, moderate, high |
| `spacing_cm` | JSONB | {between_plants, between_rows} |
| `days_to_germination` | INT4RANGE | Range, e.g., [7, 14] |
| `days_to_harvest` | INT4RANGE | From transplant/final position |
| `common_pests` | VARCHAR[] | Array of common pest names |
| `common_diseases` | VARCHAR[] | Array of common disease names |
| `companion_plants` | UUID[] | FKs to other PlantSpec entries |
| `antagonist_plants` | UUID[] | Plants to keep away from |
| `notes` | TEXT | General growing tips |

**GrowingCalendar** — what to do when, by region

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `plant_spec_id` | UUID | FK to PlantSpec |
| `uk_region` | VARCHAR(50) | Region identifier |
| `activity` | ENUM | sow_indoors, sow_outdoors, transplant, harvest_begin, harvest_end, prune, feed |
| `month_start` | SMALLINT | 1-12 |
| `month_end` | SMALLINT | 1-12 |
| `notes` | TEXT | Region-specific advice |

**CompanionPlantingRule**

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID | |
| `plant_a_id` | UUID | FK to PlantSpec |
| `plant_b_id` | UUID | FK to PlantSpec |
| `relationship` | ENUM | beneficial, antagonistic, neutral |
| `mechanism` | TEXT | Why: "Basil repels aphids from tomatoes", "Fennel inhibits growth of most plants" |

### 3.4 JSONB Strategy

PostgreSQL JSONB is used deliberately for fields that:
- Evolve frequently during early product development (preferences, microclimate notes, CV analysis results)
- Have variable structure per record (different plants have different health check data)
- Need to store timestamped arrays that grow over time (harvest logs, observation notes)

Structured columns are used for fields that are:
- Queried frequently (postcode, growth stage, health status)
- Used in joins or foreign keys
- Part of the core data model that is stable

This hybrid approach avoids constant migrations during MVP iteration while keeping query performance strong for the fields that matter.

---

## 4. Multi-Agent Architecture

### 4.1 Agent Topology

Sage uses a **hub-and-spoke orchestration pattern** where the Sage Orchestrator is the central coordinator and specialist agents are invoked as tools.

```
                    ┌─────────────────────────┐
                    │                         │
                    │    SAGE ORCHESTRATOR     │
                    │    (Claude API Call)     │
                    │                         │
                    │  • Receives user message │
                    │  • Classifies intent    │
                    │  • Invokes tools        │
                    │  • Synthesises response  │
                    │  • Maintains personality │
                    │                         │
                    └────────┬────────────────┘
                             │
              ┌──────────────┼──────────────────┐
              │              │                  │
              ▼              ▼                  ▼
    ┌─────────────┐ ┌──────────────┐ ┌─────────────────┐
    │  Weather    │ │    Soil      │ │   Pest/Disease   │
    │  Agent      │ │   Agent      │ │     Agent        │
    │             │ │              │ │                   │
    │ • Forecast  │ │ • Soil type  │ │ • Identification  │
    │ • Frost     │ │   analysis   │ │ • Treatment       │
    │   alerts    │ │ • Amendment  │ │   advice          │
    │ • Watering  │ │   advice     │ │ • Prevention      │
    │   guidance  │ │ • pH/drain-  │ │   strategies      │
    │ • Seasonal  │ │   age needs  │ │ • Risk assessment │
    │   timing    │ │ • Companion  │ │                   │
    │             │ │   suitability│ │                   │
    └─────────────┘ └──────────────┘ └─────────────────┘

              ┌──────────────┐ ┌──────────────────┐
              │   Harvest    │ │    Planning       │
              │   Agent      │ │    Agent          │
              │              │ │                   │
              │ • Readiness  │ │ • Seasonal plan   │
              │   assessment │ │ • Succession      │
              │ • Yield      │ │   sowing          │
              │   tracking   │ │ • Crop rotation   │
              │ • Storage    │ │ • Space           │
              │   advice     │ │   optimisation    │
              │ • Preserving │ │ • Calendar        │
              │   tips       │ │   generation      │
              └──────────────┘ └──────────────────┘
```

### 4.2 How It Works: Tool Use, Not Autonomous Agents

The specialist agents are **not** independent processes running in the background. They are implemented as **tool definitions** that the Sage Orchestrator (a single Claude API call with tools) can invoke. This is a critical design decision.

**The pattern:**

1. User sends a message via WhatsApp.
2. The Sage Orchestrator receives the message along with conversation history and relevant context (user profile, garden state, recent context events).
3. Claude decides which tools (specialist agents) to invoke based on the user's intent.
4. Each tool call executes a Python function that may:
   - Query the database for relevant data
   - Call an external API (weather, soil)
   - Run a secondary Claude API call with a specialist system prompt (for complex reasoning)
   - Trigger computer vision analysis
5. Tool results return to the Orchestrator.
6. Claude synthesises a final response in Sage's voice.
7. The response is sent back via WhatsApp.

**Why this over autonomous agents?**

- **Predictability:** A single orchestrator with tools is far easier to reason about, debug, and monitor than a network of autonomous agents passing messages.
- **Cost control:** Each user message results in one primary Claude API call (the orchestrator) plus zero or more secondary calls (specialist reasoning). Autonomous agents can spiral into unbounded API usage.
- **Latency:** WhatsApp users expect responses in seconds. A single orchestrated call with tool use is faster than a multi-hop agent chain.
- **Reliability:** Fewer moving parts. No risk of agent deadlocks or infinite loops.

### 4.3 Agent Tool Definitions

**Weather Agent Tools:**

| Tool | Purpose | Data Sources |
|------|---------|-------------|
| `get_weather_forecast` | Current conditions and 7-day forecast for user's location | Open-Meteo API |
| `check_frost_risk` | Frost probability for the next 72 hours | Open-Meteo hourly data, historical frost dates for region |
| `get_watering_guidance` | Whether to water today based on recent/forecast rainfall and temperature | Open-Meteo precipitation + evapotranspiration data |
| `assess_growing_conditions` | Is this a good week for sowing/transplanting given the forecast? | Open-Meteo + growing calendar |

**Soil Agent Tools:**

| Tool | Purpose | Data Sources |
|------|---------|-------------|
| `get_soil_profile` | Soil characteristics for user's postcode area | BGS API (cached), user's reported observations |
| `recommend_amendments` | What to add to soil for a specific crop | PlantSpec soil preferences vs actual soil type |
| `assess_drainage` | Drainage characteristics and improvement advice | BGS data + garden type + user observations |
| `check_companion_suitability` | Whether proposed plantings work together in this soil | CompanionPlantingRule + soil preferences |

**Pest/Disease Agent Tools:**

| Tool | Purpose | Data Sources |
|------|---------|-------------|
| `identify_from_description` | Identify pest/disease from user's text description | PlantSpec common pests/diseases + Claude reasoning |
| `identify_from_photo` | Identify pest/disease from submitted photo | CV pipeline + Claude vision |
| `get_treatment_options` | Organic and conventional treatment recommendations | Knowledge base, prioritising organic methods |
| `assess_pest_risk` | Current pest risk based on weather and season | Weather data + seasonal pest patterns |
| `get_prevention_strategy` | Preventative measures for common issues | PlantSpec + companion planting + seasonal timing |

**Harvest Agent Tools:**

| Tool | Purpose | Data Sources |
|------|---------|-------------|
| `check_harvest_readiness` | Is this plant ready to pick? | PlantSpec days_to_harvest + planting_date + growth_stage + health_status |
| `log_harvest` | Record a harvest with quantity and quality | Plant.harvest_log |
| `get_storage_advice` | How to store this crop after picking | Knowledge base |
| `suggest_recipes` | Simple recipe ideas for what's ready to harvest | Knowledge base (curated, not generated) |

**Planning Agent Tools:**

| Tool | Purpose | Data Sources |
|------|---------|-------------|
| `generate_seasonal_plan` | What to sow/plant this month based on garden, region, and experience | GrowingCalendar + user profile + garden state |
| `suggest_succession_sowing` | When to sow next batch for continuous harvest | GrowingCalendar + existing plant records |
| `plan_crop_rotation` | Rotation advice based on what was grown where last year | Context graph (previous seasons) + PlantSpec family groupings |
| `optimise_space` | Suggest plants that fit available space and complement existing ones | Garden dimensions + current plants + companion rules |
| `generate_calendar` | Personalised month-by-month growing calendar | All of the above, synthesised |

### 4.4 Cascading Agent Triggers (Background Processing)

While the tool-use pattern handles user-initiated conversations, some intelligence runs in the background on scheduled timers. This is where agents trigger each other.

**Example cascade: Frost Warning Flow**

```
1. SCHEDULER (every 6 hours)
   └─→ Weather Agent: check_frost_risk for all active users
        │
        ├─ No frost risk → log context event, no further action
        │
        └─ Frost risk detected for user X
             │
             ├─→ Query: What tender plants does user X have outdoors?
             │     └─ Result: 4 tomato plants (tender), 2 runner beans (half-hardy)
             │
             ├─→ Pest/Disease Agent: assess_pest_risk
             │     └─ Flag: Post-frost slug surge likely in 48 hours
             │
             ├─→ Context Graph: Log frost warning event with
             │   affected plants and reasoning
             │
             └─→ Compose Alert:
                  "Frost likely tonight (down to -2°C by 3am). Your tomatoes
                   and runner beans need protection — cover them or bring pots
                   inside if you can. Also worth scattering slug pellets around
                   the beans — slugs go wild after a frost. 🐌"
                  │
                  └─→ Alert Queue → WhatsApp (sent at user's preferred time)
```

**Implementation:** These cascades are orchestrated by Python functions (not additional Claude API calls unless complex reasoning is needed). The Weather Agent's `check_frost_risk` is a simple API call + threshold check. Only the final message composition uses Claude, to maintain Sage's natural voice.

### 4.5 Context Sharing Protocol

Agents share context through three mechanisms:

1. **Direct database queries.** Each tool function has read access to all relevant tables. The Weather Agent can query a user's plants to know what is at risk. The Planning Agent can read the context graph to understand what worked last season.

2. **Tool result passing.** Within a single orchestrator call, Claude sees the results of all tool invocations and can reason across them. If the Weather Agent reports rain and the Soil Agent reports clay soil, Claude can synthesise: "Don't water today — your clay soil will be holding plenty of moisture from yesterday's rain."

3. **Context graph queries.** For historical intelligence, agents query the context graph for relevant past events. Implemented as a `search_context_history` tool available to the orchestrator, using pgvector semantic search.

---

## 5. WhatsApp Integration Design

### 5.1 Message Flow

**Inbound (User → Sage):**

```
User sends WhatsApp message
        │
        ▼
Meta Cloud API delivers webhook POST to /webhook/whatsapp
        │
        ▼
FastAPI endpoint:
  1. Verify X-Hub-Signature-256 header (HMAC-SHA256)
  2. Return 200 OK immediately (Meta requires <15s response)
  3. Parse message type (text, image, button_reply, list_reply, location)
  4. Enqueue to Redis Streams: inbound_messages
        │
        ▼
ARQ worker picks up message:
  1. Load user profile + garden state + recent conversation history
  2. Build context payload for Sage Orchestrator
  3. Call Claude API with tools
  4. Receive response (may include multiple tool calls)
  5. Format response for WhatsApp (split long messages, add buttons)
  6. Enqueue to Redis Streams: outbound_messages
  7. Log context events
  8. Check achievement triggers
        │
        ▼
Outbound worker sends via WhatsApp Cloud API
  1. Send message(s) in sequence
  2. Store whatsapp_message_id for delivery tracking
  3. Handle rate limits with exponential backoff
```

**Outbound (Sage → User, proactive alerts):**

```
ARQ scheduled task (e.g., every 6 hours):
  1. Run weather checks for all users
  2. Check alert schedule (watering reminders, sow windows)
  3. Generate personalised messages via Claude
  4. Queue alerts respecting user's preferred notification window
        │
        ▼
Alert delivery worker:
  1. Check: Is this within user's notification window? (e.g., 7am-9pm)
  2. Check: Have we exceeded daily message limit for this user?
  3. Send via WhatsApp Cloud API using approved template messages
  4. Log delivery status
```

### 5.2 Conversation State Management

WhatsApp conversations don't have persistent sessions in the traditional sense. State is managed through:

1. **Conversation history in PostgreSQL.** The last N messages (configurable, default 20) are loaded as context for each Claude API call. Older messages are summarised periodically.

2. **Active conversation context in Redis.** Short-lived state for multi-turn flows (e.g., onboarding wizard, plant identification requiring follow-up questions). TTL of 30 minutes. Structure: `conv:{user_id}:{flow_type}` → JSONB with current step, accumulated data, and timeout.

3. **WhatsApp 24-hour session window.** After a user messages, we have 24 hours to send free-form replies. After 24 hours, only pre-approved template messages can be sent. The system tracks session windows per user and routes messages accordingly.

### 5.3 Rich Message Types

WhatsApp Business API supports several interactive formats. Sage uses them to reduce friction:

| Message Type | Use Case | Example |
|-------------|----------|---------|
| **Text** | General conversation, advice, explanations | "Your tomatoes look healthy! The slight yellowing on the lower leaves is normal — they're redirecting energy to the fruit." |
| **Image** | Growth comparison photos, visual guides | Side-by-side of this week vs last week's photo |
| **Quick Reply Buttons** (max 3) | Simple choices, confirmations | "Did you manage to cover the beans last night?" → [Yes] [No] [Forgot!] |
| **List Messages** (max 10 items) | Selecting from options | "What would you like help with?" → Sowing guide / Pest help / Watering advice / Check my plants / Update garden |
| **Location Request** | During onboarding, to set postcode | "Could you share your location so I can look up your soil and weather?" |
| **Template Messages** | Proactive alerts outside 24h window | "Frost alert: temperatures dropping to {{1}} tonight. Your {{2}} needs protection. Tap here for what to do." |

### 5.4 Rate Limits and Cost Management

**Meta WhatsApp pricing (as of 2026):**
- Business-initiated conversations (templates): tiered pricing by volume, approximately £0.03-0.08 per conversation (24-hour window) for UK numbers
- User-initiated conversations: first 1,000/month free, then similar pricing
- A "conversation" covers all messages within a 24-hour window from the trigger

**Cost control measures:**
- **Batch alerts:** Combine multiple alerts into a single message where sensible ("Morning update: watering not needed today, but your lettuces are ready for succession sowing, and the courgettes could use a feed this week")
- **User-configurable frequency:** Daily digest vs individual alerts. Fewer conversations = lower cost.
- **Smart session management:** When a user messages (opening a free session), send any pending alerts within that session rather than opening a new template-initiated conversation later.
- **Daily message cap:** Maximum 3 proactive outbound conversations per user per day. Prevents runaway costs from overeager agents.
- **Template message pooling:** Keep the number of approved templates manageable. Templates require Meta approval, which takes 24-48 hours. Maintain a library of 15-20 covering all alert types.

**Rate limits:**
- Meta imposes tier-based sending limits: starts at 250 unique users/day, scaling to 100,000+/day based on phone number quality rating.
- The outbound worker respects these limits with a token-bucket rate limiter in Redis.

### 5.5 Template Message Strategy

Templates are required for any message sent outside the 24-hour user-initiated session window. These must be pre-approved by Meta.

**Core templates (MVP):**

| Template Name | Category | Content Pattern |
|---------------|----------|----------------|
| `frost_alert` | UTILITY | "Frost alert for tonight: {{1}}. Your {{2}} at risk. Reply for protection tips." |
| `morning_digest` | UTILITY | "Good morning! Today's garden update: {{1}}" |
| `weekly_health_check` | UTILITY | "Time for your weekly plant check-in! Send a photo of {{1}} and I'll take a look." |
| `sow_window_open` | UTILITY | "Great news — it's time to sow {{1}}! Reply for a step-by-step guide." |
| `harvest_ready` | UTILITY | "Your {{1}} look ready to pick! Here's what to look for: {{2}}" |
| `achievement_earned` | MARKETING | "You've earned the {{1}} badge! {{2}}" |
| `seasonal_nudge` | MARKETING | "Spring is here! {{1}}" |
| `re_engagement` | MARKETING | "Your garden misses you! {{1}} Reply to catch up with Sage." |

Templates categorised as UTILITY have higher delivery rates and lower costs. MARKETING templates require user opt-in and are rate-limited by Meta.

---

## 6. Computer Vision Pipeline

### 6.1 Photo Submission Flow

```
User sends photo via WhatsApp
        │
        ▼
WhatsApp webhook delivers image message
  • message.type = "image"
  • message.image.id = WhatsApp media ID
        │
        ▼
Inbound worker:
  1. Download image from WhatsApp Media API
     GET https://graph.facebook.com/v21.0/{media_id}
     (returns temporary download URL, valid 5 minutes)
  2. Download actual image bytes from temporary URL
  3. Validate: JPEG/PNG, max 5MB, minimum 640x480
  4. Generate thumbnail (320px wide) for quick retrieval
  5. Upload both to object storage:
     photos/{user_id}/{plant_id}/{timestamp}_full.jpg
     photos/{user_id}/{plant_id}/{timestamp}_thumb.jpg
  6. Create PhotoRecord in database
  7. Enqueue CV analysis task
        │
        ▼
CV Analysis worker:
  1. Load image from object storage
  2. Run health assessment (see 6.2)
  3. Store results in PhotoRecord.cv_analysis
  4. Update Plant.health_status and Plant.health_score
  5. Log context event with analysis results
  6. If issues detected → trigger response via Sage
  7. If growth change detected → update Plant.growth_stage
        │
        ▼
Sage composes response incorporating CV results
  "Your tomato plant is looking great — nice strong stem and
   healthy green colour. I can see the first flowers forming,
   so you're moving into the flowering stage! Keep up the
   regular feeding with a high-potash fertiliser."
```

### 6.2 Image Processing and Analysis

The CV pipeline uses a two-stage approach:

**Stage 1: Claude Vision (Primary Analysis)**

Claude's multimodal capability handles the broad assessment. The image is sent to Claude along with context (plant species, growth stage, location, recent weather) and a specialist prompt:

```
System prompt for vision analysis:
- You are a plant health analyst examining a photo of {plant_species}
  ({variety}) in its {growth_stage} stage.
- Location: {uk_region}, soil type: {soil_type}
- Recent weather: {weather_summary}
- Assess: overall health (0-100), growth stage, any visible issues
  (pests, disease, nutrient deficiency, physical damage)
- Compare against expected appearance for this species at this stage
- Return structured JSON with confidence scores
```

This handles the majority of cases well. Claude can identify common issues (yellowing leaves, wilting, powdery mildew, visible pests) and reason about context (is yellowing normal for this stage? Is wilting expected given the heatwave?).

**Stage 2: Specialist Classifier (Secondary, for Common Diseases)**

For the most common UK plant diseases, a lightweight classifier provides a second opinion and higher accuracy:

| Model | Purpose | Details |
|-------|---------|--------|
| MobileNetV3-Small | Disease classification | Fine-tuned on UK plant disease dataset. 15-20 classes covering common issues: powdery mildew, blight, rust, aphid damage, slug damage, nutrient deficiencies. Runs on CPU, inference <200ms. |
| Training Data | Initially: PlantVillage dataset (open source, 50K+ images) filtered to UK-relevant crops. Augmented with user-submitted photos (with consent) over time. | |
| Confidence Threshold | Only report classifier results with >75% confidence. Below that, defer to Claude's broader reasoning. | |

**Why both?** Claude is excellent at contextual reasoning ("this yellowing is probably nitrogen deficiency given the sandy soil and heavy rain") but can be inconsistent at fine-grained disease classification. A purpose-trained classifier is more reliable for specific diseases it was trained on. The combination provides both breadth (Claude) and depth (classifier).

### 6.3 Growth Tracking Over Time

One of Sage's most compelling features: comparing photos over time to show growth progress.

**Implementation:**

1. Each plant accumulates a series of PhotoRecords, ideally one per week from weekly check-in prompts.
2. When a new photo is submitted, the CV pipeline also loads the most recent previous photo.
3. Claude receives both images with the prompt: "Compare these two photos of the same {plant_species}, taken {days_apart} days apart. Assess growth progress, any changes in health, and whether development is on track for this stage."
4. The comparison generates a context event recording the progression.
5. For the Phase 2 mobile app: a "growth timeline" view showing thumbnails in sequence with health scores charted over time.

**Photo comparison composite (for WhatsApp):**

When notable growth has occurred, the system generates a side-by-side image (using Pillow/PIL) showing "2 weeks ago → today" and sends it back to the user. This is a powerful engagement driver — people love seeing their plants grow.

### 6.4 Disease/Pest Detection Approach

**Detection hierarchy (most to least confidence):**

1. **User reports symptoms in text** + **photo confirms:** Highest confidence. "My courgette leaves have white powder on them" + photo showing powdery mildew = definitive identification.
2. **Photo analysis detects visual symptoms:** CV pipeline identifies issue. Sage asks clarifying questions: "I can see some discolouration on the leaves. Have you noticed any tiny insects on the underside?"
3. **Pattern-based risk assessment (no photo):** Based on weather + season + plant species + regional pest data. "Your broad beans are entering peak blackfly season — worth checking the growing tips this week."
4. **User describes symptoms without photo:** Sage asks for a photo. "That sounds like it could be a few things. Could you send me a photo so I can take a closer look?"

### 6.5 Model Training Strategy

**Phase 1 (MVP):** Rely primarily on Claude's vision capabilities. No custom model training needed. Supplement with the pre-trained MobileNetV3 fine-tuned on PlantVillage data for common disease detection.

**Phase 2 (6-12 months):** Begin collecting user-submitted photos (with explicit consent and GDPR-compliant processing). Label a subset for fine-tuning. Target: 500+ labelled images per disease class for the 10 most common UK issues.

**Phase 3 (12+ months):** Train a UK-specific plant health model on accumulated data. This becomes part of the compound moat — no competitor will have a dataset of UK garden plants photographed weekly with accompanying weather, soil, treatment, and outcome data.

---

## 7. API Design

### 7.1 REST API (FastAPI)

All endpoints are prefixed with `/api/v1`. Authentication is via Bearer token (JWT) for the mobile app and webhook signature verification for WhatsApp.

**User & Onboarding:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/webhook/whatsapp` | WhatsApp webhook (inbound messages + status updates) |
| `GET` | `/webhook/whatsapp` | WhatsApp webhook verification (Meta challenge) |
| `GET` | `/users/me` | Get current user profile (mobile app, authenticated) |
| `PATCH` | `/users/me` | Update user preferences |
| `GET` | `/users/me/onboarding-status` | Check onboarding completion state |

**Garden Management:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/gardens` | List user's gardens |
| `GET` | `/gardens/{garden_id}` | Get garden detail with plants summary |
| `POST` | `/gardens` | Create a garden (typically done via Sage conversation) |
| `PATCH` | `/gardens/{garden_id}` | Update garden details |

**Plant Management:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/gardens/{garden_id}/plants` | List plants in a garden, with filters (active, growth_stage, health) |
| `GET` | `/plants/{plant_id}` | Full plant detail including health history and recent photos |
| `GET` | `/plants/{plant_id}/timeline` | Photo timeline with health scores over time |
| `GET` | `/plants/{plant_id}/context` | Context events related to this plant |
| `POST` | `/gardens/{garden_id}/plants` | Add a plant |
| `PATCH` | `/plants/{plant_id}` | Update plant state |

**Intelligence & Alerts:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/alerts` | User's alerts (filterable by type, status, date range) |
| `GET` | `/weather/forecast` | Current weather forecast for user's location |
| `GET` | `/calendar/this-month` | Personalised growing calendar for current month |
| `GET` | `/recommendations` | Current actionable recommendations from agents |

**Achievements & Gamification:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/achievements` | User's earned badges and streaks |
| `GET` | `/achievements/available` | Badges the user can work towards |
| `GET` | `/streaks` | Current streak data (photo check-ins, daily engagement) |

**Knowledge Base:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/plants/search?q={query}` | Search plant database (for adding plants) |
| `GET` | `/plants/specs/{spec_id}` | Full plant species info |
| `GET` | `/plants/specs/{spec_id}/calendar` | Growing calendar for a species in user's region |
| `GET` | `/companion-check?plants={id1,id2}` | Check companion planting compatibility |

**Photos:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/plants/{plant_id}/photos` | Upload photo (mobile app — multipart form) |
| `GET` | `/plants/{plant_id}/photos` | List photos for a plant |
| `GET` | `/photos/{photo_id}` | Get photo metadata + CV analysis results |
| `GET` | `/photos/{photo_id}/image` | Serve the actual image (proxied from object storage with signed URL) |

### 7.2 WebSocket (Phase 2 — Mobile App Chat)

| Endpoint | Description |
|----------|-------------|
| `WS /ws/chat` | Real-time bidirectional chat with Sage. Supports streaming responses (token-by-token as Claude generates). Handles typing indicators, read receipts. Falls back to REST polling if WebSocket connection drops. |

**WebSocket message protocol:**

```
// Client → Server
{
  "type": "message",
  "content": "Should I water the tomatoes today?",
  "garden_id": "uuid",  // optional context
  "plant_id": "uuid"    // optional context
}

// Server → Client (streaming response)
{
  "type": "response_chunk",
  "content": "Based on today's ",
  "message_id": "uuid"
}

// Server → Client (response complete)
{
  "type": "response_complete",
  "message_id": "uuid",
  "actions_taken": ["weather_check", "soil_moisture_estimate"],
  "achievements_earned": []
}

// Server → Client (alert push)
{
  "type": "alert",
  "alert_id": "uuid",
  "content": "Frost warning tonight!",
  "priority": "high",
  "actions": [{"label": "What should I do?", "action": "frost_protection_guide"}]
}
```

### 7.3 Internal APIs (Not Exposed)

| Service | Description |
|---------|-------------|
| WhatsApp Media API client | Downloads and uploads media to/from WhatsApp |
| Open-Meteo client | Weather forecast retrieval with caching (1-hour TTL for current conditions, 6-hour TTL for 7-day forecast) |
| BGS API client | Soil data lookup with permanent cache (soil doesn't change) |
| Postcodes.io client | Postcode resolution with permanent cache |
| Claude API wrapper | Handles tool use protocol, streaming, retry with exponential backoff, usage tracking |
| CV pipeline | Image preprocessing, Claude vision call, classifier inference, result aggregation |

---

## 8. Security & Privacy

### 8.1 GDPR Compliance (UK GDPR / Data Protection Act 2018)

Sage processes personal data and must comply fully with UK GDPR. The key provisions:

**Lawful Basis:**

| Data Processing Activity | Lawful Basis | Justification |
|--------------------------|-------------|---------------|
| Core service (advice, alerts, tracking) | Contract performance (Art. 6(1)(b)) | Necessary to deliver the service the user signed up for |
| Plant photos for health analysis | Contract performance | Core feature — user submits photos specifically for analysis |
| Location/postcode for weather & soil | Contract performance | Cannot provide localised advice without it |
| Community intelligence (anonymised) | Legitimate interest (Art. 6(1)(f)) | Aggregated, anonymised data to improve advice for all users |
| Marketing messages / re-engagement | Consent (Art. 6(1)(a)) | Explicit opt-in via WhatsApp, easy opt-out |
| Model training on user photos | Consent (Art. 6(1)(a)) | Separate, explicit, granular consent. Not bundled with service agreement. |

**Data Subject Rights Implementation:**

| Right | Implementation |
|-------|---------------|
| **Right of access** | `/api/v1/users/me/data-export` — generates full JSON export of all user data, context events, photos, conversations |
| **Right to erasure** | `/api/v1/users/me/delete` — permanent deletion of all user data. Photos removed from object storage. Context graph entries anonymised (not deleted, as they contribute to aggregate intelligence without PII). Process completes within 30 days. |
| **Right to portability** | Same data export endpoint, machine-readable JSON format |
| **Right to rectification** | Users can correct their data via Sage conversation or API |
| **Right to restrict processing** | Account suspension feature — stops all proactive alerts and processing while retaining data |

**Data Minimisation:**
- Only the outward postcode is stored (e.g., "BS3"), not the full postcode or street address. This is sufficient for weather and soil lookups whilst being too imprecise to identify a specific household.
- WhatsApp phone numbers are stored (necessary for service delivery) but not shared externally.
- Conversation history is summarised and older messages purged after 90 days. Context events (the valuable intelligence) are retained as they contain no raw conversation text.
- Photos are retained for 12 months unless the user requests earlier deletion or opts into extended retention for model training.

### 8.2 Data Encryption

| Layer | Approach |
|-------|----------|
| **In transit** | TLS 1.3 everywhere. All API communication over HTTPS. WebSocket over WSS. Database connections over TLS. |
| **At rest (database)** | PostgreSQL with transparent data encryption (TDE) if supported by hosting provider, otherwise filesystem-level encryption (e.g., AWS EBS encryption, Railway's managed encryption). |
| **At rest (object storage)** | Server-side encryption (SSE-S3 or equivalent). |
| **Application-level encryption** | Phone numbers encrypted at the application level using AES-256-GCM with key management via environment variables (MVP) → dedicated KMS (scale). This means even a database dump doesn't expose phone numbers. |
| **API keys and secrets** | Stored in environment variables, never in code. Rotated quarterly. Accessed via a secrets manager (Railway's environment variables for MVP, AWS Secrets Manager or similar at scale). |

### 8.3 WhatsApp Data Handling

- **Message content** is processed in memory for agent reasoning and then stored as conversation records. Raw message payloads from Meta are not stored beyond parsing.
- **Media (photos)** are downloaded from Meta's temporary URLs (valid 5 minutes), processed, and stored in our object storage. The WhatsApp media ID is retained for reference but the temporary URL is discarded.
- **Phone numbers** are the primary user identifier for WhatsApp. Encrypted at rest in the database.
- **Meta's data sharing:** We receive only what the user sends us. We do not access the user's WhatsApp contacts, groups, or any data beyond the direct conversation.
- **WhatsApp Business Policy compliance:** No spamming, no unsolicited marketing without consent, no sharing of user data with third parties, message templates reviewed for policy compliance before submission to Meta.

### 8.4 Photo Storage and Retention

| Policy | Detail |
|--------|--------|
| **Default retention** | 12 months from upload. After 12 months, photos are permanently deleted unless the user has opted into extended retention. |
| **User deletion** | Users can delete individual photos or all photos at any time. Deletion is permanent (no soft delete for photos — they're large binary data). |
| **Model training consent** | Photos are only used for model training if the user has given explicit, separate consent. Consent can be withdrawn at any time, and previously contributed photos are excluded from future training runs. |
| **Access control** | Photos are stored with non-guessable paths and served via time-limited signed URLs. No public access to the storage bucket. |
| **EXIF data** | Stripped on upload. GPS coordinates, device model, and other metadata are removed before storage. Location data comes from the user's registered postcode, not from photo metadata. |
| **Thumbnails** | Generated on upload for quick loading. Same retention and deletion policy as full-size images. |

### 8.5 Authentication and Authorisation

| Channel | Auth Method |
|---------|-------------|
| **WhatsApp** | Implicit — the phone number is the identity. Webhook signature verification ensures messages genuinely came from Meta. |
| **Mobile App (Phase 2)** | Phone number verification via SMS OTP (links WhatsApp identity to app identity). JWT tokens with short expiry (1 hour access, 30 day refresh). |
| **Internal APIs** | Service-to-service authentication via shared secrets (MVP) → mTLS (scale). |
| **Admin Access** | Separate admin API with MFA. No admin access to raw conversation content — only anonymised metrics and aggregate data. |

---

## 9. Scalability Considerations

### 9.1 Scaling Stages

**Stage 1: 0-1,000 Users (MVP / First 6 Months)**

- **Architecture:** Single server, single PostgreSQL instance, single Redis instance.
- **Hosting:** Railway (Hobby → Pro plan). Single FastAPI process with 4 Uvicorn workers.
- **Database:** Single PostgreSQL instance (Railway managed). No partitioning needed.
- **Processing:** ARQ workers on the same server. 2-3 workers handle message processing and background tasks.
- **Bottleneck:** Claude API rate limits, not infrastructure. At 1,000 daily active users sending 3 messages each, that is 3,000 Claude API calls/day — well within standard rate limits.
- **Cost estimate per user:** Approximately £0.15-0.25/month (Claude API: £0.10, WhatsApp: £0.05, infrastructure: £0.05-0.10).

**Stage 2: 1,000-10,000 Users (Growth Phase)**

- **Architecture:** Separate web server and worker processes. May split to 2-3 server instances behind a load balancer.
- **Hosting:** Railway Pro or migrate to AWS ECS Fargate (auto-scaling task definitions).
- **Database:** PostgreSQL on a dedicated managed instance (AWS RDS or equivalent). Add read replicas for API queries. Connection pooling via PgBouncer.
- **Redis:** Dedicated instance with persistence enabled. Consider Redis Cluster if pub/sub volume demands it.
- **Processing:** Dedicated worker fleet (3-5 instances). Separate queues for time-sensitive (inbound messages) and background (weather checks, CV analysis) tasks.
- **Object Storage:** Already scalable (R2/S3 handles this natively).
- **Cost estimate per user:** £0.10-0.18/month at scale (API costs decrease with batching, infrastructure cost per user drops significantly).

**Stage 3: 10,000-100,000 Users (Scale Phase)**

- **Architecture:** Full microservice split: API gateway, message processing service, agent service, CV pipeline service, notification service.
- **Hosting:** AWS ECS Fargate or Kubernetes (EKS). Auto-scaling based on queue depth and API latency.
- **Database:** PostgreSQL with table partitioning (see 9.3). Consider read replicas per microservice. Evaluate whether the context graph benefits from a dedicated time-series or graph database (TimescaleDB or similar) — but only migrate if PostgreSQL's performance becomes a measured bottleneck.
- **Caching:** Redis Cluster. Aggressive caching of weather data, plant specs, growing calendars. Cache-aside pattern with invalidation on writes.
- **CV Pipeline:** Dedicated processing fleet with GPU instances for the classifier model. Queue-based with autoscaling. Claude vision calls load-balanced across API keys.
- **CDN:** CloudFront (or Cloudflare) in front of object storage for photo serving in the mobile app.
- **Cost estimate per user:** £0.06-0.12/month (significant economies of scale).

### 9.2 Cost Per User Breakdown (Estimated, Stage 1)

| Component | Monthly Cost Per Active User | Calculation Basis |
|-----------|------------------------------|-------------------|
| **Claude API** | £0.08-0.12 | ~90 messages/month (3/day), avg 1,500 input tokens + 500 output tokens per call. Sonnet pricing. Some calls invoke tools (additional tokens). |
| **WhatsApp** | £0.03-0.06 | ~3 business-initiated conversations/week (alerts) + user-initiated sessions. UK pricing tier. |
| **Object Storage** | £0.005 | ~4 photos/month, 2MB each, stored for 12 months. R2 zero-egress pricing. |
| **Infrastructure** | £0.03-0.06 | Railway Pro plan amortised across user base. Decreases per user as base grows. |
| **Weather API** | £0.00 | Open-Meteo is free. Met Office has generous free tier. |
| **Total** | **£0.15-0.25** | Conservative estimate for active users |

**Key cost driver:** Claude API usage. Optimisation strategies:
- Cache common queries (e.g., general growing advice for common plants) as pre-computed responses.
- Use Haiku for simple classification tasks (intent routing, photo triage) and Sonnet only for complex reasoning.
- Batch background processing (weather checks for all users in a region in a single sweep, not individual calls).
- Summarise conversation history aggressively to reduce input token count.

### 9.3 Database Partitioning Strategy

**Tables that grow unboundedly:**

| Table | Partitioning Strategy | Trigger Point |
|-------|----------------------|---------------|
| `context_event` | Range partition by `created_at` (monthly) | >10M rows or query latency >100ms on time-range scans |
| `alert` | Range partition by `scheduled_for` (monthly) | >5M rows. Old partitions can be archived or dropped after 12 months. |
| `photo_record` | Range partition by `created_at` (quarterly) | >1M rows |
| `conversation_message` | Range partition by `created_at` (monthly) + purge after 90 days | >10M rows |

**Tables that scale linearly with users (manageable):**

| Table | Strategy | Notes |
|-------|----------|-------|
| `user` | Single table, indexed | Even at 100K users, this is a small table |
| `garden` | Single table, indexed on `user_id` | ~2 gardens per user average |
| `plant` | Single table, indexed on `garden_id` | ~15 plants per user average |
| `achievement` | Single table, indexed on `user_id` | ~20 per user over time |

**Reference data tables** (PlantSpec, GrowingCalendar, CompanionPlantingRule) are read-heavy, rarely written, and small enough to cache entirely in Redis.

**Index strategy:**
- Composite indexes on frequently filtered queries: `(user_id, created_at DESC)` on context_event, alert, photo_record.
- GIN index on JSONB columns used in queries (e.g., `preferences`, `cv_analysis`).
- pgvector HNSW index on `context_event.embedding` for semantic search.
- Partial indexes where applicable: `WHERE is_active = true` on plant, `WHERE delivery_status = 'pending'` on alert.

### 9.4 Resilience and Failure Handling

| Failure Scenario | Mitigation |
|------------------|------------|
| **Claude API outage** | Graceful degradation. Queue inbound messages, send acknowledgement: "Sage is thinking — I'll get back to you shortly." Process queue when API recovers. For alerts, fall back to template-only messages without personalisation. |
| **WhatsApp API outage** | Outbound messages retry with exponential backoff (1s, 2s, 4s, 8s, max 5 minutes). Failed messages requeued. Dead letter queue after 10 attempts. |
| **Database failure** | Managed PostgreSQL with automatic failover (Railway/RDS). Application retries with circuit breaker pattern. |
| **Redis failure** | Conversations continue (slightly slower, loading full context from PostgreSQL). Background tasks pause and resume when Redis recovers. |
| **CV pipeline backlog** | Photos queued, analysis deferred. User receives immediate acknowledgement: "Photo received — I'll analyse it and get back to you." Process when capacity available. |
| **Webhook delivery failure** | Meta retries webhooks for up to 7 days. Idempotent message processing (deduplicate on `message_id`) handles duplicates. |

---

This architecture is designed to be built incrementally: Phase 1 (WhatsApp MVP) requires only the core API gateway, Sage Orchestrator, a subset of agent tools, PostgreSQL, and Redis. Every other component (CV pipeline, mobile app API, advanced partitioning, microservice split) layers on top without rearchitecting what already works.