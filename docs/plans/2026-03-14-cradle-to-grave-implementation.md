# Cradle-to-Grave Plant Intelligence — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform Sage from a reactive chat companion into a proactive gardening personal trainer with cradle-to-grave plant tracking, weather-correlated intelligence, and a context-first data model designed for future ML.

**Architecture:** Extend the existing PostgreSQL + Redis + ARQ stack. Add thin identity tables (GrowingSeason, EngagementProfile, WeatherLog) alongside an enriched ContextEvent stream. Build a proactive engagement scheduler that generates natural, whole-garden messages via Claude. Fix postcode handling for outward-only codes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x (async), Alembic, PostgreSQL, Redis, ARQ, Anthropic Claude API, httpx, pytest + pytest-asyncio.

**Design Doc:** `docs/plans/2026-03-14-cradle-to-grave-plant-intelligence-design.md`

---

## Task 1: Fix PostcodeService — Outcode Fallback

**Files:**
- Modify: `backend/app/services/postcode.py`
- Modify: `backend/tests/test_postcode.py`

**Step 1: Write the failing tests**

Add these tests to `backend/tests/test_postcode.py`:

```python
async def test_normalise_postcode_uppercase(service):
    """Lowercase input gets uppercased."""
    assert service.normalise("dn35 8lz") == "DN35 8LZ"


async def test_normalise_postcode_no_space(service):
    """'dn358lz' gets space inserted → 'DN35 8LZ'."""
    assert service.normalise("dn358lz") == "DN35 8LZ"


async def test_normalise_postcode_strip(service):
    """Whitespace stripped."""
    assert service.normalise("  DN35  ") == "DN35"


async def test_normalise_outcode_inner_space(service):
    """'DN 35' → 'DN35' (remove inner space for outcodes)."""
    assert service.normalise("DN 35") == "DN35"


async def test_lookup_outcode_fallback(service):
    """When full postcode lookup returns 404, fall back to /outcodes/ endpoint."""
    full_404 = MagicMock()
    full_404.status_code = 404

    outcode_200 = MagicMock()
    outcode_200.status_code = 200
    outcode_200.raise_for_status = MagicMock()
    outcode_200.json.return_value = {
        "status": 200,
        "result": {
            "outcode": "DN35",
            "latitude": 53.5596,
            "longitude": -0.0480,
            "admin_district": ["North East Lincolnshire"],
            "country": ["England"],
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(side_effect=[full_404, outcode_200])
        result = await service.lookup("DN35")

    assert result is not None
    assert result["outward_code"] == "DN35"
    assert result["latitude"] == 53.5596
    assert result["admin_district"] == "North East Lincolnshire"


async def test_lookup_outcode_both_fail(service):
    """When both /postcodes/ and /outcodes/ return 404, return None."""
    response_404 = MagicMock()
    response_404.status_code = 404

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=response_404)
        result = await service.lookup("ZZZZZ")

    assert result is None
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_postcode.py -v`
Expected: FAIL — `normalise` method doesn't exist, outcode fallback not implemented.

**Step 3: Implement the fix**

Replace `backend/app/services/postcode.py` with:

```python
import re

import httpx


class PostcodeService:
    BASE_URL = "https://api.postcodes.io"

    def __init__(self):
        self._client = httpx.AsyncClient(base_url=self.BASE_URL, timeout=10.0)

    @staticmethod
    def normalise(raw: str) -> str:
        """Normalise messy postcode input from WhatsApp.

        Handles: lowercase, missing spaces, extra whitespace, inner spaces in outcodes.
        """
        text = raw.strip().upper()
        # Remove all spaces for analysis
        compact = text.replace(" ", "")

        # Full UK postcode pattern: A9A 9AA, A9 9AA, A99 9AA, AA9 9AA, AA99 9AA, AA9A 9AA
        # Inward part is always 3 chars: 9AA
        if re.match(r"^[A-Z]{1,2}\d[A-Z\d]?\d[A-Z]{2}$", compact):
            # Insert space before last 3 characters
            return f"{compact[:-3]} {compact[-3:]}"

        # Otherwise treat as outward code — just return uppercased, spaces removed
        return compact

    async def lookup(self, raw_postcode: str) -> dict | None:
        """Look up a UK postcode or outward code.

        Tries full postcode first, then falls back to outcode endpoint.
        Returns lat/lng/region/admin_district or None.
        """
        postcode = self.normalise(raw_postcode)

        # Try full postcode lookup
        result = await self._try_full_postcode(postcode)
        if result:
            return result

        # Fall back to outcode lookup (handles "DN35", "B44", etc.)
        outcode = postcode.split()[0] if " " in postcode else postcode
        return await self._try_outcode(outcode)

    async def _try_full_postcode(self, postcode: str) -> dict | None:
        """Try the /postcodes/ endpoint for a full postcode."""
        response = await self._client.get(f"/postcodes/{postcode}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()["result"]
        return {
            "postcode": data["postcode"],
            "outward_code": data["outcode"],
            "latitude": data["latitude"],
            "longitude": data["longitude"],
            "region": data.get("region"),
            "admin_district": data.get("admin_district"),
        }

    async def _try_outcode(self, outcode: str) -> dict | None:
        """Try the /outcodes/ endpoint for an outward code like DN35 or B44."""
        response = await self._client.get(f"/outcodes/{outcode}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()["result"]

        # Outcode endpoint returns admin_district as a list — take first
        admin_district = data.get("admin_district", [])
        if isinstance(admin_district, list):
            admin_district = admin_district[0] if admin_district else None

        return {
            "postcode": None,
            "outward_code": data.get("outcode", outcode),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude"),
            "region": None,  # Outcode endpoint doesn't return region
            "admin_district": admin_district,
        }

    async def validate(self, postcode: str) -> bool:
        """Check if a postcode is valid."""
        response = await self._client.get(f"/postcodes/{postcode}/validate")
        return response.json().get("result", False)

    async def close(self):
        await self._client.aclose()
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_postcode.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/services/postcode.py backend/tests/test_postcode.py
git commit -m "fix: postcode service handles outward-only codes (DN35, B44) with fuzzy input normalisation"
```

