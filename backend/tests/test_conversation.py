import uuid
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.conversation import ConversationService
from app.models.conversation import ConversationMessage
from app.models.user import User
from app.models.garden import Garden
from app.models.plant import Plant
from app.models.context_event import ContextEvent


@pytest.fixture
def mock_session():
    return AsyncMock()


@pytest.fixture
def service(mock_session):
    return ConversationService(mock_session)


@pytest.fixture
def user_id():
    return uuid.uuid4()


# --- store_message ---


async def test_store_message_creates_record(service, mock_session, user_id):
    await service.store_message(user_id, "user", "Hello Sage!")

    mock_session.add.assert_called_once()
    msg = mock_session.add.call_args[0][0]
    assert isinstance(msg, ConversationMessage)
    assert msg.user_id == user_id
    assert msg.role == "user"
    assert msg.content == "Hello Sage!"
    assert msg.metadata_ is None
    assert msg.whatsapp_message_id is None
    mock_session.commit.assert_awaited_once()


async def test_store_message_with_metadata(service, mock_session, user_id):
    metadata = {"source": "whatsapp", "intent": "greeting"}
    await service.store_message(user_id, "assistant", "Hi there!", metadata=metadata)

    msg = mock_session.add.call_args[0][0]
    assert msg.metadata_ == metadata
    assert msg.role == "assistant"


async def test_store_message_with_whatsapp_id(service, mock_session, user_id):
    await service.store_message(
        user_id, "user", "What should I plant?",
        whatsapp_message_id="wamid.abc123"
    )

    msg = mock_session.add.call_args[0][0]
    assert msg.whatsapp_message_id == "wamid.abc123"


async def test_store_message_returns_message(service, mock_session, user_id):
    result = await service.store_message(user_id, "user", "Test")

    assert isinstance(result, ConversationMessage)
    assert result.content == "Test"


# --- load_conversation_history ---


async def test_load_history_returns_formatted_messages(service, mock_session, user_id):
    msg1 = MagicMock(spec=ConversationMessage)
    msg1.role = "user"
    msg1.content = "Hello"
    msg1.created_at = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)

    msg2 = MagicMock(spec=ConversationMessage)
    msg2.role = "assistant"
    msg2.content = "Hi there! How can I help?"
    msg2.created_at = datetime(2026, 3, 1, 10, 1, tzinfo=timezone.utc)

    mock_result = MagicMock()
    # Query orders by created_at DESC, so newest first
    mock_result.scalars.return_value.all.return_value = [msg2, msg1]
    mock_session.execute = AsyncMock(return_value=mock_result)

    history = await service.load_conversation_history(user_id)

    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Hello"}
    assert history[1] == {"role": "assistant", "content": "Hi there! How can I help?"}


async def test_load_history_respects_limit(service, mock_session, user_id):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    await service.load_conversation_history(user_id, limit=5)

    # Verify the query was called - we check that execute was called
    mock_session.execute.assert_awaited_once()


async def test_load_history_default_limit_20(service, mock_session, user_id):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    await service.load_conversation_history(user_id)

    mock_session.execute.assert_awaited_once()


async def test_load_history_empty_returns_empty_list(service, mock_session, user_id):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    history = await service.load_conversation_history(user_id)
    assert history == []


# --- load_user_context ---


async def test_load_user_context_full_profile(service, mock_session, user_id):
    user = MagicMock(spec=User)
    user.display_name = "Nick"
    user.experience_level = "intermediate"
    user.uk_region = "South West"
    user.postcode_outward = "BS3"
    user.soil_type = "clay"

    garden = MagicMock(spec=Garden)
    garden.garden_type = "back_garden"

    plant1 = MagicMock(spec=Plant)
    plant1.variety = "Cherry Tomato"
    plant1.growth_stage = "seedling"
    plant1.health_status = "healthy"

    plant2 = MagicMock(spec=Plant)
    plant2.variety = "Basil"
    plant2.growth_stage = "established"
    plant2.health_status = "healthy"

    context_event = MagicMock(spec=ContextEvent)
    context_event.event_type = "planting_advice"
    context_event.summary = "Advised sowing tomatoes indoors"
    context_event.created_at = datetime(2026, 3, 10, tzinfo=timezone.utc)

    # Mock user query
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user

    # Mock garden query
    mock_garden_result = MagicMock()
    mock_garden_result.scalar_one_or_none.return_value = garden

    # Mock plants query
    mock_plants_result = MagicMock()
    mock_plants_result.scalars.return_value.all.return_value = [plant1, plant2]

    # Mock context events query
    mock_events_result = MagicMock()
    mock_events_result.scalars.return_value.all.return_value = [context_event]

    mock_session.execute = AsyncMock(side_effect=[
        mock_user_result,
        mock_garden_result,
        mock_plants_result,
        mock_events_result,
    ])

    context = await service.load_user_context(user_id)

    assert context["display_name"] == "Nick"
    assert context["experience_level"] == "intermediate"
    assert context["region"] == "South West"
    assert context["postcode"] == "BS3"
    assert context["soil_type"] == "clay"
    assert context["garden_type"] == "back_garden"
    assert len(context["plants_summary"]) == 2
    assert context["plants_summary"][0]["variety"] == "Cherry Tomato"
    assert context["plants_summary"][0]["growth_stage"] == "seedling"
    assert context["plants_summary"][0]["health_status"] == "healthy"
    assert len(context["recent_context"]) == 1
    assert context["recent_context"][0]["event_type"] == "planting_advice"


async def test_load_user_context_no_user_returns_empty(service, mock_session, user_id):
    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_user_result)

    context = await service.load_user_context(user_id)
    assert context == {}


async def test_load_user_context_no_garden(service, mock_session, user_id):
    user = MagicMock(spec=User)
    user.display_name = "Jo"
    user.experience_level = "beginner"
    user.uk_region = "North West"
    user.postcode_outward = "M1"
    user.soil_type = "loam"

    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user

    mock_garden_result = MagicMock()
    mock_garden_result.scalar_one_or_none.return_value = None

    mock_plants_result = MagicMock()
    mock_plants_result.scalars.return_value.all.return_value = []

    mock_events_result = MagicMock()
    mock_events_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(side_effect=[
        mock_user_result,
        mock_garden_result,
        mock_plants_result,
        mock_events_result,
    ])

    context = await service.load_user_context(user_id)

    assert context["display_name"] == "Jo"
    assert context["garden_type"] is None
    assert context["plants_summary"] == []


async def test_load_user_context_no_plants(service, mock_session, user_id):
    user = MagicMock(spec=User)
    user.display_name = "Sam"
    user.experience_level = "beginner"
    user.uk_region = "South East"
    user.postcode_outward = "SE1"
    user.soil_type = "sandy"

    garden = MagicMock(spec=Garden)
    garden.garden_type = "allotment"

    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = user

    mock_garden_result = MagicMock()
    mock_garden_result.scalar_one_or_none.return_value = garden

    mock_plants_result = MagicMock()
    mock_plants_result.scalars.return_value.all.return_value = []

    mock_events_result = MagicMock()
    mock_events_result.scalars.return_value.all.return_value = []

    mock_session.execute = AsyncMock(side_effect=[
        mock_user_result,
        mock_garden_result,
        mock_plants_result,
        mock_events_result,
    ])

    context = await service.load_user_context(user_id)

    assert context["garden_type"] == "allotment"
    assert context["plants_summary"] == []
    assert context["recent_context"] == []
