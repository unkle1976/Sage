"""Seed the database with 50 UK edible plants and their regional growing calendars.

Usage:
    python -m app.data.seed_plants
"""

import asyncio
import json
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.growing_calendar import GrowingCalendar
from app.models.plant_spec import PlantSpec

DATA_FILE = Path(__file__).parent / "plants.json"

REGIONS = ["South", "Midlands", "North", "Scotland"]


def load_plants_json() -> list[dict]:
    """Load and return the plants data from plants.json."""
    with open(DATA_FILE) as f:
        return json.load(f)


def _plant_dict_to_model(entry: dict) -> PlantSpec:
    """Convert a JSON plant entry to a PlantSpec model instance."""
    return PlantSpec(
        id=uuid.uuid4(),
        common_name=entry["common_name"],
        botanical_name=entry.get("botanical_name"),
        category=entry["category"],
        uk_hardiness=entry.get("uk_hardiness"),
        growing_difficulty=entry.get("growing_difficulty"),
        soil_preferences=entry.get("soil_preferences"),
        sun_requirements=entry.get("sun_requirements"),
        water_needs=entry.get("water_needs"),
        spacing_cm=entry.get("spacing_cm"),
        days_to_germination_min=entry.get("days_to_germination_min"),
        days_to_germination_max=entry.get("days_to_germination_max"),
        days_to_harvest_min=entry.get("days_to_harvest_min"),
        days_to_harvest_max=entry.get("days_to_harvest_max"),
        common_pests=entry.get("common_pests"),
        common_diseases=entry.get("common_diseases"),
        companion_plants=entry.get("companion_plants"),
        antagonist_plants=entry.get("antagonist_plants"),
    )


def _calendar_entries(plant_id: uuid.UUID, entry: dict) -> list[GrowingCalendar]:
    """Build GrowingCalendar rows from the growing_calendar section of a plant entry."""
    calendars: list[GrowingCalendar] = []
    cal_data = entry.get("growing_calendar", {})
    for region, activities in cal_data.items():
        for activity, months in activities.items():
            calendars.append(
                GrowingCalendar(
                    id=uuid.uuid4(),
                    plant_spec_id=plant_id,
                    uk_region=region,
                    activity=activity,
                    month_start=months[0],
                    month_end=months[1],
                )
            )
    return calendars


async def seed(session: AsyncSession) -> dict[str, int]:
    """Seed PlantSpec and GrowingCalendar tables. Idempotent — skips existing plants.

    Returns counts of created plants and calendar entries.
    """
    plants_data = load_plants_json()

    # Fetch existing plant names for idempotency
    result = await session.execute(select(PlantSpec.common_name))
    existing_names: set[str] = {row[0] for row in result.all()}

    plants_created = 0
    calendars_created = 0

    new_plants: list[tuple[PlantSpec, dict]] = []
    for entry in plants_data:
        if entry["common_name"] in existing_names:
            continue
        plant = _plant_dict_to_model(entry)
        session.add(plant)
        new_plants.append((plant, entry))
        plants_created += 1

    # Flush plants first so FKs exist for calendar rows
    if new_plants:
        await session.flush()

    for plant, entry in new_plants:
        calendar_rows = _calendar_entries(plant.id, entry)
        for cal in calendar_rows:
            session.add(cal)
        calendars_created += len(calendar_rows)

    await session.commit()
    return {"plants_created": plants_created, "calendars_created": calendars_created}


async def main() -> None:
    """Entry point for running as a standalone script."""
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        counts = await seed(session)

    await engine.dispose()

    print(f"Seed complete: {counts['plants_created']} plants, {counts['calendars_created']} calendar entries created.")
    if counts["plants_created"] == 0:
        print("(All plants already existed — nothing to do.)")


if __name__ == "__main__":
    asyncio.run(main())
