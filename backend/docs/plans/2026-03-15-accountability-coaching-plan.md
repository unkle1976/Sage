# Accountability Coaching & Growing Plan — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make Sage a proactive accountability partner that checks in based on plant growth milestones, weather conditions, and a personalised growing plan — like an Ultimate Performance PT for your garden.

**Architecture:** Plant milestones drive the *what* (growth stages trigger check-ins), the existing ARQ scheduler drives the *when* (hourly cron evaluates triggers), and Claude Haiku generates weather-fused, location-specific messages. A new GrowingPlanItem model tracks the user's seasonal wishlist. Engagement tracking prevents over-messaging and adapts frequency based on user responsiveness.

**Tech Stack:** Python 3.12, SQLAlchemy (async), Alembic, PostgreSQL (JSONB), ARQ, Redis streams, Claude Haiku, Slack Bolt SDK

**Design doc:** `docs/plans/2026-03-15-accountability-coaching-design.md`

---

## Task 1: Schema Changes — PlantSpec, Plant, EngagementProfile

Add growth milestone and engagement tracking fields to existing models.

**Files:**
- Modify: `app/models/plant_spec.py`
- Modify: `app/models/plant.py`
- Modify: `app/models/engagement_profile.py`
- Test: `tests/test_accountability_models.py`

**Step 1: Write the failing tests**

```python
# tests/test_accountability_models.py
from app.models.plant_spec import PlantSpec
from app.models.plant import Plant
from app.models.engagement_profile import EngagementProfile

def test_plant_spec_has_growth_milestones():
    ps = PlantSpec(common_name="Tomato", category="vegetable")
    ps.growth_milestones = [{"day": 7, "stage": "sprouting", "check_in": "Seeds should be germinating"}]
    assert ps.growth_milestones[0]["day"] == 7

def test_plant_spec_has_interesting_facts():
    ps = PlantSpec(common_name="Tomato", category="vegetable")
    ps.interesting_facts = ["Tomatoes are technically a fruit"]
    assert len(ps.interesting_facts) == 1

def test_plant_has_milestone_tracking():
    p = Plant()
    p.next_milestone_index = 2
    assert p.next_milestone_index == 2
    p.milestone_delayed = True
    assert p.milestone_delayed is True

def test_engagement_profile_has_unanswered_count():
    ep = EngagementProfile()
    ep.unanswered_count = 3
    assert ep.unanswered_count == 3

def test_engagement_profile_has_current_frequency():
    ep = EngagementProfile()
    ep.current_frequency = "reduced"
    assert ep.current_frequency == "reduced"
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_accountability_models.py -v`
Expected: FAIL — attributes don't exist yet

**Step 3: Add fields to PlantSpec**

In `app/models/plant_spec.py`, add after `notes`:

```python
growth_milestones: Mapped[list | None] = mapped_column(JSONB, nullable=True)
interesting_facts: Mapped[list | None] = mapped_column(JSONB, nullable=True)
```

**Step 4: Add fields to Plant**

In `app/models/plant.py`, add after `milestone_delayed` or after existing fields:

```python
next_milestone_index: Mapped[int] = mapped_column(SmallInteger, server_default="0")
next_milestone_date: Mapped[date | None] = mapped_column(Date, nullable=True)
milestone_delayed: Mapped[bool] = mapped_column(Boolean, server_default="false")
```

**Step 5: Add fields to EngagementProfile**

In `app/models/engagement_profile.py`, add after existing fields:

```python
unanswered_count: Mapped[int] = mapped_column(SmallInteger, server_default="0")
current_frequency: Mapped[str] = mapped_column(String(20), server_default="normal")
```

**Step 6: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_accountability_models.py -v`
Expected: PASS

**Step 7: Commit**

```bash
git add app/models/plant_spec.py app/models/plant.py app/models/engagement_profile.py tests/test_accountability_models.py
git commit -m "feat: add growth milestone and engagement tracking fields to models"
```

---

## Task 2: GrowingPlanItem Model

New model for the seasonal planting wishlist/queue.

**Files:**
- Create: `app/models/growing_plan_item.py`
- Modify: `app/models/__init__.py` (add import)
- Test: `tests/test_growing_plan_model.py`

**Step 1: Write the failing test**

```python
# tests/test_growing_plan_model.py
from datetime import date
from app.models.growing_plan_item import GrowingPlanItem