---

## Task 2: Database Migration — GrowingSeason Table

**Files:**
- Create: `backend/app/models/growing_season.py`
- Modify: `backend/app/models/__init__.py`
- Create: migration via `alembic revision`
- Create: `backend/tests/test_growing_season.py`

**Step 1: Write the failing test**

Create `backend/tests/test_growing_season.py`:

```python
import uuid
from datetime import date

from app.models.growing_season import GrowingSeason


def test_growing_season_model_fields():
    """GrowingSeason model has all required fields."""
    season = GrowingSeason(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        year=2026,
        label="Spring/Summer 2026",
        started_at=date(2026, 3, 1),
    )
    assert season.year == 2026
    assert season.label == "Spring/Summer 2026"
    assert season.ended_at is None
    assert season.season_summary is None
    assert season.weather_summary is None
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_growing_season.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.growing_season'`

**Step 3: Create the model**

Create `backend/app/models/growing_season.py`:

```python
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, SmallInteger, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GrowingSeason(Base):
    __tablename__ = "growing_seasons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(SmallInteger, index=True)
    label: Mapped[str] = mapped_column(String(50))  # "Spring/Summer 2026"
    started_at: Mapped[date] = mapped_column(Date)
    ended_at: Mapped[date | None] = mapped_column(Date)
    season_summary: Mapped[dict | None] = mapped_column(JSONB)
    weather_summary: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

**Step 4: Add to `__init__.py`**

Add import and export for `GrowingSeason` in `backend/app/models/__init__.py`.

**Step 5: Run test to verify it passes**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_growing_season.py -v`
Expected: PASS

**Step 6: Generate and run migration**

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
source .venv/bin/activate
alembic revision --autogenerate -m "add growing_seasons table"
alembic upgrade head
```

**Step 7: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/models/growing_season.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_growing_season.py
git commit -m "feat: add GrowingSeason model for year-over-year plant lineage tracking"
```

---

## Task 3: Database Migration — Plant Model Extensions

**Files:**
- Modify: `backend/app/models/plant.py`
- Create: migration via `alembic revision`
- Create: `backend/tests/test_plant_lineage.py`

**Step 1: Write the failing test**

Create `backend/tests/test_plant_lineage.py`:

```python
import uuid
from datetime import date

from app.models.plant import Plant


def test_plant_lineage_fields():
    """Plant model has new lineage/season fields."""
    parent_id = uuid.uuid4()
    season_id = uuid.uuid4()
    plant = Plant(
        id=uuid.uuid4(),
        garden_id=uuid.uuid4(),
        growing_season_id=season_id,
        parent_plant_id=parent_id,
        seed_source="saved_seed",
        final_outcome="success",
        yield_total_kg=4.2,
        season_notes="Great year for tomatoes",
    )
    assert plant.growing_season_id == season_id
    assert plant.parent_plant_id == parent_id
    assert plant.seed_source == "saved_seed"
    assert plant.final_outcome == "success"
    assert plant.yield_total_kg == 4.2
    assert plant.season_notes == "Great year for tomatoes"


def test_plant_lineage_defaults():
    """New fields default to None."""
    plant = Plant(id=uuid.uuid4(), garden_id=uuid.uuid4())
    assert plant.growing_season_id is None
    assert plant.parent_plant_id is None
    assert plant.seed_source is None
    assert plant.final_outcome is None
    assert plant.yield_total_kg is None
    assert plant.season_notes is None
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_plant_lineage.py -v`
Expected: FAIL — fields don't exist on Plant model.

**Step 3: Add fields to Plant model**

Add these columns to `backend/app/models/plant.py` (after `harvest_log`):

```python
    growing_season_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("growing_seasons.id"), index=True)
    parent_plant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plants.id"))
    seed_source: Mapped[str | None] = mapped_column(String(30))  # saved_seed, bought, gifted, grown
    final_outcome: Mapped[str | None] = mapped_column(String(20))  # success, partial, failed, abandoned
    yield_total_kg: Mapped[float | None] = mapped_column(Numeric(6, 2))
    season_notes: Mapped[str | None] = mapped_column(Text)
```

Add required imports: `Numeric`, `Text` from sqlalchemy (if not already imported).

**Step 4: Run test to verify it passes**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_plant_lineage.py -v`
Expected: PASS

**Step 5: Generate and run migration**

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
alembic revision --autogenerate -m "add plant lineage and season fields"
alembic upgrade head
```

**Step 6: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/models/plant.py backend/alembic/versions/ backend/tests/test_plant_lineage.py
git commit -m "feat: add lineage tracking to Plant model (parent_plant_id, seed_source, season, outcome, yield)"
```

---

## Task 4: Database Migration — ContextEvent Weather Snapshot

**Files:**
- Modify: `backend/app/models/context_event.py`
- Create: migration via `alembic revision`

**Step 1: Write the failing test**

Add to `backend/tests/test_db.py` (or create a new test file):

```python
import uuid

