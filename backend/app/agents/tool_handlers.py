"""Tool handler implementations for Sage orchestrator.

Each handler is an async function that takes (input_data: dict) -> dict.
The `build_tool_handlers` factory wires up services and DB session so the
orchestrator can dispatch tool calls without knowing implementation details.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context_event import ContextEvent
from app.models.garden import Garden
from app.models.growing_calendar import GrowingCalendar
from app.models.plant import Plant
from app.models.plant_spec import PlantSpec
from app.models.user import User
from app.services.soil import SoilService, UK_SOIL_DEFAULTS, UK_REGION_SOIL_DEFAULTS
from app.services.weather import WeatherService


def build_tool_handlers(
    user: User,
    session: AsyncSession,
    weather_service: WeatherService | None = None,
    soil_service: SoilService | None = None,
) -> dict:
    """Return a dict of {tool_name: async handler} bound to the given user/session."""

    _weather = weather_service or WeatherService()
    _soil = soil_service or SoilService()

    async def get_weather_forecast(_input: dict) -> dict:
        lat = float(user.latitude) if user.latitude else None
        lon = float(user.longitude) if user.longitude else None
        if lat is None or lon is None:
            return {"error": "No location set — complete onboarding first."}
        try:
            data = await _weather.get_forecast(lat, lon)
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            highs = daily.get("temperature_2m_max", [])
            lows = daily.get("temperature_2m_min", [])
            rain = daily.get("precipitation_sum", [])

            forecast = []
            for i, d in enumerate(dates):
                forecast.append({
                    "date": d,
                    "high_c": highs[i] if i < len(highs) else None,
                    "low_c": lows[i] if i < len(lows) else None,
                    "rain_mm": rain[i] if i < len(rain) else None,
                })
            return {
                "location": user.uk_region or "UK",
                "forecast": forecast,
            }
        except Exception as e:
            return {"error": f"Weather API error: {e}"}

    async def check_frost_risk(_input: dict) -> dict:
        lat = float(user.latitude) if user.latitude else None
        lon = float(user.longitude) if user.longitude else None
        if lat is None or lon is None:
            return {"error": "No location set."}
        try:
            return await _weather.check_frost_risk(lat, lon)
        except Exception as e:
            return {"error": f"Frost check error: {e}"}

    async def get_watering_guidance(_input: dict) -> dict:
        lat = float(user.latitude) if user.latitude else None
        lon = float(user.longitude) if user.longitude else None
        if lat is None or lon is None:
            return {"error": "No location set."}
        try:
            return await _weather.get_watering_guidance(lat, lon)
        except Exception as e:
            return {"error": f"Watering check error: {e}"}

    async def get_soil_profile(_input: dict) -> dict:
        soil_type = user.soil_type or "unknown"
        region = (user.uk_region or "").lower()

        # Try to get rich soil data from our defaults tables
        profile = UK_SOIL_DEFAULTS.get(region)
        if not profile:
            profile = UK_REGION_SOIL_DEFAULTS.get(region)
        if not profile:
            profile = {"soil_type": soil_type}

        return {
            "location": user.uk_region or "UK",
            **profile,
        }

    async def search_plant_database(_input: dict) -> dict:
        query = _input.get("query", "").strip()
        if not query:
            return {"error": "No search query provided."}

        lower = query.lower()
        # Build search variants (same plural logic as onboarding)
        variants = {lower}
        if lower.endswith("oes"):
            variants.add(lower[:-2])
        elif lower.endswith("ies"):
            variants.add(lower[:-3] + "y")
        elif lower.endswith("s") and not lower.endswith("ss"):
            variants.add(lower[:-1])

        from sqlalchemy import or_

        conditions = [func.lower(PlantSpec.common_name) == v for v in variants]
        # Also do LIKE search for partial matches
        conditions.append(func.lower(PlantSpec.common_name).like(f"%{lower}%"))

        stmt = select(PlantSpec).where(or_(*conditions)).limit(5)
        result = await session.execute(stmt)
        specs = result.scalars().all()

        if not specs:
            return {"results": [], "message": f"No plants found matching '{query}'."}

        results = []
        for spec in specs:
            results.append({
                "common_name": spec.common_name,
                "botanical_name": spec.botanical_name,
                "category": spec.category,
                "difficulty": spec.growing_difficulty,
                "hardiness": spec.uk_hardiness,
                "sun": spec.sun_requirements,
                "water_needs": spec.water_needs,
                "spacing_cm": spec.spacing_cm,
                "days_to_harvest": f"{spec.days_to_harvest_min}-{spec.days_to_harvest_max}" if spec.days_to_harvest_min else None,
                "soil_preferences": spec.soil_preferences,
                "common_pests": spec.common_pests,
                "common_diseases": spec.common_diseases,
                "companion_plants": spec.companion_plants,
                "notes": spec.notes,
            })
        return {"results": results}

    async def get_growing_calendar(_input: dict) -> dict:
        month = _input.get("month") or datetime.now().month
        region = user.uk_region or "UK"

        # Get the user's plants
        garden_stmt = select(Garden).where(
            Garden.user_id == user.id, Garden.is_primary.is_(True)
        )
        garden_result = await session.execute(garden_stmt)
        garden = garden_result.scalar_one_or_none()

        plant_spec_ids = []
        if garden:
            plant_stmt = select(Plant.plant_spec_id).where(
                Plant.garden_id == garden.id,
                Plant.is_active.is_(True),
                Plant.plant_spec_id.isnot(None),
            )
            plant_result = await session.execute(plant_stmt)
            plant_spec_ids = [row[0] for row in plant_result.all()]

        # Query calendar entries for this month
        cal_stmt = select(
            GrowingCalendar, PlantSpec.common_name
        ).join(
            PlantSpec, GrowingCalendar.plant_spec_id == PlantSpec.id
        ).where(
            GrowingCalendar.month_start <= month,
            GrowingCalendar.month_end >= month,
        )

        # If user has plants, prioritise those but also show general suggestions
        cal_result = await session.execute(cal_stmt)
        entries = cal_result.all()

        your_plants = []
        suggestions = []
        for cal_entry, plant_name in entries:
            item = {
                "plant": plant_name,
                "activity": cal_entry.activity,
                "notes": cal_entry.notes,
            }
            if cal_entry.plant_spec_id in plant_spec_ids:
                your_plants.append(item)
            else:
                suggestions.append(item)

        return {
            "month": datetime(2000, month, 1).strftime("%B"),
            "region": region,
            "your_plants": your_plants,
            "other_suggestions": suggestions[:10],  # Cap suggestions
        }

    async def log_context_event(_input: dict) -> dict:
        event_type = _input.get("event_type", "observation")
        summary = _input.get("summary", "")
        detail = _input.get("detail")

        # Find garden
        garden_stmt = select(Garden).where(
            Garden.user_id == user.id, Garden.is_primary.is_(True)
        )
        garden_result = await session.execute(garden_stmt)
        garden = garden_result.scalar_one_or_none()

        event = ContextEvent(
            user_id=user.id,
            garden_id=garden.id if garden else None,
            event_type=event_type,
            source_agent="sage",
            summary=summary,
            detail=detail,
        )
        session.add(event)
        await session.commit()

        return {"logged": True, "event_type": event_type, "summary": summary}

    return {
        "get_weather_forecast": get_weather_forecast,
        "check_frost_risk": check_frost_risk,
        "get_watering_guidance": get_watering_guidance,
        "get_soil_profile": get_soil_profile,
        "search_plant_database": search_plant_database,
        "get_growing_calendar": get_growing_calendar,
        "log_context_event": log_context_event,
    }
