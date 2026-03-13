"""AlertService — generates proactive alerts (frost, watering, sowing windows) for users."""

import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.garden import Garden
from app.models.growing_calendar import GrowingCalendar
from app.models.plant import Plant
from app.services.weather import WeatherService

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, session: AsyncSession, weather: WeatherService):
        self._session = session
        self._weather = weather

    # ------------------------------------------------------------------
    # Deduplication helper
    # ------------------------------------------------------------------

    async def _alert_exists_today(self, user_id: uuid.UUID, alert_type: str) -> bool:
        """Check if an alert of this type already exists for the user today."""
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start.replace(hour=23, minute=59, second=59, microsecond=999999)

        stmt = (
            select(func.count())
            .select_from(Alert)
            .where(
                Alert.user_id == user_id,
                Alert.alert_type == alert_type,
                Alert.created_at >= today_start,
                Alert.created_at <= today_end,
            )
        )
        result = await self._session.execute(stmt)
        count = result.scalar()
        return count > 0

    # ------------------------------------------------------------------
    # Frost alerts
    # ------------------------------------------------------------------

    async def check_frost_alerts(self, users: list) -> list[Alert]:
        """Check weather for each user and create frost warning alerts."""
        alerts: list[Alert] = []

        for user in users:
            if user.latitude is None or user.longitude is None:
                continue

            try:
                frost_data = await self._weather.check_frost_risk(
                    float(user.latitude), float(user.longitude)
                )
            except Exception:
                logger.exception("Failed to check frost risk for user %s", user.id)
                continue

            if not frost_data.get("frost_risk"):
                continue

            if await self._alert_exists_today(user.id, "frost_warning"):
                logger.debug("Frost alert already exists today for user %s", user.id)
                continue

            min_temp = frost_data.get("min_temperature", 0)
            frost_hours = frost_data.get("frost_hours", [])
            hour_count = len(frost_hours)

            message = (
                f"Frost warning! Temperatures dropping to {min_temp}\u00b0C tonight "
                f"with {hour_count} hour{'s' if hour_count != 1 else ''} below 2\u00b0C. "
                "Consider protecting tender plants with fleece or moving pots indoors."
            )

            alert = Alert(
                id=uuid.uuid4(),
                user_id=user.id,
                alert_type="frost_warning",
                priority="high",
                scheduled_for=datetime.now(timezone.utc),
                delivery_status="pending",
                message_content=message,
                source_agent="alert_scheduler",
                reasoning=f"Frost risk detected: min temp {min_temp}C, {hour_count} frost hours",
            )

            self._session.add(alert)
            alerts.append(alert)

        if alerts:
            await self._session.commit()

        return alerts

    # ------------------------------------------------------------------
    # Watering reminders
    # ------------------------------------------------------------------

    async def check_watering_reminders(self, users: list) -> list[Alert]:
        """Check weather for each user and create watering reminders."""
        alerts: list[Alert] = []

        for user in users:
            if user.latitude is None or user.longitude is None:
                continue

            try:
                guidance = await self._weather.get_watering_guidance(
                    float(user.latitude), float(user.longitude)
                )
            except Exception:
                logger.exception("Failed to get watering guidance for user %s", user.id)
                continue

            if not guidance.get("needs_watering"):
                continue

            if await self._alert_exists_today(user.id, "watering_reminder"):
                logger.debug("Watering alert already exists today for user %s", user.id)
                continue

            max_temp = guidance.get("max_temperature", 0)
            recent = guidance.get("recent_rainfall_mm", 0)
            forecast = guidance.get("forecast_rainfall_mm", 0)

            message = (
                f"Your plants could do with a drink! No significant rain recently "
                f"({recent}mm) and none forecast ({forecast}mm), with temps up to "
                f"{max_temp}\u00b0C. Best to water in the early morning or evening."
            )

            alert = Alert(
                id=uuid.uuid4(),
                user_id=user.id,
                alert_type="watering_reminder",
                priority="medium",
                scheduled_for=datetime.now(timezone.utc),
                delivery_status="pending",
                message_content=message,
                source_agent="alert_scheduler",
                reasoning=f"Dry conditions: {recent}mm recent rain, {forecast}mm forecast, max {max_temp}C",
            )

            self._session.add(alert)
            alerts.append(alert)

        if alerts:
            await self._session.commit()

        return alerts

    # ------------------------------------------------------------------
    # Sowing window alerts
    # ------------------------------------------------------------------

    async def check_sowing_windows(self, users: list) -> list[Alert]:
        """Compare growing calendar with current month to generate sowing alerts."""
        alerts: list[Alert] = []
        today = date.today()
        current_month = today.month

        for user in users:
            if not user.uk_region:
                continue

            # Get user's gardens
            garden_result = await self._session.execute(
                select(Garden).where(Garden.user_id == user.id)
            )
            gardens = garden_result.scalars().all()
            if not gardens:
                continue

            garden_ids = [g.id for g in gardens]

            # Get active plants across all gardens
            plant_result = await self._session.execute(
                select(Plant).where(
                    Plant.garden_id.in_(garden_ids),
                    Plant.is_active == True,  # noqa: E712
                )
            )
            plants = plant_result.scalars().all()
            if not plants:
                continue

            plant_spec_ids = [p.plant_spec_id for p in plants if p.plant_spec_id]

            # Get matching calendar entries for user's region and plants
            cal_result = await self._session.execute(
                select(GrowingCalendar).where(
                    GrowingCalendar.plant_spec_id.in_(plant_spec_ids),
                    GrowingCalendar.uk_region == user.uk_region,
                    GrowingCalendar.month_start <= current_month,
                    GrowingCalendar.month_end >= current_month,
                )
            )
            calendar_entries = cal_result.scalars().all()

            # Build a lookup from plant_spec_id to plant
            spec_to_plant = {p.plant_spec_id: p for p in plants if p.plant_spec_id}

            for entry in calendar_entries:
                plant = spec_to_plant.get(entry.plant_spec_id)
                if not plant:
                    continue

                if await self._alert_exists_today(user.id, "sowing_window"):
                    continue

                activity_label = entry.activity.replace("_", " ")
                message = (
                    f"It's a good time to {activity_label}! The window runs from "
                    f"month {entry.month_start} to {entry.month_end} in your region."
                )

                alert = Alert(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    plant_id=plant.id,
                    alert_type="sowing_window",
                    priority="low",
                    scheduled_for=datetime.now(timezone.utc),
                    delivery_status="pending",
                    message_content=message,
                    source_agent="alert_scheduler",
                    reasoning=f"Sowing window open: {entry.activity} month {entry.month_start}-{entry.month_end}",
                )

                self._session.add(alert)
                alerts.append(alert)

        if alerts:
            await self._session.commit()

        return alerts
