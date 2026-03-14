"""Integration test — full WhatsApp message round-trip.

Simulates the complete flow from first contact through onboarding to post-onboarding
chat, calling process_inbound_message() directly (no HTTP layer). External services
(Claude API, postcodes.io, BGS soil API, Redis) are mocked, but the real routing
logic in process_inbound_message and the real OnboardingService state machine are
exercised.
"""

import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.user import User
from app.models.conversation import ConversationMessage
from app.models.garden import Garden
from app.models.plant import Plant
from app.services.onboarding import OnboardingService
from app.services.postcode import PostcodeService
from app.services.soil import SoilService


# ---------------------------------------------------------------------------
# In-memory mock session
# ---------------------------------------------------------------------------

class FakeAsyncSession:
    """Minimal async session that tracks objects in memory.

    Maintains a list of added objects and a persistent User record so that
    successive calls to process_inbound_message (which each open a new session
    via the context manager) share the same state.
    """

    def __init__(self, state: dict):
        # state is shared across session instances to survive context-manager cycles
        self._state = state  # {"user": User | None, "objects": [...]}

    # -- context manager --
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    # -- ORM methods --
    def add(self, obj):
        self._state["objects"].append(obj)
        if isinstance(obj, User):
            self._state["user"] = obj
        if isinstance(obj, Garden):
            self._state["garden"] = obj

    async def flush(self):
        # Assign an id to any object that needs one
        for obj in self._state["objects"]:
            if hasattr(obj, "id") and obj.id is None:
                obj.id = uuid.uuid4()

    async def commit(self):
        await self.flush()

    async def execute(self, stmt):
        """Route queries based on the compiled SQL to return appropriate results."""
        compiled = str(stmt)

        # User lookup by phone
        if "users" in compiled and "whatsapp_phone" in compiled:
            result = MagicMock()
            result.scalar_one_or_none.return_value = self._state.get("user")
            return result

        # PlantSpec lookup (for onboarding plants step)
        if "plant_specs" in compiled:
            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            return result

        # Garden lookup (primary garden for user)
        if "gardens" in compiled:
            result = MagicMock()
            garden = self._state.get("garden")
            # scalar_one_or_none used by onboarding _handle_plants
            result.scalar_one_or_none.return_value = garden
            # scalars().first() used by _handle_chat
            result.scalars.return_value.first.return_value = garden
            return result

        # Plant lookup (active plants)
        if "plants" in compiled and "plant_specs" not in compiled:
            result = MagicMock()
            mock_plant = MagicMock()
            mock_plant.variety = "tomatoes"
            result.scalars.return_value.all.return_value = [mock_plant]
            return result

        # Conversation history lookup
        if "conversation_messages" in compiled:
            result = MagicMock()
            result.scalars.return_value.all.return_value = []
            return result

        # Fallback
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        result.scalars.return_value.all.return_value = []
        result.scalars.return_value.first.return_value = None
        return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PHONE = "447700900111"


@pytest.fixture
def shared_state():
    """Shared mutable dict that persists User state across session instances."""
    return {"user": None, "garden": None, "objects": []}


@pytest.fixture
def mock_session_factory(shared_state):
    """Returns a callable that produces FakeAsyncSession context managers."""
    def factory():
        return FakeAsyncSession(shared_state)
    return factory


@pytest.fixture
def mock_postcode():
    svc = MagicMock(spec=PostcodeService)
    svc.lookup = AsyncMock(return_value={
        "postcode": "BS3 1AB",
        "outward_code": "BS3",
        "latitude": 51.438,
        "longitude": -2.604,
        "region": "South West",
        "admin_district": "Bristol",
    })
    return svc


@pytest.fixture
def mock_soil():
    svc = MagicMock(spec=SoilService)
    svc.get_soil_type = AsyncMock(return_value={"soil_type": "clay", "source": "bgs"})
    return svc


@pytest.fixture
def mock_queue():
    queue = AsyncMock()
    queue.enqueue_outbound = AsyncMock()
    # Collect all enqueued messages for assertions
    queue.sent_messages = []

    async def _capture(msg):
        queue.sent_messages.append(msg)

    queue.enqueue_outbound.side_effect = _capture
    return queue


