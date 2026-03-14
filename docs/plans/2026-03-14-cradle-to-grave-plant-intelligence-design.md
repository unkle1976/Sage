# Cradle-to-Grave Plant Intelligence — Design Document

**Date**: 14 March 2026
**Status**: Approved
**Scope**: Data model redesign, proactive engagement engine, postcode fix, photo intelligence

---

## 1. Vision

Sage is a high-end personal trainer for your garden. Not a notification system, not a dashboard, not an app — a mate who knows your garden, watches the weather, remembers what worked last year, and texts you when something needs attention.

The long-term moat is the **UK gardening intelligence dataset** — structured, location-specific, season-over-season, outcome-tracked growing data correlated with weather, soil, and care actions. Nobody has this. Within 2-3 seasons, Sage can answer questions nobody else can: "What's the best tomato variety for DN35 on silty clay?" or "Does potash actually improve courgette yields?"

### Architecture (Three-Layer, No Middleware)

```
AI/Agent Layer  →  Sage (reasoning, proactive engagement, photo analysis)
Context Layer   →  Rich event stream — everything that happened, why, weather at the time
Data Layer      →  PostgreSQL (identity + context events) + Redis (scheduling + cache)
```

No app. No dashboard. WhatsApp is the pipe. The AI is the interface.

---

## 2. Data Model — Context-First Architecture

### Design Principle

Don't build tables for humans to query. Build a rich context stream for AI to reason over. Future models will reason over semi-structured event streams far better than SQL joins across normalised tables.

### Thin Identity Layer (relational, boring, necessary)

These tables already exist and stay largely unchanged:

- **User** — who, where, soil type, experience, preferences
- **Garden** — growing spaces (type, orientation, microclimate)
- **Plant** — individual plantings, linked to specs and seasons
- **PlantSpec** — reference catalogue (50 UK plants seeded)
- **GrowingCalendar** — regional sow/transplant/harvest schedules

### Modifications to Plant Model

```
Plant (existing — add these fields)
  + growing_season_id    FK → GrowingSeason
  + parent_plant_id      FK → self (nullable) — lineage tracking
  + seed_source          enum: saved_seed | bought | gifted | grown
  + final_outcome        enum: success | partial | failed | abandoned
  + yield_total_kg       decimal (nullable) — aggregated from context events
  + season_notes         text — end-of-season reflection
```

**Lineage example**:
```
Season 2026: Plant(variety="Moneymaker", seed_source="bought", final_outcome="success", yield=4.2kg)
    ↓ parent_plant_id
Season 2027: Plant(variety="Moneymaker", seed_source="saved_seed")
    → Sage: "You saved seed from last year's Moneymaker — nice!
       They yielded 4.2kg. Let's beat that."
```

### New Tables

#### GrowingSeason
```
id              UUID PK
user_id         FK → users
year            int (2026, 2027...)
label           str ("Spring/Summer 2026")
started_at      date
ended_at        date (nullable — null = current season)
season_summary  JSONB — auto-generated at season end
weather_summary JSONB — avg temps, total rainfall for their postcode
```

#### EngagementProfile
```
id                      UUID PK
user_id                 FK → users (one-to-one)
preferred_time          str: "morning" | "evening" | "anytime"
notification_level      str: "alerts_only" | "normal" | "chatty"
quiet_hours_start       time (nullable)
quiet_hours_end         time (nullable)
last_sage_initiated_at  datetime
last_user_message_at    datetime
```

Everything else about the user's personality, what they respond to, how they like to chat — that lives in the context stream. Sage reads the events and conversation history and figures it out, like a mate would.

### The Context Stream (The Moat)

**ContextEvent** already exists and is solid. It becomes the single source of truth for everything that happens in a garden. Minor additions:

```
ContextEvent (existing — add these fields)
  + weather_snapshot    JSONB — auto-captured temp/rain/wind at event time
```

**All activity flows through ContextEvent** as structured event types:

