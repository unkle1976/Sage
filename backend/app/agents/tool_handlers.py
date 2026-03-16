"""Tool handler implementations for Sage orchestrator.

Each handler is an async function that takes (input_data: dict) -> dict.
The `build_tool_handlers` factory wires up services and DB session so the
orchestrator can dispatch tool calls without knowing implementation details.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.plant_milestones import PLANT_MILESTONES
from app.models.context_event import ContextEvent
from app.models.garden import Garden
from app.models.growing_calendar import GrowingCalendar
from app.models.growing_plan_item import GrowingPlanItem
from app.models.plant import Plant
from app.models.plant_spec import PlantSpec
from app.models.user import User
from app.services.growing_plan import GrowingPlanService
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

        # Sanitise event_type: strip XML/HTML tags, truncate to column limit
        import re
        event_type = re.sub(r"<[^>]*>", "", event_type).strip()
        event_type = event_type[:100] if event_type else "observation"

        # Sanitise source_agent similarly
        source_agent = "sage"

        # Find garden
        garden_stmt = select(Garden).where(
            Garden.user_id == user.id, Garden.is_primary.is_(True)
        )
        garden_result = await session.execute(garden_stmt)
        garden = garden_result.scalar_one_or_none()

        # Auto-capture weather snapshot if user has location
        weather_snapshot = None
        lat = float(user.latitude) if user.latitude else None
        lon = float(user.longitude) if user.longitude else None
        if lat is not None and lon is not None:
            try:
                weather_snapshot = await _weather.get_weather_snapshot(lat, lon)
            except Exception:
                pass  # Weather failure must not block event logging

        event = ContextEvent(
            user_id=user.id,
            garden_id=garden.id if garden else None,
            event_type=event_type,
            source_agent=source_agent,
            summary=summary,
            detail=detail,
            weather_snapshot=weather_snapshot,
        )
        session.add(event)
        await session.commit()

        return {"logged": True, "event_type": event_type, "summary": summary}

    async def manage_growing_plan(_input: dict) -> dict:
        action = _input.get("action", "list")
        plant_name = (_input.get("plant_name") or "").strip().lower()

        from sqlalchemy import or_

        if action == "add":
            if not plant_name:
                return {"error": "plant_name is required for the 'add' action."}

            # Find matching PlantSpec
            variants = {plant_name}
            if plant_name.endswith("oes"):
                variants.add(plant_name[:-2])
            elif plant_name.endswith("ies"):
                variants.add(plant_name[:-3] + "y")
            elif plant_name.endswith("s") and not plant_name.endswith("ss"):
                variants.add(plant_name[:-1])

            conditions = [func.lower(PlantSpec.common_name) == v for v in variants]
            conditions.append(func.lower(PlantSpec.common_name).like(f"%{plant_name}%"))
            stmt = select(PlantSpec).where(or_(*conditions)).limit(1)
            result = await session.execute(stmt)
            spec = result.scalar_one_or_none()

            if not spec:
                return {"error": f"No plant found matching '{plant_name}'."}

            # Check timing via GrowingCalendar
            today = datetime.now().date()
            cal_stmt = select(GrowingCalendar).where(
                GrowingCalendar.plant_spec_id == spec.id
            )
            cal_result = await session.execute(cal_stmt)
            cal_entries = cal_result.scalars().all()

            timing = GrowingPlanService.check_timing(cal_entries, today)

            # Determine optimal sow window from calendar
            optimal_start = None
            optimal_end = None
            for entry in cal_entries:
                if entry.activity in ("sow_indoors", "sow_outdoors"):
                    start_date = datetime(today.year, entry.month_start, 1).date()
                    end_date = datetime(today.year, entry.month_end, 28).date()
                    if optimal_start is None or start_date < optimal_start:
                        optimal_start = start_date
                    if optimal_end is None or end_date > optimal_end:
                        optimal_end = end_date

            item = GrowingPlanItem(
                user_id=user.id,
                plant_spec_id=spec.id,
                status=timing.get("status", "queued"),
                optimal_sow_start=optimal_start,
                optimal_sow_end=optimal_end,
            )
            session.add(item)
            await session.commit()

            return {
                "added": True,
                "plant": spec.common_name,
                "timing": timing,
                "optimal_sow_start": str(optimal_start) if optimal_start else None,
                "optimal_sow_end": str(optimal_end) if optimal_end else None,
            }

        elif action == "list":
            stmt = (
                select(GrowingPlanItem, PlantSpec.common_name)
                .join(PlantSpec, GrowingPlanItem.plant_spec_id == PlantSpec.id)
                .where(GrowingPlanItem.user_id == user.id)
                .order_by(GrowingPlanItem.optimal_sow_start.asc().nullslast())
            )
            result = await session.execute(stmt)
            rows = result.all()

            items = []
            for item, name in rows:
                items.append({
                    "plant": name,
                    "status": item.status,
                    "optimal_sow_start": str(item.optimal_sow_start) if item.optimal_sow_start else None,
                    "optimal_sow_end": str(item.optimal_sow_end) if item.optimal_sow_end else None,
                    "added_at": item.added_at.isoformat() if item.added_at else None,
                    "activated_at": item.activated_at.isoformat() if item.activated_at else None,
                })
            return {"items": items, "count": len(items)}

        elif action == "check_timing":
            if not plant_name:
                return {"error": "plant_name is required for 'check_timing'."}

            variants = {plant_name}
            if plant_name.endswith("s") and not plant_name.endswith("ss"):
                variants.add(plant_name[:-1])

            conditions = [func.lower(PlantSpec.common_name) == v for v in variants]
            conditions.append(func.lower(PlantSpec.common_name).like(f"%{plant_name}%"))
            stmt = select(PlantSpec).where(or_(*conditions)).limit(1)
            result = await session.execute(stmt)
            spec = result.scalar_one_or_none()

            if not spec:
                return {"error": f"No plant found matching '{plant_name}'."}

            today = datetime.now().date()
            cal_stmt = select(GrowingCalendar).where(
                GrowingCalendar.plant_spec_id == spec.id
            )
            cal_result = await session.execute(cal_stmt)
            cal_entries = cal_result.scalars().all()

            timing = GrowingPlanService.check_timing(cal_entries, today)
            return {"plant": spec.common_name, "timing": timing}

        elif action == "activate":
            if not plant_name:
                return {"error": "plant_name is required for 'activate'."}

            stmt = (
                select(GrowingPlanItem)
                .join(PlantSpec, GrowingPlanItem.plant_spec_id == PlantSpec.id)
                .where(
                    GrowingPlanItem.user_id == user.id,
                    func.lower(PlantSpec.common_name) == plant_name,
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()

            if not item:
                return {"error": f"No plan item found for '{plant_name}'."}

            item.status = "active"
            item.activated_at = datetime.now()
            await session.commit()
            return {"activated": True, "plant": plant_name}

        elif action == "skip":
            if not plant_name:
                return {"error": "plant_name is required for 'skip'."}

            stmt = (
                select(GrowingPlanItem)
                .join(PlantSpec, GrowingPlanItem.plant_spec_id == PlantSpec.id)
                .where(
                    GrowingPlanItem.user_id == user.id,
                    func.lower(PlantSpec.common_name) == plant_name,
                )
                .limit(1)
            )
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()

            if not item:
                return {"error": f"No plan item found for '{plant_name}'."}

            item.status = "skipped"
            await session.commit()
            return {"skipped": True, "plant": plant_name}

        else:
            return {"error": f"Unknown action: {action}"}

    async def advance_milestone(_input: dict) -> dict:
        plant_name = (_input.get("plant_name") or "").strip().lower()
        user_confirmed = _input.get("user_confirmed", False)
        notes = _input.get("notes")

        if not plant_name:
            return {"error": "plant_name is required."}

        # Find the user's garden and plant
        garden_stmt = select(Garden).where(
            Garden.user_id == user.id, Garden.is_primary.is_(True)
        )
        garden_result = await session.execute(garden_stmt)
        garden = garden_result.scalar_one_or_none()

        if not garden:
            return {"error": "No garden found for user."}

        # Search for the plant by name/variety
        plant_stmt = (
            select(Plant)
            .join(PlantSpec, Plant.plant_spec_id == PlantSpec.id, isouter=True)
            .where(
                Plant.garden_id == garden.id,
                Plant.is_active.is_(True),
                (
                    func.lower(PlantSpec.common_name).like(f"%{plant_name}%")
                    | func.lower(Plant.variety).like(f"%{plant_name}%")
                ),
            )
            .limit(1)
        )
        plant_result = await session.execute(plant_stmt)
        plant = plant_result.scalar_one_or_none()

        if not plant:
            return {"error": f"No active plant found matching '{plant_name}'."}

        # Look up the milestone data for this plant
        # Try to match against PLANT_MILESTONES keys
        spec_stmt = select(PlantSpec).where(PlantSpec.id == plant.plant_spec_id)
        spec_result = await session.execute(spec_stmt)
        spec = spec_result.scalar_one_or_none()

        milestone_key = None
        if spec:
            # Try exact match, then normalised match
            candidate = spec.common_name.lower().replace(" ", "_")
            if candidate in PLANT_MILESTONES:
                milestone_key = candidate
            else:
                # Try partial match
                for key in PLANT_MILESTONES:
                    if key in candidate or candidate in key:
                        milestone_key = key
                        break

        milestones = (
            PLANT_MILESTONES[milestone_key]["milestones"]
            if milestone_key
            else None
        )

        current_index = plant.next_milestone_index or 0
        new_index = current_index + 1

        new_stage = None
        next_milestone_info = None
        next_date = None

        if milestones and new_index < len(milestones):
            next_ms = milestones[new_index]
            new_stage = next_ms["stage"]
            next_milestone_info = next_ms.get("check_in")

            # Calculate next milestone date from planting_date
            if plant.planting_date and new_index + 1 < len(milestones):
                from datetime import timedelta
                future_ms = milestones[new_index + 1]
                next_date = plant.planting_date + timedelta(days=future_ms["day"])
        elif milestones and new_index >= len(milestones):
            new_stage = milestones[-1]["stage"]
            next_milestone_info = "All milestones complete!"
        else:
            new_stage = plant.growth_stage

        # Update the plant record
        plant.next_milestone_index = new_index
        if new_stage:
            plant.growth_stage = new_stage
        if next_date:
            plant.next_milestone_date = next_date

        # Log a context event
        event = ContextEvent(
            user_id=user.id,
            garden_id=garden.id,
            event_type="milestone",
            source_agent="sage",
            summary=f"{spec.common_name if spec else plant_name} reached milestone: {new_stage}",
            detail={
                "plant_name": spec.common_name if spec else plant_name,
                "milestone_index": new_index,
                "stage": new_stage,
                "user_confirmed": user_confirmed,
                "notes": notes,
            },
        )
        session.add(event)
        await session.commit()

        return {
            "advanced": True,
            "plant": spec.common_name if spec else plant_name,
            "new_stage": new_stage,
            "milestone_index": new_index,
            "next_milestone_date": str(next_date) if next_date else None,
            "next_check_in": next_milestone_info,
        }

    return {
        "get_weather_forecast": get_weather_forecast,
        "check_frost_risk": check_frost_risk,
        "get_watering_guidance": get_watering_guidance,
        "get_soil_profile": get_soil_profile,
        "search_plant_database": search_plant_database,
        "get_growing_calendar": get_growing_calendar,
        "log_context_event": log_context_event,
        "manage_growing_plan": manage_growing_plan,
        "advance_milestone": advance_milestone,
    }