@pytest.fixture
def mock_orchestrator():
    orch = AsyncMock()
    orch.chat = AsyncMock(return_value="March is a great time to start your tomatoes indoors!")
    return orch


@pytest.fixture
def real_onboarding(mock_postcode, mock_soil):
    """Real OnboardingService with mocked external dependencies."""
    return OnboardingService(postcode_service=mock_postcode, soil_service=mock_soil)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def send_message(text, mock_session_factory, mock_queue, onboarding, orchestrator, msg_id=None):
    """Call process_inbound_message with all dependencies patched."""
    from app.tasks.process_message import process_inbound_message

    message_data = {
        "from": PHONE,
        "text": text,
        "message_id": msg_id or f"wamid_{uuid.uuid4().hex[:8]}",
    }

    with patch("app.tasks.process_message.async_session", mock_session_factory), \
         patch("app.tasks.process_message.get_onboarding_service", return_value=onboarding), \
         patch("app.tasks.process_message.get_orchestrator", return_value=orchestrator), \
         patch("app.tasks.process_message.get_message_queue", return_value=mock_queue):
        await process_inbound_message(message_data)


# ---------------------------------------------------------------------------
# The integration test
# ---------------------------------------------------------------------------

class TestFullMessageRoundTrip:
    """End-to-end integration test simulating a user journey from first
    contact through onboarding completion to a post-onboarding garden question."""

    async def test_full_onboarding_then_chat(
        self,
        shared_state,
        mock_session_factory,
        mock_queue,
        real_onboarding,
        mock_orchestrator,
        mock_postcode,
        mock_soil,
    ):
        # -- Step 1: New user says "Hello" -----------------------------------
        await send_message(
            "Hello",
            mock_session_factory,
            mock_queue,
            real_onboarding,
            mock_orchestrator,
        )

        # User record should have been created
        user = shared_state["user"]
        assert user is not None, "User should be created on first message"
        assert user.whatsapp_phone == PHONE
        assert user.onboarding_step == "awaiting_first_plant"
        assert not user.onboarding_complete  # None or False — both mean not onboarded

        # Welcome message should be enqueued (asks what to grow)
        assert len(mock_queue.sent_messages) == 1
        welcome = mock_queue.sent_messages[0]
        assert welcome["to"] == PHONE
        assert "grow" in welcome["text"].lower()

        # -- Step 2: User says "tomatoes" ------------------------------------
        await send_message(
            "tomatoes",
            mock_session_factory,
            mock_queue,
            real_onboarding,
            mock_orchestrator,
        )

        assert user.onboarding_step == "awaiting_postcode"

        # Response should ask for postcode
        assert len(mock_queue.sent_messages) == 2
        plant_resp = mock_queue.sent_messages[1]
        assert "postcode" in plant_resp["text"].lower()

        # -- Step 3: User sends postcode "BS3 1AB" ---------------------------
        await send_message(
            "BS3 1AB",
            mock_session_factory,
            mock_queue,
            real_onboarding,
            mock_orchestrator,
        )

        # Postcode and soil services should have been called
        mock_postcode.lookup.assert_awaited_once_with("BS3 1AB")
        mock_soil.get_soil_type.assert_awaited_once_with(
            51.438, -2.604, admin_district="Bristol", region="South West"
        )

        # User record should be updated
        assert user.postcode_outward == "BS3"
        assert user.uk_region == "Bristol"
        assert user.soil_type == "clay"
        assert user.onboarding_complete is True
        assert user.onboarding_step == "complete"

        # A Garden record should have been created
        garden = shared_state.get("garden")
        assert garden is not None, "Garden record should be created"
        assert garden.garden_type == "back_garden"
        assert garden.is_primary is True

        # Response should mention location
        assert len(mock_queue.sent_messages) == 3
        postcode_resp = mock_queue.sent_messages[2]
        assert "bristol" in postcode_resp["text"].lower()

        # -- Step 4: Onboarded user asks a garden question -------------------
        await send_message(
            "When should I plant my tomatoes?",
            mock_session_factory,
            mock_queue,
            real_onboarding,
            mock_orchestrator,
        )

        # Orchestrator should have been called (not onboarding)
        mock_orchestrator.chat.assert_awaited_once()
        call_args = mock_orchestrator.chat.call_args

        # First arg: the user's message
        assert call_args[0][0] == "When should I plant my tomatoes?"

        # Second arg: user context dict with correct values
        user_context = call_args[0][1]
        assert user_context["experience_level"] == "beginner"
        assert user_context["region"] == "Bristol"
        assert user_context["soil_type"] == "clay"
        assert user_context["postcode"] == "BS3"
        assert user_context["garden_type"] == "back_garden"

        # Third arg: conversation history (list of dicts)
        history = call_args[0][2]
        assert isinstance(history, list)

        # Response should be the orchestrator's canned reply
        assert len(mock_queue.sent_messages) == 4
        chat_resp = mock_queue.sent_messages[3]
        assert chat_resp["to"] == PHONE
        assert chat_resp["text"] == "March is a great time to start your tomatoes indoors!"
        assert chat_resp["type"] == "text"

    async def test_new_user_not_routed_to_orchestrator(
        self,
        shared_state,
        mock_session_factory,
        mock_queue,
        real_onboarding,
        mock_orchestrator,
    ):
        """A brand new user should never reach the orchestrator."""
        await send_message(
            "Hello",
            mock_session_factory,
            mock_queue,
            real_onboarding,
            mock_orchestrator,
        )

        mock_orchestrator.chat.assert_not_awaited()
        assert len(mock_queue.sent_messages) == 1
        assert "grow" in mock_queue.sent_messages[0]["text"].lower()

    async def test_mid_onboarding_user_not_routed_to_orchestrator(
        self,
        shared_state,
        mock_session_factory,
        mock_queue,
        real_onboarding,
        mock_orchestrator,
    ):
        """A user partway through onboarding should stay in onboarding flow."""
        # First message creates user
        await send_message("Hi", mock_session_factory, mock_queue, real_onboarding, mock_orchestrator)
        # Second message is the first plant step (moves to awaiting_postcode)
        await send_message("tomatoes", mock_session_factory, mock_queue, real_onboarding, mock_orchestrator)

        # Orchestrator should still not have been called
        mock_orchestrator.chat.assert_not_awaited()
        assert not shared_state["user"].onboarding_complete

    async def test_conversation_messages_stored_each_step(
        self,
        shared_state,
        mock_session_factory,
        mock_queue,
        real_onboarding,
        mock_orchestrator,
    ):
        """Every message exchange should produce a user + assistant ConversationMessage."""
        await send_message("Hi", mock_session_factory, mock_queue, real_onboarding, mock_orchestrator)
        await send_message("tomatoes", mock_session_factory, mock_queue, real_onboarding, mock_orchestrator)

        # Each call adds User (first call only) + ConversationMessage(user) + ConversationMessage(assistant)
        # Filter to ConversationMessages only.
        conv_messages = [
            obj for obj in shared_state["objects"]
            if isinstance(obj, ConversationMessage)
        ]

        # 2 calls x 2 messages each = 4 ConversationMessages
        assert len(conv_messages) == 4

        # First pair: user said "Hi", assistant sent welcome (asks what to grow)
        assert conv_messages[0].role == "user"
        assert conv_messages[0].content == "Hi"
        assert conv_messages[1].role == "assistant"
        assert "grow" in conv_messages[1].content.lower()

        # Second pair: user said "tomatoes", assistant asked for postcode
        assert conv_messages[2].role == "user"
        assert conv_messages[2].content == "tomatoes"
        assert conv_messages[3].role == "assistant"
        assert "postcode" in conv_messages[3].content.lower()

    async def test_outbound_messages_have_correct_shape(
        self,
        shared_state,
        mock_session_factory,
        mock_queue,
        real_onboarding,
        mock_orchestrator,
    ):
        """Every outbound message should have to/text/type keys."""
        await send_message("Hi", mock_session_factory, mock_queue, real_onboarding, mock_orchestrator)

        msg = mock_queue.sent_messages[0]
        assert msg["to"] == PHONE
        assert msg["type"] == "text"
        assert isinstance(msg["text"], str)
        assert len(msg["text"]) > 0