def test_growing_plan_item_creation():
    item = GrowingPlanItem()
    item.status = "queued"
    item.optimal_sow_start = date(2026, 3, 15)
    item.optimal_sow_end = date(2026, 4, 30)
    assert item.status == "queued"

def test_growing_plan_item_statuses():
    for status in ["queued", "ready", "active", "too_late", "skipped"]:
        item = GrowingPlanItem()
        item.status = status
        assert item.status == status

def test_growing_plan_item_has_alternative():
    item = GrowingPlanItem()
    item.suggested_alternative_id = None
    assert item.suggested_alternative_id is None
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_growing_plan_model.py -v`
Expected: FAIL — module doesn't exist

**Step 3: Create the model**

```python
# app/models/growing_plan_item.py
from __future__ import annotations
import uuid
from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class GrowingPlanItem(Base):
    __tablename__ = "growing_plan_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plant_spec_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("plant_specs.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), server_default="queued")
    optimal_sow_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    optimal_sow_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    suggested_alternative_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plant_specs.id"), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

**Step 4: Add import to `app/models/__init__.py`**

Add: `from app.models.growing_plan_item import GrowingPlanItem`

**Step 5: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_growing_plan_model.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add app/models/growing_plan_item.py app/models/__init__.py tests/test_growing_plan_model.py
git commit -m "feat: add GrowingPlanItem model for seasonal planting queue"
```

---

## Task 3: Alembic Migration

Generate and apply migration for all schema changes from Tasks 1-2.

**Files:**
- Create: `alembic/versions/<auto>_add_accountability_coaching_fields.py`

**Step 1: Generate migration**

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
source .venv/bin/activate
alembic revision --autogenerate -m "add accountability coaching fields and growing plan items"
```

**Step 2: Review the generated migration**

Check it includes:
- `growth_milestones` and `interesting_facts` JSONB columns on `plant_specs`
- `next_milestone_index`, `next_milestone_date`, `milestone_delayed` on `plants`
- `unanswered_count`, `current_frequency` on `engagement_profiles`
- New `growing_plan_items` table

**Step 3: Apply migration**

```bash
alembic upgrade head
```

**Step 4: Verify**

```bash
python -c "
import asyncio
from app.core.database import async_session
from sqlalchemy import text
async def check():
    async with async_session() as s:
        r = await s.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='plant_specs' AND column_name='growth_milestones'\"))
        print('growth_milestones exists:', r.scalar() is not None)
        r = await s.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='growing_plan_items' AND column_name='status'\"))
        print('growing_plan_items exists:', r.scalar() is not None)
asyncio.run(check())
"
```

**Step 5: Commit**

```bash
git add alembic/versions/
git commit -m "feat: migration for accountability coaching schema changes"
```

---

## Task 4: Seed PlantSpec Growth Milestones & Facts

Populate growth milestones and interesting facts for the most common UK edible plants.

**Files:**
- Create: `app/data/plant_milestones.py`
- Test: `tests/test_plant_milestones.py`

**Step 1: Write the test**

```python
# tests/test_plant_milestones.py
from app.data.plant_milestones import PLANT_MILESTONES

def test_milestones_have_required_keys():
    for plant_name, data in PLANT_MILESTONES.items():
        assert "milestones" in data, f"{plant_name} missing milestones"
        assert "facts" in data, f"{plant_name} missing facts"
        for m in data["milestones"]:
            assert "day" in m, f"{plant_name} milestone missing day"
            assert "stage" in m, f"{plant_name} milestone missing stage"
            assert "check_in" in m, f"{plant_name} milestone missing check_in"

def test_milestones_are_ordered_by_day():
    for plant_name, data in PLANT_MILESTONES.items():
        days = [m["day"] for m in data["milestones"]]
        assert days == sorted(days), f"{plant_name} milestones not in day order"

def test_weather_gates_are_valid():
    for plant_name, data in PLANT_MILESTONES.items():
        for m in data["milestones"]:
            if "weather_gate" in m:
                gate = m["weather_gate"]
                assert any(k in gate for k in ["min_temp", "max_temp", "no_frost"]), \
                    f"{plant_name} milestone has invalid weather_gate"

def test_minimum_plant_coverage():
    """We need at least 10 common UK edible plants"""
    assert len(PLANT_MILESTONES) >= 10
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_plant_milestones.py -v`
Expected: FAIL — module doesn't exist

**Step 3: Create milestone data**

Create `app/data/__init__.py` (empty) and `app/data/plant_milestones.py` with growth timelines for at least these plants: tomato, cucumber, lettuce, strawberry, basil, courgette, runner beans, chilli pepper, radish, peas, beetroot, rocket, spring onion, mint, parsley.

