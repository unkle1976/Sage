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


async def log_daily_weather(_ctx: dict) -> None:
    """Fetch and store today's weather for all active postcodes."""
    weather = WeatherService()

    try:
        async with async_session() as session:
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

                    log_entry = WeatherLog(
                        postcode_outward=postcode,
                        date=today,
                        temp_max_c=snapshot.get("temp_max_c"),
                        temp_min_c=snapshot.get("temp_min_c"),
                        rainfall_mm=snapshot.get("rainfall_mm"),
                        wind_max_kmh=snapshot.get("wind_kmh"),
                        frost=frost_data.get("frost_risk", False),
                    )
                    session.add(log_entry)
                except Exception:
                    logger.exception("Failed to log weather for %s", postcode)

            await session.commit()
            logger.info("Weather logged for %d postcodes", len(postcodes))

    finally:
        await weather.close()
