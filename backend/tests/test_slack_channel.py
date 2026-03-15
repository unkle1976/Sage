"""Tests for the Slack channel adapter."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.channels.slack import _find_or_create_slack_user


class TestFindOrCreateSlackUser:
    @pytest.mark.asyncio
    async def test_returns_existing_user(self):
        session = AsyncMock()
        existing_user = MagicMock()
        existing_user.slack_user_id = "U123"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        session.execute.return_value = mock_result

        user, is_new = await _find_or_create_slack_user("U123", session)
        assert user == existing_user
        assert is_new is False

    @pytest.mark.asyncio
    async def test_creates_new_user_when_not_found(self):
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute.return_value = mock_result

        user, is_new = await _find_or_create_slack_user("U999", session)
        assert is_new is True
        assert user.slack_user_id == "U999"
        assert user.whatsapp_phone == "slack-U999"
        assert user.onboarding_step == "awaiting_first_plant"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()