| event_type | detail JSONB example | source |
|---|---|---|
| `planting` | `{"variety": "Moneymaker", "method": "seed", "location": "raised bed 1"}` | user_reported |
| `care_watering` | `{"method": "hose", "duration_mins": 15}` | user_reported |
| `care_feeding` | `{"product": "Potash", "brand": "Vitax", "quantity": "handful", "dilution": "10g/L"}` | user_reported |
| `care_pruning` | `{"action": "pinched out side shoots"}` | user_reported |
| `care_treatment` | `{"product": "Copper spray", "target": "blight", "brand": "Vitax"}` | user_reported |
| `care_mulching` | `{"material": "bark chips", "depth_cm": 5}` | user_reported |
| `growth_stage_change` | `{"from": "seedling", "to": "established", "days_in_previous": 21, "expected_days": 18}` | sage_observed |
| `harvest` | `{"quantity_kg": 0.5, "quantity_desc": "2 large courgettes", "quality": 4, "taste_notes": "great"}` | user_reported |
| `problem_observed` | `{"issue": "yellowing leaves", "severity": "mild", "location": "lower leaves"}` | user_reported / sage_observed |
| `problem_diagnosed` | `{"diagnosis": "magnesium deficiency", "confidence": 0.8, "recommendation": "Epsom salts"}` | sage_inferred |
| `photo_observation` | `{"growth_stage_observed": "flowering", "health": "healthy", "issues": [], "notable": ["first flowers"]}` | sage_observed |
| `weather_alert` | `{"alert_type": "frost", "min_temp": -2, "when": "tonight"}` | sage_system |
| `sage_advice` | `{"topic": "feeding", "recommendation": "potash feed", "context": "heavy feeder, 6 weeks in"}` | sage_initiated |
| `season_end` | `{"final_outcome": "success", "total_yield_kg": 4.2, "learnings": "..."}` | sage_generated |
| `product_recommendation` | `{"product": "Nitrachalk", "purpose": "nitrogen feed for clay soil", "where_to_buy": "Wilko, ~£4"}` | sage_initiated |

**Every event auto-captures `weather_snapshot`** from Open-Meteo at the time of the event. This is the ML gold — correlating care actions with weather conditions and outcomes.

### WeatherLog (daily cache for correlation)

```
WeatherLog
  id                  UUID PK
  postcode_outward    str (indexed)
  date                date (indexed)
  temp_max_c          decimal
  temp_min_c          decimal
  rainfall_mm         decimal
  wind_max_kmh        decimal
  sunshine_hours      decimal
  frost               bool
  (unique constraint: postcode_outward + date)
```

Populated daily by the scheduler for all active postcodes. Allows historical weather correlation without re-calling the API.

### What This Enables for ML (Future)

| Question | How the context stream answers it |
|---|---|
| Best tomato variety for DN35 on clay? | Filter context events: `planting` + `season_end` by postcode + soil → compare `final_outcome` + `yield_total_kg` across varieties |
| Does potash improve yields? | Compare plants with `care_feeding` events (product=potash) vs without → correlate with `harvest` events |
| When should Midlands growers really sow? | `planting` events + `growth_stage_change` (to germinating) + `weather_snapshot` → actual germination success by date and weather |
| Why do beginners lose tomatoes? | `problem_observed` + `problem_diagnosed` events for users with experience_level=novice → pattern extraction |
| What feeding schedule maximises courgette yield? | Sequence of `care_feeding` events per plant → correlate timing/product with `harvest` totals |

---

## 3. Proactive Engagement Engine — "Sage as a Mate"

### Three Trigger Types

**1. Urgent — weather-driven (send immediately)**
- Frost tonight, heatwave, storm, heavy rain after dry spell
- Always sent regardless of notification_level (except quiet hours)

**2. Timely — growth stage / care-driven (within a window)**
- Plants due stage transition, feeding overdue, harvest window
- Sent at preferred_time, respects notification_level

**3. Sporadic — the mate check-in (random, human-feeling)**
- Haven't heard from user, seasonal nudge, celebration, learning moment
- Weighted random chance, never forced

### The Sporadic Algorithm

```python
days_since_contact = (now - last_interaction).days

if days_since_contact <= 2:
    chance = 0.05    # 5% — active, leave them be
elif days_since_contact <= 5:
    chance = 0.15    # 15% — gentle nudge territory
elif days_since_contact <= 14:
    chance = 0.30    # 30% — "haven't heard from you"
else:
    chance = 0.50    # 50% — re-engagement

# Seasonal weighting
if current_month in (11, 12, 1, 2):
    chance *= 0.3    # Winter — mostly quiet
elif current_month in (3, 4, 5, 6):
    chance *= 1.5    # Spring/early summer — lots happening
```

### Anti-Nag Rules (Critical)

1. **One message, whole garden** — never per-plant messages
2. **Short** — 2-3 sentences max. It's WhatsApp, not an essay
3. **Only ask one question** — "how's it looking?" not per-plant interrogation
4. **Don't expect a reply** — if they reply, great. If not, don't follow up
5. **Vary the tone** — practical, curious, celebratory. Not robotic
6. **Bundle everything** — frost warning + care reminder = one message
7. **Never more than `max_messages_per_day`** (default: 2, configurable)
8. **Urgent overrides all** — but still bundles with other pending messages
9. **Sporadic only if no other message sent that day**
10. **Respect quiet hours** — queue for next preferred time

### Message Generation

Messages are NOT templates. When the scheduler triggers an outbound, Sage (Claude) gets:
- All active plants, their stages, when last mentioned
- Recent weather for their postcode
- Last 10 context events
- Recent conversation history
- Time of year, what should be happening
- User's experience level

Then Claude generates a natural, contextual message. Every nudge is unique.