from app.models.context_event import ContextEvent


def test_context_event_has_weather_snapshot():
    """ContextEvent has weather_snapshot JSONB field."""
    event = ContextEvent(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        event_type="care_watering",
        summary="Watered tomatoes",
        weather_snapshot={"temp_c": 22, "rainfall_last_24h_mm": 0, "wind_kmh": 8},
    )
    assert event.weather_snapshot["temp_c"] == 22
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_db.py::test_context_event_has_weather_snapshot -v`
Expected: FAIL

**Step 3: Add the field**

Add to `backend/app/models/context_event.py` (after `detail`):

```python
    weather_snapshot: Mapped[dict | None] = mapped_column(JSONB)
```

**Step 4: Run test, generate migration, commit**

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
python -m pytest tests/test_db.py::test_context_event_has_weather_snapshot -v
alembic revision --autogenerate -m "add weather_snapshot to context_events"
alembic upgrade head
```

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/models/context_event.py backend/alembic/versions/
git commit -m "feat: add weather_snapshot JSONB to ContextEvent for weather-correlated intelligence"
```

---

## Task 5: Database Migration — WeatherLog Table

**Files:**
- Create: `backend/app/models/weather_log.py`
- Modify: `backend/app/models/__init__.py`
- Create: migration via `alembic revision`
- Create: `backend/tests/test_weather_log.py`

**Step 1: Write the failing test**

Create `backend/tests/test_weather_log.py`:

```python
import uuid
from datetime import date

from app.models.weather_log import WeatherLog


def test_weather_log_fields():
    """WeatherLog stores daily weather per postcode."""
    log = WeatherLog(
        id=uuid.uuid4(),
        postcode_outward="DN35",
        date=date(2026, 3, 14),
        temp_max_c=14.5,
        temp_min_c=3.2,
        rainfall_mm=2.1,
        wind_max_kmh=25.0,
        sunshine_hours=6.5,
        frost=False,
    )
    assert log.postcode_outward == "DN35"
    assert log.temp_max_c == 14.5
    assert log.frost is False
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_weather_log.py -v`
Expected: FAIL

**Step 3: Create the model**

Create `backend/app/models/weather_log.py`:

```python
import uuid
from datetime import date as date_type