Each entry should have:
- `milestones`: list of `{day, stage, check_in, weather_gate?}` — realistic UK growing timelines
- `facts`: list of 3-5 interesting facts per plant
- `sow_method`: "indoor" or "outdoor" or "either"

Use real horticultural data. Example for tomato:

```python
PLANT_MILESTONES = {
    "tomato": {
        "sow_method": "indoor",
        "milestones": [
            {"day": 0, "stage": "planted", "check_in": "Seeds sown"},
            {"day": 10, "stage": "sprouting", "check_in": "Seeds should be germinating — look for tiny green shoots"},
            {"day": 28, "stage": "seedling", "check_in": "Seedlings should have their first true leaves — the serrated ones, not the smooth seed leaves"},
            {"day": 42, "stage": "potting_on", "check_in": "Time to move seedlings into bigger pots — they need more root room now"},
            {"day": 56, "stage": "hardening_off", "check_in": "Start getting plants used to outside — a few hours in a sheltered spot each day",
             "weather_gate": {"min_temp": 10, "no_frost": True}},
            {"day": 70, "stage": "transplant", "check_in": "Ready to plant outside permanently — in the ground or big pots",
             "weather_gate": {"min_temp": 12, "no_frost": True}},
            {"day": 90, "stage": "flowering", "check_in": "Yellow flowers appearing — fruit is on its way"},
            {"day": 120, "stage": "fruiting", "check_in": "Green tomatoes forming — keep watering consistently"},
            {"day": 150, "stage": "ripening", "check_in": "Tomatoes starting to change colour — nearly there"},
            {"day": 160, "stage": "harvest", "check_in": "First ripe tomatoes — pick them when they're fully coloured and slightly soft to touch"},
        ],
        "facts": [
            "Tomatoes are technically a fruit — they're berries, in fact",
            "The tomato plant is related to deadly nightshade, which is why the leaves smell so distinctive",
            "Homegrown tomatoes have about 3x more flavour compounds than supermarket ones because they're picked ripe",
            "Pinching out the side shoots between the main stem and branches focuses energy into fruit production",
            "Irregular watering is the main cause of split tomatoes — consistency matters more than quantity",
        ],
    },
    # ... more plants
}
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_plant_milestones.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/data/__init__.py app/data/plant_milestones.py tests/test_plant_milestones.py
git commit -m "feat: add growth milestone data for 15 UK edible plants"
```

---

## Task 5: Milestone Trigger Logic in Proactive Scheduler

Enhance the existing proactive scheduler to check plant milestones and weather-gate them.

**Files:**
- Modify: `app/tasks/proactive_scheduler.py`
- Create: `app/services/milestone_checker.py`
- Test: `tests/test_milestone_checker.py`

**Step 1: Write the failing tests**

```python
# tests/test_milestone_checker.py
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.services.milestone_checker import MilestoneChecker

@pytest.fixture
def checker():
    return MilestoneChecker()

def _make_plant(planting_date, milestone_index=0, milestones=None, delayed=False):
    plant = MagicMock()
    plant.planting_date = planting_date
    plant.next_milestone_index = milestone_index
    plant.milestone_delayed = delayed
    plant.variety = "Test Plant"
    plant.growth_stage = "seed"
    spec = MagicMock()
    spec.growth_milestones = milestones or [
        {"day": 7, "stage": "sprouting", "check_in": "Should be sprouting"},
        {"day": 21, "stage": "seedling", "check_in": "Seedlings growing"},
    ]
    spec.common_name = "Tomato"
    plant.plant_spec = spec
    return plant

def test_milestone_due_today(checker):
    plant = _make_plant(planting_date=date.today() - timedelta(days=7), milestone_index=0)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 1
    assert due[0]["stage"] == "sprouting"

def test_milestone_not_yet_due(checker):
    plant = _make_plant(planting_date=date.today() - timedelta(days=3), milestone_index=0)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 0

def test_milestone_overdue_still_triggers(checker):
    plant = _make_plant(planting_date=date.today() - timedelta(days=10), milestone_index=0)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 1

def test_weather_gate_blocks_milestone(checker):
    milestones = [
        {"day": 7, "stage": "hardening_off", "check_in": "Put outside",
         "weather_gate": {"min_temp": 10, "no_frost": True}},
    ]
    plant = _make_plant(planting_date=date.today() - timedelta(days=7), milestones=milestones)
    weather = {"temp_min_c": 4, "frost": True}
    due = checker.get_due_milestones([plant], date.today(), weather=weather)
    assert len(due) == 1
    assert due[0]["delayed"] is True

def test_weather_gate_passes(checker):
    milestones = [
        {"day": 7, "stage": "hardening_off", "check_in": "Put outside",
         "weather_gate": {"min_temp": 10}},
    ]
    plant = _make_plant(planting_date=date.today() - timedelta(days=7), milestones=milestones)
    weather = {"temp_min_c": 14, "frost": False}
    due = checker.get_due_milestones([plant], date.today(), weather=weather)
    assert len(due) == 1
    assert due[0]["delayed"] is False

def test_no_milestones_if_spec_has_none(checker):
    plant = _make_plant(planting_date=date.today() - timedelta(days=7), milestones=None)
    plant.plant_spec.growth_milestones = None
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 0

def test_skips_already_passed_milestones(checker):
    plant = _make_plant(planting_date=date.today() - timedelta(days=25), milestone_index=1)
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 1
    assert due[0]["stage"] == "seedling"
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_milestone_checker.py -v`
Expected: FAIL — module doesn't exist