**Good**: "How's the garden? Your tomatoes should be flowering by now and those courgettes will want a feed soon. Oh and your radishes are probably ready to pull — have a look! 🌱"

**Bad**: "Reminder: water your tomatoes. Reminder: feed your courgettes. Reminder: harvest your radishes."

### Scheduler Architecture

```
Redis Queue (hourly check)
  │
  ├── For each active user:
  │   ├── Check EngagementProfile (preferences, cooldowns)
  │   ├── Check URGENT triggers (weather API)
  │   ├── Check TIMELY triggers (plant stages, care gaps)
  │   ├── Check SPORADIC triggers (weighted random)
  │   ├── Bundle all triggers into single context
  │   └── If triggering: generate message via Claude → send via WhatsApp
  │
  └── Anti-spam enforcement at queue level
```

---

## 4. Postcode Fix

### Problem
postcodes.io `/postcodes/{code}` requires full postcodes. Outward codes like "DN35" or "B44" return 404.

### Solution
Fallback to `/outcodes/{outcode}` endpoint:

```
User types postcode
  → Normalise: uppercase, handle "dn358lz" → "DN35 8LZ", "dn35" → "DN35"
  → Try /postcodes/{input} (full postcode?)
    → 200: store outward code + lat/lon/region ✅
  → Try /outcodes/{input} (outward code?)
    → 200: store outward code + lat/lon/region ✅
  → Both fail: "Hmm, couldn't find that postcode. Try your full postcode like DN35 8LZ"
```

### Fuzzy Input Handling
- `"dn35"` → uppercase → `"DN35"`
- `"dn358lz"` → insert space → `"DN35 8LZ"`
- `"DN 35"` → strip inner spaces for outcode → `"DN35"`
- `"  dn35 8lz  "` → strip + uppercase → `"DN35 8LZ"`

---

## 5. Photo Intelligence

### Flow (all via WhatsApp)

1. **User sends photo** → WhatsApp webhook receives media
2. **Sage analyses** (Claude Vision) with full plant context
3. **Responds naturally**: "Looking good! Those leaves are a healthy green. I can see it's starting to flower — exciting!"
4. **Logs to context stream**: `photo_observation` event with structured analysis
5. **If problems spotted**: diagnosis + product recommendation logged as separate events
6. **Over time**: comparison with previous photos, growth tracking

### Context Event Logging

```json
{
  "event_type": "photo_observation",
  "plant_id": "uuid",
  "detail": {
    "growth_stage_observed": "flowering",
    "health_assessment": "healthy",
    "issues": [],
    "notable_features": ["strong stem", "first flowers visible"],
    "comparison_note": "significant growth since photo 3 weeks ago"
  },
  "weather_snapshot": {"temp_c": 18, "rainfall_last_24h_mm": 2},
  "photo_id": "uuid"
}
```

### Problem → Product Recommendation Pipeline

```
Photo shows white spots on leaves
  → sage_observed: "photo_observation" (issues: ["powdery mildew suspect"])
  → sage_inferred: "problem_diagnosed" (diagnosis: "powdery mildew", confidence: 0.75)
  → sage_initiated: "product_recommendation" (product: "Fungus Fighter", where: "Wilko ~£5")
  → User message: "I can see some white powdery spots on those leaves — looks like
     powdery mildew. Dead common, easy fix. Grab some Fungus Fighter from Wilko
     (about a fiver) and spray the leaves. Should clear up in a week or two."
```

### Future: Business Tie-Ins
- Affiliate links to garden centres / online retailers
- Local garden centre partnerships ("Dave's Garden Centre in Grimsby stocks this")
- Sponsored product recommendations (clearly marked)
- Aggregate anonymised data: "70% of growers on clay soil in the Midlands use Nitrachalk — here's why"

---

## 6. Summary of Changes Required

### Database Migrations
1. Add `growing_season_id`, `parent_plant_id`, `seed_source`, `final_outcome`, `yield_total_kg`, `season_notes` to `Plant`
2. Create `GrowingSeason` table
3. Create `EngagementProfile` table
4. Create `WeatherLog` table
5. Add `weather_snapshot` to `ContextEvent`

### Services (New)
1. **EngagementService** — manages proactive outreach logic, anti-nag rules
2. **SchedulerService** — hourly check loop, trigger evaluation, message generation
3. **PhotoAnalysisService** — Claude Vision integration, structured observation logging

### Services (Modified)
1. **PostcodeService** — add outcode fallback + fuzzy input normalisation
2. **WeatherService** — add daily weather logging for active postcodes
3. **OnboardingService** — use fixed postcode service

### Agent (Modified)
1. **SageOrchestrator** — new tools: `log_care_event`, `update_growth_stage`, `log_harvest`, `analyse_photo`
2. **System prompt** — incorporate proactive engagement personality, anti-nag rules, whole-garden messaging

### Infrastructure
- Redis already running — add task queue (APScheduler or Celery)
- No new infrastructure required
