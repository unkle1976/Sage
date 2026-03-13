import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import User
from app.models.conversation import ConversationMessage


# --- Fixtures ---

@pytest.fixture
def new_user_phone():
    return "447700900001"


@pytest.fixture
def existing_user():
    user = User(
        whatsapp_phone="447700900002",
        onboarding_complete=True,
        onboarding_step="complete",
        display_name="Jo",
        experience_level="beginner",
        uk_region="South West",
        postcode_outward="BS3",
        soil_type="clay",
    )
    user.id = uuid.uuid4()
    return user


@pytest.fixture
def onboarding_user():
    user = User(
        whatsapp_phone="447700900003",
        onboarding_complete=False,
        onboarding_step="awaiting_garden_type",
    )
    user.id = uuid.uuid4()
    return user


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def mock_queue():
    queue = AsyncMock()
    queue.enqueue_outbound = AsyncMock()
    return queue


@pytest.fixture
def mock_onboarding():
    svc = AsyncMock()
    svc.get_welcome_message = AsyncMock(return_value="Welcome! What's your postcode?")
    svc.process_step = AsyncMock(return_value="Great, what type of garden?")
    return svc


@pytest.fixture
def mock_orchestrator():
    orch = AsyncMock()
    orch.chat = AsyncMock(return_value="Your tomatoes should be fine in clay soil.")
    return orch


# --- Tests ---

