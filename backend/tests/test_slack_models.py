"""Tests for Slack-related model changes."""
import uuid
from app.models.conversation import ConversationMessage
from app.models.user import User


def test_conversation_message_has_channel_field():
    msg = ConversationMessage(user_id=uuid.uuid4(), role="user", content="hello")
    assert msg.channel == "cli"


def test_conversation_message_channel_can_be_set():
    msg = ConversationMessage(user_id=uuid.uuid4(), role="user", content="hello", channel="slack")
    assert msg.channel == "slack"


def test_user_has_slack_user_id_field():
    user = User(whatsapp_phone="00000000000")
    assert user.slack_user_id is None


def test_user_slack_user_id_can_be_set():
    user = User(whatsapp_phone="00000000000", slack_user_id="U1234567890")
    assert user.slack_user_id == "U1234567890"