from sqlalchemy import Boolean, Date, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class WeatherLog(Base):
    __tablename__ = "weather_logs"
    __table_args__ = (
        UniqueConstraint("postcode_outward", "date", name="uq_weather_postcode_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    postcode_outward: Mapped[str] = mapped_column(String(4), index=True)
    date: Mapped[date_type] = mapped_column(Date, index=True)
    temp_max_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    temp_min_c: Mapped[float | None] = mapped_column(Numeric(4, 1))
    rainfall_mm: Mapped[float | None] = mapped_column(Numeric(5, 1))
    wind_max_kmh: Mapped[float | None] = mapped_column(Numeric(4, 1))
    sunshine_hours: Mapped[float | None] = mapped_column(Numeric(3, 1))
    frost: Mapped[bool] = mapped_column(Boolean, default=False)
```

**Step 4: Add to `__init__.py`, run test, generate migration, commit**

Add `WeatherLog` to `backend/app/models/__init__.py`.

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
python -m pytest tests/test_weather_log.py -v
alembic revision --autogenerate -m "add weather_logs table"
alembic upgrade head
```

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/models/weather_log.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_weather_log.py
git commit -m "feat: add WeatherLog table for daily weather capture per postcode"
```

---

## Task 6: Database Migration — EngagementProfile Table

**Files:**
- Create: `backend/app/models/engagement_profile.py`
- Modify: `backend/app/models/__init__.py`
- Create: migration via `alembic revision`
- Create: `backend/tests/test_engagement_profile.py`

**Step 1: Write the failing test**

Create `backend/tests/test_engagement_profile.py`:

```python
import uuid
from datetime import time

from app.models.engagement_profile import EngagementProfile


def test_engagement_profile_fields():
    """EngagementProfile stores user notification preferences."""
    profile = EngagementProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        preferred_time="morning",
        notification_level="normal",
        quiet_hours_start=time(22, 0),
        quiet_hours_end=time(7, 0),
    )
    assert profile.preferred_time == "morning"
    assert profile.notification_level == "normal"
    assert profile.quiet_hours_start == time(22, 0)


def test_engagement_profile_defaults():
    """Sensible defaults for new profiles."""
    profile = EngagementProfile(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
    )
    assert profile.preferred_time == "morning"
    assert profile.notification_level == "normal"
    assert profile.last_sage_initiated_at is None
    assert profile.last_user_message_at is None
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_engagement_profile.py -v`
Expected: FAIL

**Step 3: Create the model**

Create `backend/app/models/engagement_profile.py`:

```python
import uuid
from datetime import datetime, time as time_type

from sqlalchemy import DateTime, ForeignKey, String, Time
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EngagementProfile(Base):
    __tablename__ = "engagement_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    preferred_time: Mapped[str] = mapped_column(String(20), default="morning")  # morning, evening, anytime
    notification_level: Mapped[str] = mapped_column(String(20), default="normal")  # alerts_only, normal, chatty
    quiet_hours_start: Mapped[time_type | None] = mapped_column(Time)
    quiet_hours_end: Mapped[time_type | None] = mapped_column(Time)
    last_sage_initiated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_user_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

**Step 4: Add to `__init__.py`, run test, generate migration, commit**

Add `EngagementProfile` to `backend/app/models/__init__.py`.

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
python -m pytest tests/test_engagement_profile.py -v
alembic revision --autogenerate -m "add engagement_profiles table"
alembic upgrade head
```

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/models/engagement_profile.py backend/app/models/__init__.py backend/alembic/versions/ backend/tests/test_engagement_profile.py
git commit -m "feat: add EngagementProfile model for proactive notification preferences"
```

---

## Task 7: Weather Logging Service

**Files:**
- Modify: `backend/app/services/weather.py`
- Create: `backend/tests/test_weather_logging.py`

**Step 1: Write the failing test**

Create `backend/tests/test_weather_logging.py`:

```python
import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.weather import WeatherService


async def test_get_weather_snapshot():
    """get_weather_snapshot returns a dict suitable for ContextEvent.weather_snapshot."""
    service = WeatherService()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {
        "current_weather": {
            "temperature": 18.5,
            "windspeed": 12.0,
        },
        "daily": {
            "temperature_2m_max": [18.5],
            "temperature_2m_min": [8.2],
            "precipitation_sum": [1.5],
        },
    }

    with patch.object(service, "_client") as mock_client:
        mock_client.get = AsyncMock(return_value=mock_response)
        snapshot = await service.get_weather_snapshot(53.56, -0.05)

    assert "temp_c" in snapshot
    assert "temp_max_c" in snapshot
    assert "rainfall_mm" in snapshot
    assert snapshot["temp_c"] == 18.5
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_weather_logging.py -v`
Expected: FAIL — `get_weather_snapshot` doesn't exist.

**Step 3: Add `get_weather_snapshot` method to WeatherService**

Add this method to `backend/app/services/weather.py`:

```python
    async def get_weather_snapshot(self, lat: float, lon: float) -> dict:
        """Get a compact weather snapshot for embedding in context events.

        Returns a dict with current conditions — designed to be stored as
        ContextEvent.weather_snapshot JSONB.
        """
        response = await self._client.get(
            "/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "Europe/London",
                "forecast_days": 1,
            },
        )
        response.raise_for_status()
        data = response.json()

        current = data.get("current_weather", {})
        daily = data.get("daily", {})

        return {
            "temp_c": current.get("temperature"),
            "wind_kmh": current.get("windspeed"),
            "temp_max_c": daily.get("temperature_2m_max", [None])[0],
            "temp_min_c": daily.get("temperature_2m_min", [None])[0],
            "rainfall_mm": daily.get("precipitation_sum", [None])[0],
        }
```

**Step 4: Run test to verify it passes**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_weather_logging.py -v`
Expected: PASS

**Step 5: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/services/weather.py backend/tests/test_weather_logging.py
git commit -m "feat: add get_weather_snapshot to WeatherService for context event enrichment"
```

---

## Task 8: Context Event Enrichment — Auto Weather Capture

**Files:**
- Modify: `backend/app/agents/tool_handlers.py` (the `log_context_event` handler)
- Create: `backend/tests/test_context_enrichment.py`

**Step 1: Write the failing test**

Create `backend/tests/test_context_enrichment.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


async def test_log_context_event_adds_weather_snapshot():
    """When log_context_event is called, it auto-captures weather and stores in weather_snapshot."""
    # This test validates the integration: tool_handler calls WeatherService.get_weather_snapshot
    # and stores the result on the ContextEvent.weather_snapshot field.
    # Implementation detail: read tool_handlers.py to see the exact function signature.
    # The key assertion is that ContextEvent gets weather_snapshot populated.
    pass  # Placeholder — fill in after reading tool_handlers.py exact signature
```

Note to implementer: Read `backend/app/agents/tool_handlers.py` to see how `log_context_event` currently works. The change is:
1. Accept `weather_service` in `build_tool_handlers()`
2. In the `log_context_event` handler, call `weather_service.get_weather_snapshot(user.latitude, user.longitude)`
3. Store result as `weather_snapshot` on the `ContextEvent`
4. Wrap in try/except — weather failure should NOT block event logging

**Step 2: Implement the enrichment**

Modify `build_tool_handlers()` in `backend/app/agents/tool_handlers.py`:
- Add `weather_service` parameter
- In `log_context_event` handler, auto-capture weather snapshot before creating the ContextEvent
- Store as `event.weather_snapshot = snapshot`

**Step 3: Update call sites**

Anywhere `build_tool_handlers()` is called (check `cli.py`, `process_message.py`), pass the `weather_service`.

**Step 4: Run all tests**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/agents/tool_handlers.py backend/tests/test_context_enrichment.py
git commit -m "feat: auto-capture weather snapshot on every context event"
```

---

## Task 9: Proactive Engagement Scheduler

**Files:**
- Create: `backend/app/services/engagement.py`
- Modify: `backend/app/tasks/alert_scheduler.py`
- Create: `backend/tests/test_engagement.py`

**Step 1: Write the failing tests**

Create `backend/tests/test_engagement.py`:

```python
from datetime import datetime, timezone, timedelta, time

import pytest

from app.services.engagement import EngagementService


def test_sporadic_chance_active_user():
    """Active user (contacted 1 day ago) has very low chance."""
    chance = EngagementService.calculate_sporadic_chance(
        days_since_contact=1, current_month=6,
    )
    assert 0 < chance < 0.10  # 5% * 1.5 seasonal = 7.5%


def test_sporadic_chance_dormant_user():
    """Dormant user (14+ days) has high chance in growing season."""
    chance = EngagementService.calculate_sporadic_chance(
        days_since_contact=15, current_month=5,
    )
    assert chance >= 0.5  # 50% * 1.5 = 75%


def test_sporadic_chance_winter_low():
    """Winter months reduce sporadic chance."""
    chance = EngagementService.calculate_sporadic_chance(
        days_since_contact=7, current_month=12,
    )
    summer_chance = EngagementService.calculate_sporadic_chance(
        days_since_contact=7, current_month=6,
    )
    assert chance < summer_chance


def test_is_quiet_hours():
    """Respects user quiet hours."""
    assert EngagementService.is_quiet_hours(
        current_time=time(23, 0),
        quiet_start=time(22, 0),
        quiet_end=time(7, 0),
    ) is True

    assert EngagementService.is_quiet_hours(
        current_time=time(12, 0),
        quiet_start=time(22, 0),
        quiet_end=time(7, 0),
    ) is False


def test_is_quiet_hours_none():
    """No quiet hours set — never quiet."""
    assert EngagementService.is_quiet_hours(
        current_time=time(3, 0),
        quiet_start=None,
        quiet_end=None,
    ) is False
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_engagement.py -v`
Expected: FAIL

**Step 3: Implement EngagementService**

Create `backend/app/services/engagement.py`:

```python
"""Proactive engagement logic — determines when and whether Sage should reach out."""

import random
from datetime import time as time_type


class EngagementService:
    """Pure logic for engagement decisions. No DB access — takes values, returns decisions."""

    # Seasonal multipliers — growing season is chatty, winter is quiet
    SEASON_MULTIPLIERS = {
        1: 0.3, 2: 0.3,   # Winter — mostly quiet
        3: 1.5, 4: 1.5, 5: 1.5, 6: 1.5,  # Spring/early summer — lots happening
        7: 1.0, 8: 1.0, 9: 1.0,  # Mid/late summer — steady
        10: 0.7, 11: 0.3, 12: 0.3,  # Autumn/winter — winding down
    }

    @staticmethod
    def calculate_sporadic_chance(days_since_contact: int, current_month: int) -> float:
        """Calculate probability of sending a sporadic check-in.

        Returns a float 0.0–1.0 representing the chance of reaching out.
        """
        if days_since_contact <= 2:
            base_chance = 0.05
        elif days_since_contact <= 5:
            base_chance = 0.15
        elif days_since_contact <= 14:
            base_chance = 0.30
        else:
            base_chance = 0.50

        multiplier = EngagementService.SEASON_MULTIPLIERS.get(current_month, 1.0)
        return base_chance * multiplier

    @staticmethod
    def should_send_sporadic(days_since_contact: int, current_month: int) -> bool:
        """Roll the dice — should Sage send a sporadic check-in?"""
        chance = EngagementService.calculate_sporadic_chance(days_since_contact, current_month)
        return random.random() < chance

    @staticmethod
    def is_quiet_hours(
        current_time: time_type,
        quiet_start: time_type | None,
        quiet_end: time_type | None,
    ) -> bool:
        """Check if current time falls within user's quiet hours.

        Handles overnight ranges like 22:00 → 07:00.
        """
        if quiet_start is None or quiet_end is None:
            return False

        if quiet_start <= quiet_end:
            # Same-day range (e.g., 13:00–15:00)
            return quiet_start <= current_time <= quiet_end
        else:
            # Overnight range (e.g., 22:00–07:00)
            return current_time >= quiet_start or current_time <= quiet_end
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_engagement.py -v`
Expected: ALL PASS

**Step 5: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/services/engagement.py backend/tests/test_engagement.py
git commit -m "feat: add EngagementService with sporadic check-in algorithm and quiet hours"
```

---

## Task 10: Proactive Message Generation — Whole-Garden Bundled Messages

**Files:**
- Create: `backend/app/services/proactive.py`
- Create: `backend/tests/test_proactive.py`

This is the core intelligence — gathering all triggers for a user and generating one natural, whole-garden message via Claude.

**Step 1: Write the failing test**

Create `backend/tests/test_proactive.py`:

```python
import pytest

from app.services.proactive import ProactiveMessageBuilder


def test_build_context_summary_combines_plants():
    """Context summary includes all active plants in one description."""
    plants = [
        {"variety": "Tomato", "growth_stage": "flowering", "planting_date": "2026-03-01"},
        {"variety": "Courgette", "growth_stage": "established", "planting_date": "2026-04-15"},
        {"variety": "Radish", "growth_stage": "ready_to_harvest", "planting_date": "2026-02-20"},
    ]
    summary = ProactiveMessageBuilder.build_plant_summary(plants)
    assert "Tomato" in summary
    assert "Courgette" in summary
    assert "Radish" in summary


def test_build_trigger_context():
    """Trigger context bundles weather + plant status into one prompt."""
    triggers = {
        "weather_alerts": [{"type": "frost", "min_temp": -1}],
        "care_due": [{"plant": "Courgette", "action": "feed", "product": "potash"}],
        "growth_updates": [{"plant": "Radish", "expected_stage": "ready_to_harvest"}],
    }
    context = ProactiveMessageBuilder.build_trigger_context(triggers)
    assert "frost" in context.lower()
    assert "courgette" in context.lower()
    assert "radish" in context.lower()
```

**Step 2: Run tests to verify they fail**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_proactive.py -v`
Expected: FAIL

**Step 3: Implement ProactiveMessageBuilder**

Create `backend/app/services/proactive.py`:

```python
"""Proactive message building — gathers triggers and builds context for Claude to generate
a natural, whole-garden message.

This does NOT call Claude directly. It prepares the context that the scheduler passes to
the SageOrchestrator for message generation.
"""


class ProactiveMessageBuilder:
    """Builds structured context for proactive outbound messages."""

    @staticmethod
    def build_plant_summary(plants: list[dict]) -> str:
        """Summarise all active plants into a natural description for Claude context."""
        if not plants:
            return "No active plants."

        parts = []
        for p in plants:
            variety = p.get("variety", "Unknown")
            stage = p.get("growth_stage", "unknown").replace("_", " ")
            parts.append(f"{variety} ({stage})")

        return "Active plants: " + ", ".join(parts)

    @staticmethod
    def build_trigger_context(triggers: dict) -> str:
        """Bundle all triggers into a single context string for Claude.

        Claude uses this to generate ONE natural message covering everything.
        """
        lines = []

        weather_alerts = triggers.get("weather_alerts", [])
        for alert in weather_alerts:
            alert_type = alert.get("type", "weather")
            if alert_type == "frost":
                lines.append(f"URGENT: Frost warning — minimum temperature {alert.get('min_temp')}°C")
            elif alert_type == "heatwave":
                lines.append(f"URGENT: Heatwave — temperatures reaching {alert.get('max_temp')}°C")
            else:
                lines.append(f"Weather alert: {alert_type}")

        care_due = triggers.get("care_due", [])
        for care in care_due:
            plant = care.get("plant", "plants")
            action = care.get("action", "care")
            product = care.get("product")
            if product:
                lines.append(f"Care due: {plant} needs {action} (suggest {product})")
            else:
                lines.append(f"Care due: {plant} needs {action}")

        growth_updates = triggers.get("growth_updates", [])
        for update in growth_updates:
            plant = update.get("plant", "plant")
            expected = update.get("expected_stage", "next stage").replace("_", " ")
            lines.append(f"Growth check: {plant} should be at {expected} stage by now")

        if not lines:
            lines.append("General check-in — no specific triggers, just being friendly")

        return "\n".join(lines)

    @staticmethod
    def build_system_instruction(
        trigger_context: str,
        plant_summary: str,
        user_name: str,
        experience_level: str,
    ) -> str:
        """Build the system instruction for Claude to generate a proactive message.

        Returns a prompt that tells Claude to write ONE short WhatsApp message
        covering the whole garden.
        """
        return f"""You are Sage, a friendly gardening mate. Generate a proactive WhatsApp message.

RULES:
- ONE message covering the whole garden — NEVER separate messages per plant
- Maximum 2-3 sentences. It's WhatsApp, not an essay
- Ask at most ONE question (or none — not every message needs a reply)
- Vary your tone: sometimes practical, sometimes curious, sometimes celebratory
- Don't be robotic or template-y — sound like a mate
- Use UK English
- Tailor complexity to experience level: {experience_level}

USER: {user_name}
{plant_summary}

TRIGGERS:
{trigger_context}

Write the message now. Just the message text, nothing else."""
```

**Step 4: Run tests to verify they pass**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_proactive.py -v`
Expected: PASS

**Step 5: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/services/proactive.py backend/tests/test_proactive.py
git commit -m "feat: add ProactiveMessageBuilder for whole-garden bundled outbound messages"
```

---

## Task 11: Integrate Proactive Scheduler with ARQ

**Files:**
- Create: `backend/app/tasks/proactive_scheduler.py`
- Modify: `backend/app/tasks/worker.py` (register the cron task)

**Step 1: Create the scheduler task**

Create `backend/app/tasks/proactive_scheduler.py`:

```python
"""Proactive engagement scheduler — runs hourly via ARQ cron.

Checks each active user for triggers (weather, care due, sporadic)
and sends a single bundled WhatsApp message if appropriate.
"""

import logging
from datetime import datetime, timezone

import anthropic
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.models.engagement_profile import EngagementProfile
from app.models.garden import Garden
from app.models.plant import Plant
from app.models.user import User
from app.services.engagement import EngagementService
from app.services.proactive import ProactiveMessageBuilder
from app.services.queue import MessageQueue
from app.services.weather import WeatherService

logger = logging.getLogger(__name__)


async def run_proactive_checks() -> None:
    """Hourly check: for each active user, evaluate triggers and send messages."""
    weather = WeatherService()
    queue = MessageQueue(settings.redis_url)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    try:
        await queue.connect()

        async with async_session() as session:
            result = await session.execute(
                select(User).where(User.onboarding_complete == True)  # noqa: E712
            )
            users = result.scalars().all()

            if not users:
                logger.info("No active users, skipping proactive checks")
                return

            now = datetime.now(timezone.utc)

            for user in users:
                try:
                    await _process_user(user, session, weather, queue, client, now)
                except Exception:
                    logger.exception("Failed proactive check for user %s", user.id)

    finally:
        await weather.close()
        await queue.close()
        await client.close()


async def _process_user(user, session, weather, queue, client, now):
    """Evaluate all triggers for a single user and send message if appropriate."""
    # Load engagement profile
    ep_result = await session.execute(
        select(EngagementProfile).where(EngagementProfile.user_id == user.id)
    )
    profile = ep_result.scalar_one_or_none()

    # No profile yet — skip (will be created after onboarding enhancement)
    if not profile:
        return

    # Check quiet hours
    current_time = now.time()
    if EngagementService.is_quiet_hours(current_time, profile.quiet_hours_start, profile.quiet_hours_end):
        return

    # Calculate days since last contact
    last_contact = max(
        filter(None, [profile.last_sage_initiated_at, profile.last_user_message_at]),
        default=None,
    )
    days_since = (now - last_contact).days if last_contact else 999

    # Gather triggers
    triggers = {"weather_alerts": [], "care_due": [], "growth_updates": []}

    # Weather checks
    if user.latitude and user.longitude:
        try:
            frost = await weather.check_frost_risk(float(user.latitude), float(user.longitude))
            if frost.get("frost_risk"):
                triggers["weather_alerts"].append({
                    "type": "frost",
                    "min_temp": frost.get("min_temperature"),
                })
        except Exception:
            logger.warning("Weather check failed for user %s", user.id)

    # Check if any triggers warrant a message
    has_urgent = bool(triggers["weather_alerts"])
    has_timely = bool(triggers["care_due"] or triggers["growth_updates"])
    should_sporadic = EngagementService.should_send_sporadic(days_since, now.month)

    if not has_urgent and not has_timely and not should_sporadic:
        return

    # Anti-nag: check notification level
    if profile.notification_level == "alerts_only" and not has_urgent:
        return

    # Load plants for context
    garden_result = await session.execute(
        select(Garden).where(Garden.user_id == user.id, Garden.is_primary.is_(True))
    )
    garden = garden_result.scalar_one_or_none()

    plants_data = []
    if garden:
        plants_result = await session.execute(
            select(Plant).where(Plant.garden_id == garden.id, Plant.is_active.is_(True))
        )
        plants = plants_result.scalars().all()
        plants_data = [
            {"variety": p.variety, "growth_stage": p.growth_stage, "planting_date": str(p.planting_date)}
            for p in plants
        ]

    # Build context and generate message via Claude
    plant_summary = ProactiveMessageBuilder.build_plant_summary(plants_data)
    trigger_context = ProactiveMessageBuilder.build_trigger_context(triggers)
    system_instruction = ProactiveMessageBuilder.build_system_instruction(
        trigger_context=trigger_context,
        plant_summary=plant_summary,
        user_name=user.display_name or "there",
        experience_level=user.experience_level or "beginner",
    )

    response = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=300,
        messages=[{"role": "user", "content": "Generate the proactive message now."}],
        system=system_instruction,
    )

    message_text = response.content[0].text

    # Send via WhatsApp
    await queue.enqueue_outbound({
        "to": user.whatsapp_phone,
        "text": message_text,
        "type": "text",
    })

    # Update engagement profile
    profile.last_sage_initiated_at = now
    await session.commit()

    logger.info("Sent proactive message to user %s", user.id)