**Step 3: Implement MilestoneChecker**

```python
# app/services/milestone_checker.py
from __future__ import annotations
from datetime import date, timedelta

class MilestoneChecker:
    def get_due_milestones(
        self,
        plants: list,
        today: date,
        weather: dict | None = None,
    ) -> list[dict]:
        """Check which plants have milestones due today or overdue."""
        due = []
        for plant in plants:
            spec = getattr(plant, "plant_spec", None)
            if not spec or not spec.growth_milestones or not plant.planting_date:
                continue

            milestones = spec.growth_milestones
            idx = plant.next_milestone_index or 0

            if idx >= len(milestones):
                continue

            milestone = milestones[idx]
            milestone_date = plant.planting_date + timedelta(days=milestone["day"])

            if milestone_date > today:
                continue

            # Milestone is due or overdue
            delayed = False
            gate = milestone.get("weather_gate")
            if gate and weather:
                if gate.get("min_temp") and weather.get("temp_min_c", 99) < gate["min_temp"]:
                    delayed = True
                if gate.get("no_frost") and weather.get("frost"):
                    delayed = True

            due.append({
                "plant": plant,
                "plant_name": spec.common_name,
                "variety": plant.variety,
                "stage": milestone["stage"],
                "check_in": milestone["check_in"],
                "milestone_index": idx,
                "delayed": delayed,
                "days_since_planting": (today - plant.planting_date).days,
            })

        return due
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_milestone_checker.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/milestone_checker.py tests/test_milestone_checker.py
git commit -m "feat: add MilestoneChecker service for growth stage tracking"
```

---

## Task 6: Engagement Frequency Adaptation

Enhance EngagementService to track unanswered messages and adapt frequency.

**Files:**
- Modify: `app/services/engagement.py`
- Test: `tests/test_engagement_frequency.py`

**Step 1: Write the failing tests**

```python
# tests/test_engagement_frequency.py
from app.services.engagement import EngagementService

def test_frequency_normal_at_zero_unanswered():
    freq = EngagementService.get_frequency_for_unanswered(0)
    assert freq == "normal"

def test_frequency_normal_at_one_unanswered():
    freq = EngagementService.get_frequency_for_unanswered(1)
    assert freq == "normal"

def test_frequency_normal_at_two_unanswered():
    """Two unanswered triggers gentle nudge but stays normal frequency"""
    freq = EngagementService.get_frequency_for_unanswered(2)
    assert freq == "normal"

def test_frequency_reduced_at_three_unanswered():
    freq = EngagementService.get_frequency_for_unanswered(3)
    assert freq == "reduced"

def test_frequency_minimal_at_four_plus_unanswered():
    freq = EngagementService.get_frequency_for_unanswered(4)
    assert freq == "minimal"
    freq = EngagementService.get_frequency_for_unanswered(10)
    assert freq == "minimal"

def test_should_nudge_at_two_unanswered():
    assert EngagementService.should_nudge(2) is True

def test_should_not_nudge_at_one_unanswered():
    assert EngagementService.should_nudge(1) is False

def test_should_not_nudge_at_three_unanswered():
    """At 3+ we reduce frequency, not nudge again"""
    assert EngagementService.should_nudge(3) is False

def test_min_days_between_for_normal():
    assert EngagementService.min_days_between("normal") == 3

def test_min_days_between_for_reduced():
    assert EngagementService.min_days_between("reduced") == 7

def test_min_days_between_for_minimal():
    assert EngagementService.min_days_between("minimal") == 14
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_engagement_frequency.py -v`
Expected: FAIL — methods don't exist