class TestProcessInboundMessage:
    """Tests for the process_inbound_message pipeline."""

    async def test_brand_new_user_gets_welcome(
        self, mock_session, mock_queue, mock_onboarding
    ):
        """A message from an unknown phone creates a user and sends the welcome."""
        from app.tasks.process_message import process_inbound_message

        phone = "447700900099"

        # No existing user found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        message_data = {"from": phone, "text": "Hi", "message_id": "wamid_new"}

        with patch("app.tasks.process_message.async_session") as mock_session_factory, \
             patch("app.tasks.process_message.get_onboarding_service", return_value=mock_onboarding), \
             patch("app.tasks.process_message.get_message_queue", return_value=mock_queue):
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_inbound_message(message_data)

        # Should have created a new user via session.add
        mock_session.add.assert_called()
        added_user = mock_session.add.call_args_list[0][0][0]
        assert isinstance(added_user, User)
        assert added_user.whatsapp_phone == phone

        # Should get welcome message, NOT process_step
        mock_onboarding.get_welcome_message.assert_awaited_once()
        mock_onboarding.process_step.assert_not_awaited()

        # Should enqueue the welcome response
        mock_queue.enqueue_outbound.assert_awaited_once()
        outbound = mock_queue.enqueue_outbound.call_args[0][0]
        assert outbound["to"] == phone
        assert outbound["text"] == "Welcome! What's your postcode?"
        assert outbound["type"] == "text"

    async def test_onboarding_user_routes_to_onboarding(
        self, onboarding_user, mock_session, mock_queue, mock_onboarding
    ):
        """A user mid-onboarding has their message routed to OnboardingService."""
        from app.tasks.process_message import process_inbound_message

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = onboarding_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        message_data = {
            "from": onboarding_user.whatsapp_phone,
            "text": "1",
            "message_id": "wamid_onb",
        }

        with patch("app.tasks.process_message.async_session") as mock_session_factory, \
             patch("app.tasks.process_message.get_onboarding_service", return_value=mock_onboarding), \
             patch("app.tasks.process_message.get_message_queue", return_value=mock_queue):
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_inbound_message(message_data)

        mock_onboarding.process_step.assert_awaited_once_with(
            onboarding_user, "1", mock_session
        )
        mock_queue.enqueue_outbound.assert_awaited_once()
        outbound = mock_queue.enqueue_outbound.call_args[0][0]
        assert outbound["text"] == "Great, what type of garden?"

    async def test_onboarded_user_routes_to_orchestrator(
        self, existing_user, mock_session, mock_queue, mock_orchestrator
    ):
        """An onboarded user's message goes to the SageOrchestrator."""
        from app.tasks.process_message import process_inbound_message

        # User lookup returns existing_user
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = existing_user

        # Garden query
        mock_garden = MagicMock()
        mock_garden.garden_type = "back_garden"
        mock_garden_result = MagicMock()
        mock_garden_result.scalars.return_value.first.return_value = mock_garden

        # Plants query
        mock_plants_result = MagicMock()
        mock_plant = MagicMock()
        mock_plant.variety = "Tomato"
        mock_plants_result.scalars.return_value.all.return_value = [mock_plant]

        # Conversation history query
        mock_conv_result = MagicMock()
        mock_conv_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[mock_user_result, mock_garden_result, mock_plants_result, mock_conv_result]
        )

        message_data = {
            "from": existing_user.whatsapp_phone,
            "text": "How are my tomatoes?",
            "message_id": "wamid_chat",
        }

        with patch("app.tasks.process_message.async_session") as mock_session_factory, \
             patch("app.tasks.process_message.get_orchestrator", return_value=mock_orchestrator), \
             patch("app.tasks.process_message.get_message_queue", return_value=mock_queue):
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_inbound_message(message_data)

        # Orchestrator should be called with user message, context, and history
        mock_orchestrator.chat.assert_awaited_once()
        call_args = mock_orchestrator.chat.call_args
        assert call_args[0][0] == "How are my tomatoes?"
        user_context = call_args[0][1]
        assert user_context["display_name"] == "Jo"
        assert user_context["soil_type"] == "clay"
        assert user_context["garden_type"] == "back_garden"
        assert "Tomato" in user_context["plants_summary"]

        # Should enqueue the orchestrator response
        mock_queue.enqueue_outbound.assert_awaited_once()
        outbound = mock_queue.enqueue_outbound.call_args[0][0]
        assert outbound["text"] == "Your tomatoes should be fine in clay soil."

    async def test_stores_user_and_assistant_messages(
        self, existing_user, mock_session, mock_queue, mock_orchestrator
    ):
        """Both the user message and assistant response are saved as ConversationMessage."""
        from app.tasks.process_message import process_inbound_message

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = existing_user

        mock_garden = MagicMock()
        mock_garden.garden_type = "back_garden"
        mock_garden_result = MagicMock()
        mock_garden_result.scalars.return_value.first.return_value = mock_garden

        mock_plants_result = MagicMock()
        mock_plants_result.scalars.return_value.all.return_value = []

        mock_conv_result = MagicMock()
        mock_conv_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(
            side_effect=[mock_user_result, mock_garden_result, mock_plants_result, mock_conv_result]
        )

        message_data = {
            "from": existing_user.whatsapp_phone,
            "text": "Hello Sage",
            "message_id": "wamid_hist",
        }

        with patch("app.tasks.process_message.async_session") as mock_session_factory, \
             patch("app.tasks.process_message.get_orchestrator", return_value=mock_orchestrator), \
             patch("app.tasks.process_message.get_message_queue", return_value=mock_queue):
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_inbound_message(message_data)

        # Should have added ConversationMessage records (user + assistant)
        added_objects = [call[0][0] for call in mock_session.add.call_args_list]
        conv_messages = [obj for obj in added_objects if isinstance(obj, ConversationMessage)]
        assert len(conv_messages) == 2

        user_msg = conv_messages[0]
        assert user_msg.role == "user"
        assert user_msg.content == "Hello Sage"
        assert user_msg.whatsapp_message_id == "wamid_hist"

        assistant_msg = conv_messages[1]
        assert assistant_msg.role == "assistant"
        assert assistant_msg.content == "Your tomatoes should be fine in clay soil."

    async def test_conversation_history_passed_to_orchestrator(
        self, existing_user, mock_session, mock_queue, mock_orchestrator
    ):
        """Recent conversation messages are loaded and passed to the orchestrator."""
        from app.tasks.process_message import process_inbound_message

        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = existing_user

        mock_garden = MagicMock()
        mock_garden.garden_type = "back_garden"
        mock_garden_result = MagicMock()
        mock_garden_result.scalars.return_value.first.return_value = mock_garden

        mock_plants_result = MagicMock()
        mock_plants_result.scalars.return_value.all.return_value = []

        # Existing conversation history
        prev_user_msg = MagicMock()
        prev_user_msg.role = "user"
        prev_user_msg.content = "What should I plant?"
        prev_assistant_msg = MagicMock()
        prev_assistant_msg.role = "assistant"
        prev_assistant_msg.content = "Try some tomatoes!"

        mock_conv_result = MagicMock()
        # Returned in DESC order (most recent first) — implementation reverses to chronological
        mock_conv_result.scalars.return_value.all.return_value = [prev_assistant_msg, prev_user_msg]

        mock_session.execute = AsyncMock(
            side_effect=[mock_user_result, mock_garden_result, mock_plants_result, mock_conv_result]
        )

        message_data = {
            "from": existing_user.whatsapp_phone,
            "text": "Tell me more",
            "message_id": "wamid_ctx",
        }

        with patch("app.tasks.process_message.async_session") as mock_session_factory, \
             patch("app.tasks.process_message.get_orchestrator", return_value=mock_orchestrator), \
             patch("app.tasks.process_message.get_message_queue", return_value=mock_queue):
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_inbound_message(message_data)

        call_args = mock_orchestrator.chat.call_args
        history = call_args[0][2]
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "What should I plant?"}
        assert history[1] == {"role": "assistant", "content": "Try some tomatoes!"}

    async def test_onboarding_messages_also_stored(
        self, onboarding_user, mock_session, mock_queue, mock_onboarding
    ):
        """Onboarding conversation messages are stored too."""
        from app.tasks.process_message import process_inbound_message

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = onboarding_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        message_data = {
            "from": onboarding_user.whatsapp_phone,
            "text": "2",
            "message_id": "wamid_onb2",
        }

        with patch("app.tasks.process_message.async_session") as mock_session_factory, \
             patch("app.tasks.process_message.get_onboarding_service", return_value=mock_onboarding), \
             patch("app.tasks.process_message.get_message_queue", return_value=mock_queue):
            mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_inbound_message(message_data)

        added_objects = [call[0][0] for call in mock_session.add.call_args_list]
        conv_messages = [obj for obj in added_objects if isinstance(obj, ConversationMessage)]
        assert len(conv_messages) == 2
        assert conv_messages[0].role == "user"
        assert conv_messages[0].content == "2"
        assert conv_messages[1].role == "assistant"