```

**Step 2: Register in ARQ worker**

Add to `backend/app/tasks/worker.py`:

```python
from app.tasks.proactive_scheduler import run_proactive_checks

# In WorkerSettings class, add cron job:
class WorkerSettings:
    functions = [process_inbound_message]
    cron_jobs = [
        cron(run_proactive_checks, hour={7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20}),
    ]
    # ... rest of settings
```

Import `cron` from `arq`:
```python
from arq import cron
```

**Step 3: Run all tests**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest -v`
Expected: ALL PASS (no new tests for this task — integration tested manually)

**Step 4: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/tasks/proactive_scheduler.py backend/app/tasks/worker.py
git commit -m "feat: add proactive engagement scheduler with ARQ cron (hourly, 7am-8pm)"
```

---

## Task 12: Create EngagementProfile During Onboarding

**Files:**
- Modify: `backend/app/services/onboarding.py`
- Modify: `backend/tests/test_onboarding.py`

**Step 1: Modify onboarding to create EngagementProfile**

In `_handle_plants()` (the final onboarding step), after setting `user.onboarding_complete = True`, add:

```python
from app.models.engagement_profile import EngagementProfile

# Create default engagement profile
profile = EngagementProfile(
    user_id=user.id,
    preferred_time="morning",
    notification_level="normal",
)
session.add(profile)
```

**Step 2: Also create a GrowingSeason**

```python
from app.models.growing_season import GrowingSeason
from datetime import date

