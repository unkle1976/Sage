"""Tests for proactive alert scheduler — frost, watering, and sowing window alerts."""

import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.alerts import AlertService
from app.tasks.alert_scheduler import run_alert_checks


# ---------------------------------------------------------------------------
# Helpers — lightweight stand-ins for ORM rows
# ---------------------------------------------------------------------------

def _make_user(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "whatsapp_phone": "447700900000",
        "display_name": "Test User",
        "latitude": Decimal("51.509865"),
        "longitude": Decimal("-0.118092"),
        "uk_region": "south_east",
        "onboarding_complete": True,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_plant(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "garden_id": uuid.uuid4(),
        "plant_spec_id": uuid.uuid4(),
        "is_active": True,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_garden(user_id, **overrides):
    defaults = {
        "id": uuid.uuid4(),
        "user_id": user_id,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


def _make_calendar_entry(**overrides):
    defaults = {
        "id": uuid.uuid4(),
        "plant_spec_id": uuid.uuid4(),
        "uk_region": "south_east",
        "activity": "sow_outdoors",
        "month_start": 3,
        "month_end": 5,
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def session():
    """A mock async database session."""
    s = AsyncMock()
    # execute returns a result with .scalars().all()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    result_mock.scalar.return_value = 0
    s.execute = AsyncMock(return_value=result_mock)
    s.commit = AsyncMock()
    s.add = MagicMock()
    return s


@pytest.fixture
def weather_service():
    ws = AsyncMock()
    ws.check_frost_risk = AsyncMock(return_value={
        "frost_risk": False,
        "frost_hours": [],
        "min_temperature": 8.0,
    })
    ws.get_watering_guidance = AsyncMock(return_value={
        "needs_watering": False,
        "recent_rainfall_mm": 12.0,
        "forecast_rainfall_mm": 8.0,
        "max_temperature": 16,
    })
    return ws


@pytest.fixture
def queue():
    q = AsyncMock()
    q.enqueue_outbound = AsyncMock()
    return q


# ===========================================================================
# AlertService — frost alerts
# ===========================================================================


class TestFrostAlerts:
    async def test_creates_alert_when_frost_risk(self, session, weather_service):
        user = _make_user()
        weather_service.check_frost_risk = AsyncMock(return_value={
            "frost_risk": True,
            "frost_hours": [
                {"time": "2026-03-14T03:00", "temperature": -1.2},
                {"time": "2026-03-14T04:00", "temperature": 0.5},
            ],
            "min_temperature": -1.2,
        })

        # No existing alert for today (dedup check returns 0)
        dedup_result = MagicMock()
        dedup_result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=dedup_result)

        svc = AlertService(session, weather_service)
        alerts = await svc.check_frost_alerts([user])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == "frost_warning"
        assert alert.priority == "high"
        assert alert.user_id == user.id
        assert "-1.2" in alert.message_content
        session.add.assert_called_once()
        session.commit.assert_called()

    async def test_no_alert_when_no_frost_risk(self, session, weather_service):
        user = _make_user()
        # weather_service already returns frost_risk=False by default

        svc = AlertService(session, weather_service)
        alerts = await svc.check_frost_alerts([user])

        assert len(alerts) == 0
        session.add.assert_not_called()

    async def test_skips_user_without_location(self, session, weather_service):
        user = _make_user(latitude=None, longitude=None)

        svc = AlertService(session, weather_service)
        alerts = await svc.check_frost_alerts([user])

        assert len(alerts) == 0
        weather_service.check_frost_risk.assert_not_called()

    async def test_no_duplicate_frost_alert_today(self, session, weather_service):
        user = _make_user()
        weather_service.check_frost_risk = AsyncMock(return_value={
            "frost_risk": True,
            "frost_hours": [{"time": "2026-03-14T03:00", "temperature": 1.0}],
            "min_temperature": 1.0,
        })

        # Dedup check returns 1 — alert already exists today
        dedup_result = MagicMock()
        dedup_result.scalar.return_value = 1
        session.execute = AsyncMock(return_value=dedup_result)

        svc = AlertService(session, weather_service)
        alerts = await svc.check_frost_alerts([user])

        assert len(alerts) == 0
        session.add.assert_not_called()


# ===========================================================================
# AlertService — watering reminders
# ===========================================================================


class TestWateringReminders:
    async def test_creates_alert_when_watering_needed(self, session, weather_service):
        user = _make_user()
        weather_service.get_watering_guidance = AsyncMock(return_value={
            "needs_watering": True,
            "recent_rainfall_mm": 1.2,
            "forecast_rainfall_mm": 0.0,
            "max_temperature": 24,
        })

        dedup_result = MagicMock()
        dedup_result.scalar.return_value = 0
        session.execute = AsyncMock(return_value=dedup_result)

        svc = AlertService(session, weather_service)
        alerts = await svc.check_watering_reminders([user])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == "watering_reminder"
        assert alert.priority == "medium"
        assert alert.user_id == user.id
        session.add.assert_called_once()
        session.commit.assert_called()

    async def test_no_alert_when_watering_not_needed(self, session, weather_service):
        user = _make_user()
        # default fixture already returns needs_watering=False

        svc = AlertService(session, weather_service)
        alerts = await svc.check_watering_reminders([user])

        assert len(alerts) == 0
        session.add.assert_not_called()

    async def test_no_duplicate_watering_alert_today(self, session, weather_service):
        user = _make_user()
        weather_service.get_watering_guidance = AsyncMock(return_value={
            "needs_watering": True,
            "recent_rainfall_mm": 0.0,
            "forecast_rainfall_mm": 0.0,
            "max_temperature": 25,
        })

        dedup_result = MagicMock()
        dedup_result.scalar.return_value = 1
        session.execute = AsyncMock(return_value=dedup_result)

        svc = AlertService(session, weather_service)
        alerts = await svc.check_watering_reminders([user])

        assert len(alerts) == 0


# ===========================================================================
# AlertService — sowing window alerts
# ===========================================================================


class TestSowingWindowAlerts:
    async def test_creates_alert_when_sowing_window_open(self, session, weather_service):
        user = _make_user(uk_region="south_east")
        garden = _make_garden(user.id)
        plant = _make_plant(garden_id=garden.id, plant_spec_id=uuid.uuid4())

        cal_entry = _make_calendar_entry(
            plant_spec_id=plant.plant_spec_id,
            uk_region="south_east",
            activity="sow_outdoors",
            month_start=3,
            month_end=5,
        )

        # First call: gardens query; second: plants query; third: calendar query; fourth: dedup
        call_count = 0

        async def mock_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                # gardens for user
                result.scalars.return_value.all.return_value = [garden]
            elif call_count == 2:
                # active plants
                result.scalars.return_value.all.return_value = [plant]
            elif call_count == 3:
                # growing calendar entries
                result.scalars.return_value.all.return_value = [cal_entry]
            elif call_count >= 4:
                # dedup check
                result.scalar.return_value = 0
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        svc = AlertService(session, weather_service)
        with patch("app.services.alerts.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 15)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            alerts = await svc.check_sowing_windows([user])

        assert len(alerts) == 1
        alert = alerts[0]
        assert alert.alert_type == "sowing_window"
        assert alert.priority == "low"
        assert alert.plant_id == plant.id

    async def test_no_alert_when_outside_sowing_window(self, session, weather_service):
        """When month is outside the calendar window, the SQL query returns no entries."""
        user = _make_user(uk_region="south_east")
        garden = _make_garden(user.id)
        plant = _make_plant(garden_id=garden.id)

        # Calendar entry is June-August, but current month will be January.
        # In the real DB the WHERE clause filters this out, so mock returns empty.
        call_count = 0

        async def mock_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.scalars.return_value.all.return_value = [garden]
            elif call_count == 2:
                result.scalars.return_value.all.return_value = [plant]
            elif call_count == 3:
                # No matching calendar entries (month filter excludes them)
                result.scalars.return_value.all.return_value = []
            elif call_count >= 4:
                result.scalar.return_value = 0
            return result

        session.execute = AsyncMock(side_effect=mock_execute)

        svc = AlertService(session, weather_service)
        with patch("app.services.alerts.date") as mock_date:
            mock_date.today.return_value = date(2026, 1, 10)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            alerts = await svc.check_sowing_windows([user])

        assert len(alerts) == 0

    async def test_skips_user_without_region(self, session, weather_service):
        user = _make_user(uk_region=None)

        svc = AlertService(session, weather_service)
        alerts = await svc.check_sowing_windows([user])

        assert len(alerts) == 0


# ===========================================================================
# run_alert_checks — top-level scheduler function
# ===========================================================================


class TestRunAlertChecks:
    async def test_runs_all_check_types(self):
        mock_session = AsyncMock()
        mock_weather = AsyncMock()
        mock_queue = AsyncMock()

        users = [_make_user(), _make_user(whatsapp_phone="447700900001")]

        # Mock session to return users
        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = users
        mock_session.execute = AsyncMock(return_value=user_result)

        with patch("app.tasks.alert_scheduler.AlertService") as MockAlertSvc, \
             patch("app.tasks.alert_scheduler.async_session") as mock_session_maker, \
             patch("app.tasks.alert_scheduler.WeatherService") as MockWeather, \
             patch("app.tasks.alert_scheduler.MessageQueue") as MockQueue:

            # Set up the context manager for async_session
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_weather_instance = AsyncMock()
            MockWeather.return_value = mock_weather_instance

            mock_queue_instance = AsyncMock()
            MockQueue.return_value = mock_queue_instance

            svc_instance = AsyncMock()
            svc_instance.check_frost_alerts = AsyncMock(return_value=[])
            svc_instance.check_watering_reminders = AsyncMock(return_value=[])
            svc_instance.check_sowing_windows = AsyncMock(return_value=[])
            MockAlertSvc.return_value = svc_instance

            await run_alert_checks()

            svc_instance.check_frost_alerts.assert_called_once_with(users)
            svc_instance.check_watering_reminders.assert_called_once_with(users)
            svc_instance.check_sowing_windows.assert_called_once_with(users)

    async def test_enqueues_outbound_messages_for_alerts(self):
        mock_session = AsyncMock()
        mock_weather = AsyncMock()

        user = _make_user()
        users = [user]

        user_result = MagicMock()
        user_result.scalars.return_value.all.return_value = users
        mock_session.execute = AsyncMock(return_value=user_result)

        frost_alert = MagicMock(
            user_id=user.id,
            message_content="Frost warning tonight!",
            alert_type="frost_warning",
        )

        with patch("app.tasks.alert_scheduler.AlertService") as MockAlertSvc, \
             patch("app.tasks.alert_scheduler.async_session") as mock_session_maker, \
             patch("app.tasks.alert_scheduler.WeatherService") as MockWeather, \
             patch("app.tasks.alert_scheduler.MessageQueue") as MockQueue:

            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=False)

            mock_weather_instance = AsyncMock()
            MockWeather.return_value = mock_weather_instance

            mock_queue_instance = AsyncMock()
            mock_queue_instance.connect = AsyncMock()
            mock_queue_instance.enqueue_outbound = AsyncMock()
            mock_queue_instance.close = AsyncMock()
            MockQueue.return_value = mock_queue_instance

            svc_instance = AsyncMock()
            svc_instance.check_frost_alerts = AsyncMock(return_value=[frost_alert])
            svc_instance.check_watering_reminders = AsyncMock(return_value=[])
            svc_instance.check_sowing_windows = AsyncMock(return_value=[])
            MockAlertSvc.return_value = svc_instance

            await run_alert_checks()

            mock_queue_instance.enqueue_outbound.assert_called_once()
            call_args = mock_queue_instance.enqueue_outbound.call_args[0][0]
            assert call_args["to"] == user.whatsapp_phone
            assert call_args["text"] == "Frost warning tonight!"
            assert call_args["type"] == "text"
