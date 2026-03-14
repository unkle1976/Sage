"""ARQ worker configuration for background message processing."""

import logging

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import settings
from app.tasks.proactive_scheduler import run_proactive_checks
from app.tasks.process_message import process_inbound_message
from app.tasks.weather_logger import log_daily_weather

logger = logging.getLogger(__name__)


def parse_redis_url(url: str) -> RedisSettings:
    """Convert a redis:// URL into ARQ RedisSettings."""
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip("/") or 0),
        password=parsed.password,
    )


async def startup(ctx: dict) -> None:
    """Called once when the worker starts."""
    logger.info("Sage worker starting up")


async def shutdown(ctx: dict) -> None:
    """Called once when the worker shuts down."""
    logger.info("Sage worker shutting down")


class WorkerSettings:
    """ARQ worker settings — pass this class to ``arq worker``."""

    functions = [process_inbound_message]
    cron_jobs = [
        cron(log_daily_weather, hour=6, minute=0),
        cron(run_proactive_checks, hour={7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20}),
    ]
    redis_settings = parse_redis_url(settings.redis_url)
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 120