# Create initial growing season
current_year = date.today().year
season = GrowingSeason(
    user_id=user.id,
    year=current_year,
    label=f"Spring/Summer {current_year}",
    started_at=date.today(),
)
session.add(season)
```

**Step 3: Update existing onboarding tests**

In `backend/tests/test_onboarding.py`, add assertions that EngagementProfile and GrowingSeason are created.

**Step 4: Run tests**

Run: `cd "/Users/nickdavie/2026 Gardening App/backend" && python -m pytest tests/test_onboarding.py -v`
Expected: PASS

**Step 5: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/services/onboarding.py backend/tests/test_onboarding.py
git commit -m "feat: create EngagementProfile and GrowingSeason during onboarding"
```

---

## Task 13: Daily Weather Logging Task

**Files:**
- Create: `backend/app/tasks/weather_logger.py`
- Modify: `backend/app/tasks/worker.py`

**Step 1: Create the weather logging task**

Create `backend/app/tasks/weather_logger.py`:

```python
"""Daily weather logger — captures weather for all active postcodes.

Runs once daily via ARQ cron. Stores in weather_logs table for
historical correlation with plant outcomes.
"""

import logging
from datetime import date

from sqlalchemy import select, func

from app.core.database import async_session
from app.models.user import User
from app.models.weather_log import WeatherLog
from app.services.weather import WeatherService

logger = logging.getLogger(__name__)


async def log_daily_weather() -> None:
    """Fetch and store today's weather for all active postcodes."""
    weather = WeatherService()

    try:
        async with async_session() as session:
            # Get distinct postcodes for onboarded users
            result = await session.execute(
                select(func.distinct(User.postcode_outward), User.latitude, User.longitude)
                .where(
                    User.onboarding_complete == True,  # noqa: E712
                    User.postcode_outward.isnot(None),
                    User.latitude.isnot(None),
                )
            )
            postcodes = result.all()

            if not postcodes:
                logger.info("No active postcodes, skipping weather logging")
                return

            today = date.today()

            for postcode, lat, lon in postcodes:
                # Skip if already logged today
                existing = await session.execute(
                    select(WeatherLog).where(
                        WeatherLog.postcode_outward == postcode,
                        WeatherLog.date == today,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                try:
                    snapshot = await weather.get_weather_snapshot(float(lat), float(lon))
                    frost_data = await weather.check_frost_risk(float(lat), float(lon))

                    log = WeatherLog(
                        postcode_outward=postcode,
                        date=today,
                        temp_max_c=snapshot.get("temp_max_c"),
                        temp_min_c=snapshot.get("temp_min_c"),
                        rainfall_mm=snapshot.get("rainfall_mm"),
                        wind_max_kmh=snapshot.get("wind_kmh"),
                        frost=frost_data.get("frost_risk", False),
                    )
                    session.add(log)
                except Exception:
                    logger.exception("Failed to log weather for %s", postcode)

            await session.commit()
            logger.info("Weather logged for %d postcodes", len(postcodes))

    finally:
        await weather.close()
```