**Step 3: Add methods to EngagementService**

In `app/services/engagement.py`, add these static methods:

```python
@staticmethod
def get_frequency_for_unanswered(count: int) -> str:
    if count >= 4:
        return "minimal"
    if count >= 3:
        return "reduced"
    return "normal"

@staticmethod
def should_nudge(count: int) -> bool:
    return count == 2

@staticmethod
def min_days_between(frequency: str) -> int:
    return {"normal": 3, "reduced": 7, "minimal": 14}.get(frequency, 3)
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_engagement_frequency.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/engagement.py tests/test_engagement_frequency.py
git commit -m "feat: add engagement frequency adaptation for silence handling"
```

---

## Task 7: Growing Plan Service

Service for managing the seasonal planting queue — adding wishlist items, checking timing, suggesting alternatives.

**Files:**
- Create: `app/services/growing_plan.py`
- Test: `tests/test_growing_plan_service.py`

**Step 1: Write the failing tests**

```python
# tests/test_growing_plan_service.py
from datetime import date
from unittest.mock import MagicMock
from app.services.growing_plan import GrowingPlanService

def _make_calendar_entry(activity, month_start, month_end):
    entry = MagicMock()
    entry.activity = activity
    entry.month_start = month_start
    entry.month_end = month_end
    return entry

def _make_plant_spec(common_name):
    spec = MagicMock()
    spec.common_name = common_name
    spec.id = common_name  # simple for testing
    return spec

def test_check_timing_in_window():
    calendars = [_make_calendar_entry("sow_indoors", 3, 4)]
    result = GrowingPlanService.check_timing(calendars, date(2026, 3, 15))
    assert result["status"] == "ready"

def test_check_timing_too_late():
    calendars = [_make_calendar_entry("sow_indoors", 1, 2)]
    result = GrowingPlanService.check_timing(calendars, date(2026, 3, 15))
    assert result["status"] == "too_late"

def test_check_timing_future():
    calendars = [_make_calendar_entry("sow_indoors", 5, 6)]
    result = GrowingPlanService.check_timing(calendars, date(2026, 3, 15))
    assert result["status"] == "queued"

def test_prioritise_plan_orders_by_sow_date():
    items = [
        {"common_name": "Basil", "optimal_sow_start": date(2026, 5, 1)},
        {"common_name": "Tomato", "optimal_sow_start": date(2026, 3, 15)},
        {"common_name": "Strawberry", "optimal_sow_start": date(2026, 4, 1)},
    ]
    ordered = GrowingPlanService.prioritise(items)
    assert [i["common_name"] for i in ordered] == ["Tomato", "Strawberry", "Basil"]
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_growing_plan_service.py -v`
Expected: FAIL

**Step 3: Implement GrowingPlanService**

```python
# app/services/growing_plan.py
from __future__ import annotations
from datetime import date

class GrowingPlanService:

    @staticmethod
    def check_timing(calendar_entries: list, today: date) -> dict:
        """Check if a plant can still be sown based on growing calendar entries."""
        current_month = today.month

        # Find the latest applicable sow window
        latest_end = 0
        earliest_start = 13
        for entry in calendar_entries:
            if entry.activity in ("sow_indoors", "sow_outdoors"):
                if entry.month_end > latest_end:
                    latest_end = entry.month_end
                if entry.month_start < earliest_start:
                    earliest_start = entry.month_start

        if latest_end == 0:
            return {"status": "unknown"}

        if current_month > latest_end:
            return {"status": "too_late", "last_month": latest_end}
        elif current_month >= earliest_start:
            return {"status": "ready", "sow_start": earliest_start, "sow_end": latest_end}
        else:
            return {"status": "queued", "sow_start": earliest_start}

    @staticmethod
    def prioritise(items: list[dict]) -> list[dict]:
        """Order growing plan items by optimal sow start date."""
        return sorted(items, key=lambda x: x.get("optimal_sow_start", date.max))
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_growing_plan_service.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/services/growing_plan.py tests/test_growing_plan_service.py
git commit -m "feat: add GrowingPlanService for seasonal planting queue"
```

---

## Task 8: Orchestrator Tools — manage_growing_plan & advance_milestone

