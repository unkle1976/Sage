import pytest
from sqlalchemy import text

from app.core.database import engine


@pytest.fixture
async def db_engine():
    yield engine
    await engine.dispose()


@pytest.mark.asyncio
async def test_database_connection(db_engine):
    async with db_engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1


@pytest.mark.asyncio
async def test_tables_exist(db_engine):
    expected_tables = {
        "users",
        "gardens",
        "plants",
        "alerts",
        "context_events",
        "conversation_messages",
        "achievements",
        "photo_records",
        "plant_specs",
        "growing_calendar",
    }
    async with db_engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
        actual_tables = {row[0] for row in result.fetchall()}
    assert expected_tables.issubset(actual_tables)