**Step 2: Register in ARQ worker as daily cron**

Add to `backend/app/tasks/worker.py`:

```python
from app.tasks.weather_logger import log_daily_weather

# In WorkerSettings.cron_jobs, add:
cron(log_daily_weather, hour=6, minute=0),  # Run at 6am daily
```

**Step 3: Commit**

```bash
cd "/Users/nickdavie/2026 Gardening App"
git add backend/app/tasks/weather_logger.py backend/app/tasks/worker.py
git commit -m "feat: add daily weather logging task for historical weather correlation"
```

---

## Task 14: End-to-End CLI Test

**Files:** None new — manual testing via CLI.

**Step 1: Start services**

```bash
brew services start postgresql@15
# Redis should already be running

cd "/Users/nickdavie/2026 Gardening App/backend"
source .venv/bin/activate
alembic upgrade head
python -m app.cli
```

**Step 2: Test the postcode fix**

Type: `DN35`
Expected: Sage recognises it, shows "North East Lincolnshire" and soil type.

Type: `B44`
Expected: Sage recognises it, shows "Birmingham" area and soil type.

**Step 3: Complete onboarding and test context events**

Walk through: garden type → experience → plants (tomatoes, courgettes, radishes).
Verify: "planted tomatoes today" → Sage logs a context event.
Verify: Ask about weather → Sage uses weather tools.