Add tools so the orchestrator can manage growing plans and update milestone progress during conversations.

**Files:**
- Modify: `app/agents/tools.py` (add tool definitions)
- Modify: `app/agents/tool_handlers.py` (add handlers)
- Test: `tests/test_growing_plan_tools.py`

**Step 1: Write the failing tests**

```python
# tests/test_growing_plan_tools.py
from app.agents.tools import TOOLS

def test_manage_growing_plan_tool_exists():
    names = [t["name"] for t in TOOLS]
    assert "manage_growing_plan" in names

def test_advance_milestone_tool_exists():
    names = [t["name"] for t in TOOLS]
    assert "advance_milestone" in names

def test_manage_growing_plan_schema():
    tool = next(t for t in TOOLS if t["name"] == "manage_growing_plan")
    props = tool["input_schema"]["properties"]
    assert "action" in props
    assert "plant_name" in props

def test_advance_milestone_schema():
    tool = next(t for t in TOOLS if t["name"] == "advance_milestone")
    props = tool["input_schema"]["properties"]
    assert "plant_name" in props
    assert "user_confirmed" in props
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_growing_plan_tools.py -v`
Expected: FAIL

**Step 3: Add tool definitions to `app/agents/tools.py`**

```python
{
    "name": "manage_growing_plan",
    "description": "Add, check, or update items on the user's seasonal growing plan. Use when the user mentions wanting to grow something, or to check what's next on their plan.",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["add", "list", "check_timing", "activate", "skip"],
                "description": "What to do with the growing plan",
            },
            "plant_name": {
                "type": "string",
                "description": "Name of the plant (for add/check_timing/activate/skip)",
            },
        },
        "required": ["action"],
    },
},
{
    "name": "advance_milestone",
    "description": "Record that a plant has reached the next growth milestone. Use when the user confirms progress like 'they've sprouted' or 'I've transplanted them'.",
    "input_schema": {
        "type": "object",
        "properties": {
            "plant_name": {
                "type": "string",
                "description": "Name or variety of the plant",
            },
            "user_confirmed": {
                "type": "boolean",
                "description": "Whether the user explicitly confirmed this milestone",
            },
            "notes": {
                "type": "string",
                "description": "Any details the user shared (e.g. '12 out of 15 sprouted')",
            },
        },
        "required": ["plant_name"],
    },
},
```

**Step 4: Add handlers to `app/agents/tool_handlers.py`**

Add handlers in `build_tool_handlers()`:

- `manage_growing_plan`: query GrowingPlanItem by user, add new items by looking up PlantSpec + GrowingCalendar, return status
- `advance_milestone`: find the user's Plant by name/variety, increment `next_milestone_index`, update `growth_stage`, log ContextEvent

**Step 5: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_growing_plan_tools.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add app/agents/tools.py app/agents/tool_handlers.py tests/test_growing_plan_tools.py
git commit -m "feat: add manage_growing_plan and advance_milestone tools"
```

---

## Task 9: Update Proactive Scheduler with Milestone Triggers

Wire milestone checks into the existing proactive scheduler loop.

**Files:**
- Modify: `app/tasks/proactive_scheduler.py`
- Modify: `app/services/proactive.py` (add milestone context to message builder)
- Test: `tests/test_proactive_milestones.py`

**Step 1: Write the failing tests**

```python
# tests/test_proactive_milestones.py
from app.services.proactive import ProactiveMessageBuilder

def test_build_milestone_context():
    milestones = [
        {"plant_name": "Tomato", "variety": "Gardener's Delight", "stage": "sprouting",
         "check_in": "Should be sprouting by now", "delayed": False, "days_since_planting": 10},
    ]
    ctx = ProactiveMessageBuilder.build_milestone_context(milestones)
    assert "Tomato" in ctx
    assert "sprouting" in ctx

def test_build_milestone_context_delayed():
    milestones = [
        {"plant_name": "Tomato", "stage": "hardening_off", "variety": None,
         "check_in": "Put outside", "delayed": True, "days_since_planting": 42},
    ]
    ctx = ProactiveMessageBuilder.build_milestone_context(milestones)
    assert "DELAYED" in ctx or "delayed" in ctx.lower()

