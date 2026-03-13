import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.orchestrator import SageOrchestrator


# ---------------------------------------------------------------------------
# Helpers to build mock Claude API responses
# ---------------------------------------------------------------------------

def _make_text_response(text: str):
    block = MagicMock()
    block.type = "text"
    block.text = text
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "end_turn"
    return response


def _make_tool_use_response(tool_name: str, tool_id: str, tool_input: dict):
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.id = tool_id
    block.input = tool_input
    response = MagicMock()
    response.content = [block]
    response.stop_reason = "tool_use"
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_simple_chat():
    """Sage returns a text response without calling any tools."""
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        return_value=_make_text_response(
            "Your tomatoes should go in after the last frost!"
        )
    )
    orchestrator = SageOrchestrator(client=mock_client)
    result = await orchestrator.chat(
        user_message="When should I plant tomatoes?",
        user_context={"region": "South West", "experience_level": "beginner"},
        conversation_history=[],
    )
    assert "tomatoes" in result.lower()
    assert mock_client.messages.create.call_count == 1


@pytest.mark.asyncio
async def test_tool_use_loop():
    """Orchestrator executes a tool call and loops back for the final answer."""
    mock_client = MagicMock()
    # First call: Claude wants to use the weather tool
    # Second call: Claude gives the final text answer
    mock_client.messages.create = AsyncMock(
        side_effect=[
            _make_tool_use_response("get_weather_forecast", "tool_123", {}),
            _make_text_response("Based on the forecast, no watering needed today."),
        ]
    )

    async def mock_weather_handler(input_data):
        return {"forecast": "rain expected", "temp_max": 15}

    orchestrator = SageOrchestrator(
        client=mock_client,
        tool_handlers={"get_weather_forecast": mock_weather_handler},
    )
    result = await orchestrator.chat(
        user_message="Should I water today?",
        user_context={"region": "South West", "latitude": 51.4, "longitude": -2.6},
        conversation_history=[],
    )
    assert "watering" in result.lower() or "water" in result.lower()
    assert mock_client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_unknown_tool_returns_error():
    """When Claude calls a tool with no registered handler, an error dict is returned."""
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[
            _make_tool_use_response("nonexistent_tool", "tool_456", {}),
            _make_text_response("I had trouble with that, but here's what I know..."),
        ]
    )
    orchestrator = SageOrchestrator(client=mock_client)
    result = await orchestrator.chat(
        user_message="Test",
        user_context={},
        conversation_history=[],
    )
    assert len(result) > 0

    # Verify the tool result sent back contained the error
    second_call_args = mock_client.messages.create.call_args_list[1]
    messages = second_call_args.kwargs.get("messages") or second_call_args[1].get("messages")
    tool_result_msg = messages[-1]  # last message is the tool result
    assert "error" in str(tool_result_msg).lower()


@pytest.mark.asyncio
async def test_system_prompt_includes_context():
    """System prompt is populated with user context values."""
    orchestrator = SageOrchestrator(client=MagicMock())
    prompt = orchestrator._build_system_prompt(
        {
            "display_name": "Sophie",
            "region": "South West",
            "soil_type": "clay",
            "experience_level": "beginner",
        }
    )
    assert "Sophie" in prompt
    assert "South West" in prompt
    assert "clay" in prompt
    assert "beginner" in prompt


@pytest.mark.asyncio
async def test_system_prompt_defaults():
    """System prompt uses sensible defaults when context is sparse."""
    orchestrator = SageOrchestrator(client=MagicMock())
    prompt = orchestrator._build_system_prompt({})
    assert "there" in prompt  # default user_name
    assert "beginner" in prompt  # default experience_level
    assert "the UK" in prompt  # default region
    assert "unknown" in prompt  # default soil_type


@pytest.mark.asyncio
async def test_multiple_sequential_tool_calls():
    """Orchestrator handles two rounds of tool calls before the final answer."""
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[
            _make_tool_use_response("check_frost_risk", "tool_a", {}),
            _make_tool_use_response("get_weather_forecast", "tool_b", {}),
            _make_text_response("All clear — no frost risk and mild weather ahead."),
        ]
    )

    calls_received = []

    async def mock_frost_handler(input_data):
        calls_received.append("frost")
        return {"frost_risk": False, "min_temperature": 5.0}

    async def mock_weather_handler(input_data):
        calls_received.append("weather")
        return {"forecast": "mild", "temp_max": 16}

    orchestrator = SageOrchestrator(
        client=mock_client,
        tool_handlers={
            "check_frost_risk": mock_frost_handler,
            "get_weather_forecast": mock_weather_handler,
        },
    )
    result = await orchestrator.chat(
        user_message="Is it safe to put my courgettes out?",
        user_context={"region": "East Midlands"},
        conversation_history=[],
    )
    assert "frost" in result.lower() or "clear" in result.lower()
    assert mock_client.messages.create.call_count == 3
    assert calls_received == ["frost", "weather"]