**Step 4: Verify database state**

```bash
cd "/Users/nickdavie/2026 Gardening App/backend"
source .venv/bin/activate
python -c "
import asyncio
from sqlalchemy import select
from app.core.database import async_session
from app.models.engagement_profile import EngagementProfile
from app.models.growing_season import GrowingSeason
from app.models.context_event import ContextEvent

async def check():
    async with async_session() as s:
        profiles = (await s.execute(select(EngagementProfile))).scalars().all()
        print(f'EngagementProfiles: {len(profiles)}')
        seasons = (await s.execute(select(GrowingSeason))).scalars().all()
        print(f'GrowingSeasons: {len(seasons)}')
        events = (await s.execute(select(ContextEvent))).scalars().all()
        print(f'ContextEvents: {len(events)}')
        for e in events[-5:]:
            print(f'  {e.event_type}: {e.summary}')
            print(f'  weather_snapshot: {e.weather_snapshot}')

asyncio.run(check())
"
```

Expected: EngagementProfile created, GrowingSeason created, context events with weather snapshots.

---

## Summary

| Task | What | Commit message |
|------|------|----------------|
| 1 | Postcode outcode fallback + normalisation | `fix: postcode service handles outward-only codes` |
| 2 | GrowingSeason table | `feat: add GrowingSeason model` |
| 3 | Plant lineage fields | `feat: add lineage tracking to Plant model` |
| 4 | ContextEvent weather_snapshot | `feat: add weather_snapshot to ContextEvent` |
| 5 | WeatherLog table | `feat: add WeatherLog table` |
| 6 | EngagementProfile table | `feat: add EngagementProfile model` |
| 7 | WeatherService.get_weather_snapshot | `feat: add get_weather_snapshot to WeatherService` |
| 8 | Auto weather capture on context events | `feat: auto-capture weather on context events` |
| 9 | EngagementService (sporadic algorithm) | `feat: add EngagementService` |
| 10 | ProactiveMessageBuilder | `feat: add ProactiveMessageBuilder` |
| 11 | Proactive scheduler (ARQ cron) | `feat: add proactive engagement scheduler` |
| 12 | Create profiles during onboarding | `feat: create EngagementProfile during onboarding` |
| 13 | Daily weather logging task | `feat: add daily weather logging` |
| 14 | End-to-end CLI test | Manual verification |