def test_build_milestone_context_empty():
    ctx = ProactiveMessageBuilder.build_milestone_context([])
    assert ctx == ""
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_proactive_milestones.py -v`
Expected: FAIL

**Step 3: Add `build_milestone_context` to ProactiveMessageBuilder**

In `app/services/proactive.py`:

```python
@staticmethod
def build_milestone_context(milestones: list[dict]) -> str:
    if not milestones:
        return ""
    lines = ["MILESTONE CHECK-INS DUE:"]
    for m in milestones:
        name = f"{m['plant_name']}"
        if m.get("variety"):
            name += f" ({m['variety']})"
        status = "DELAYED by weather" if m["delayed"] else f"Day {m['days_since_planting']}"
        lines.append(f"- {name}: {m['stage']} ({status}) — {m['check_in']}")
    return "\n".join(lines)
```

**Step 4: Update `run_proactive_checks()` in `app/tasks/proactive_scheduler.py`**

Add milestone checking to the trigger evaluation:
- After fetching active plants, instantiate `MilestoneChecker`
- Call `get_due_milestones(plants, today, weather)` where weather comes from existing forecast
- Add milestone triggers to the trigger dict
- Pass milestone context to `ProactiveMessageBuilder`

**Step 5: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_proactive_milestones.py -v`
Expected: PASS

**Step 6: Run full test suite**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/ -v`
Expected: All pass

**Step 7: Commit**

```bash
git add app/tasks/proactive_scheduler.py app/services/proactive.py tests/test_proactive_milestones.py
git commit -m "feat: wire milestone triggers into proactive scheduler"
```

---

## Task 10: Slack Outbound Sender

Consume outbound messages from Redis queue and send via Slack API.

**Files:**
- Create: `app/channels/slack_sender.py`
- Modify: `app/tasks/proactive_scheduler.py` (enqueue with channel info)
- Test: `tests/test_slack_sender.py`

**Step 1: Write the failing tests**

```python
# tests/test_slack_sender.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.channels.slack_sender import SlackOutboundSender

@pytest.fixture
def sender():
    client = AsyncMock()
    return SlackOutboundSender(client)

@pytest.mark.asyncio
async def test_send_message(sender):
    sender.client.chat_postMessage = AsyncMock(return_value={"ok": True})
    result = await sender.send("U12345", "Hello from Sage!")
    sender.client.chat_postMessage.assert_called_once()
    assert result is True

@pytest.mark.asyncio
async def test_send_opens_dm_first(sender):
    sender.client.conversations_open = AsyncMock(return_value={"ok": True, "channel": {"id": "D12345"}})
    sender.client.chat_postMessage = AsyncMock(return_value={"ok": True})
    result = await sender.send("U12345", "Hello!")
    sender.client.conversations_open.assert_called_once_with(users="U12345")
    assert result is True

@pytest.mark.asyncio
async def test_send_handles_error(sender):
    sender.client.conversations_open = AsyncMock(side_effect=Exception("Slack error"))
    result = await sender.send("U12345", "Hello!")
    assert result is False
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_slack_sender.py -v`
Expected: FAIL

**Step 3: Implement SlackOutboundSender**

```python
# app/channels/slack_sender.py
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

class SlackOutboundSender:
    def __init__(self, client):
        self.client = client

    async def send(self, slack_user_id: str, text: str) -> bool:
        try:
            dm = await self.client.conversations_open(users=slack_user_id)
            channel_id = dm["channel"]["id"]
            await self.client.chat_postMessage(channel=channel_id, text=text)
            return True
        except Exception:
            logger.exception("Failed to send Slack message to %s", slack_user_id)
            return False
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_slack_sender.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add app/channels/slack_sender.py tests/test_slack_sender.py
git commit -m "feat: add Slack outbound sender for proactive messages"
```

---

## Task 11: Update System Prompt for Accountability Coaching

Update the Sage system prompt to include accountability coaching behaviour, growing plan awareness, and milestone tracking instructions.

**Files:**
- Modify: `app/agents/system_prompt.py`
- No test needed — behaviour tested via integration

**Step 1: Read the current system prompt**

Read `app/agents/system_prompt.py` to understand current structure.

**Step 2: Add accountability coaching section**

Add to the system prompt:

```
## Accountability Coaching

You are Sage — a gardening PT, not just an advisor. Like a personal trainer who checks in to make sure you did your session.

### Growing Plan
- When users mention wanting to grow things, use manage_growing_plan to track their wishlist
- Be honest about timing — if they've missed the sowing window, say so directly and suggest alternatives
- Pace introductions — don't overwhelm beginners with everything at once
- When a plant's window opens, prompt them: "Remember those strawberries on your list? Now's the time"

### Milestone Tracking
- When users confirm progress ("they've sprouted", "I planted them out"), use advance_milestone
- Celebrate genuinely — "12 out of 15 sprouted is a great rate, well done"
- Don't be saccharine — acknowledge wins like a mate would, not a motivational poster
- Note specific details they share and reference them later

### Proactive Style
- When checking in on milestones, be specific: "Your tomato seedlings should have their first true leaves by now — the serrated ones, not the smooth seed leaves"
- Always include local weather context: "It's 14°C in Lewisham tomorrow, perfect for..."
- If weather blocks a milestone, explain why: "Too cold to put them out this week — I'll let you know when it warms up"
- Never guilt-trip about missed tasks — just pick up where they left off
```

**Step 3: Commit**

```bash
git add app/agents/system_prompt.py
git commit -m "feat: update system prompt with accountability coaching behaviour"
```

---

## Task 12: Integration Test — Full Accountability Flow

End-to-end test verifying the complete flow from planting → milestone check → proactive message.

**Files:**
- Create: `tests/test_accountability_integration.py`

**Step 1: Write the integration test**

```python
# tests/test_accountability_integration.py
from datetime import date, timedelta
from unittest.mock import MagicMock
from app.services.milestone_checker import MilestoneChecker
from app.services.engagement import EngagementService
from app.services.proactive import ProactiveMessageBuilder
from app.data.plant_milestones import PLANT_MILESTONES

def test_full_milestone_flow():
    """Simulate: user plants tomatoes → 10 days pass → milestone triggers → message built"""
    # 1. User plants tomatoes
    tomato_data = PLANT_MILESTONES["tomato"]
    plant = MagicMock()
    plant.planting_date = date.today() - timedelta(days=10)
    plant.next_milestone_index = 0
    plant.milestone_delayed = False
    plant.variety = "Gardener's Delight"
    plant.growth_stage = "seed"
    spec = MagicMock()
    spec.growth_milestones = tomato_data["milestones"]
    spec.common_name = "Tomato"
    plant.plant_spec = spec

    # 2. Check milestones
    checker = MilestoneChecker()
    due = checker.get_due_milestones([plant], date.today())
    assert len(due) == 1
    assert due[0]["stage"] == "sprouting"

    # 3. Build message context
    ctx = ProactiveMessageBuilder.build_milestone_context(due)
    assert "Tomato" in ctx
    assert "Gardener's Delight" in ctx

    # 4. Engagement check
    freq = EngagementService.get_frequency_for_unanswered(0)
    assert freq == "normal"
    min_days = EngagementService.min_days_between(freq)
    assert min_days == 3

def test_growing_plan_timing_check():
    """Verify timing check works with real PlantSpec data"""
    from app.services.growing_plan import GrowingPlanService
    cal = MagicMock()
    cal.activity = "sow_indoors"
    cal.month_start = 3
    cal.month_end = 4
    result = GrowingPlanService.check_timing([cal], date(2026, 3, 15))
    assert result["status"] == "ready"

def test_silence_handling_flow():
    """User goes quiet → frequency adapts → nudge at right time"""
    # 0-1 unanswered: normal
    assert EngagementService.get_frequency_for_unanswered(0) == "normal"
    assert EngagementService.should_nudge(0) is False

    # 2 unanswered: nudge
    assert EngagementService.should_nudge(2) is True
    assert EngagementService.get_frequency_for_unanswered(2) == "normal"

    # 3 unanswered: reduce frequency
    assert EngagementService.get_frequency_for_unanswered(3) == "reduced"
    assert EngagementService.min_days_between("reduced") == 7

    # 4+ unanswered: minimal
    assert EngagementService.get_frequency_for_unanswered(5) == "minimal"
    assert EngagementService.min_days_between("minimal") == 14
```

**Step 2: Run the integration tests**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_accountability_integration.py -v`
Expected: PASS

**Step 3: Run full test suite**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/ -v`
Expected: All pass

**Step 4: Commit**

```bash
git add tests/test_accountability_integration.py
git commit -m "test: add integration tests for accountability coaching flow"
```

---

## Task 13: Final — Run All Tests & Verify

**Step 1: Run complete test suite**

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
source .venv/bin/activate
python -m pytest tests/ -v --tb=short
```

Expected: All tests pass

**Step 2: Verify migration is applied**

```bash
alembic current
```

Expected: Shows latest migration head

**Step 3: Final commit if any loose ends**

```bash
git status
# If clean, done. If not, add and commit remaining files.
```
