from __future__ import annotations

import anthropic
from datetime import datetime

from app.agents.system_prompt import SAGE_SYSTEM_PROMPT
from app.agents.tools import TOOLS


class SageOrchestrator:
    """Sage AI gardening companion — Claude API with tool use loop."""

    MODEL = "claude-3-haiku-20240307"

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        tool_handlers: dict | None = None,
    ):
        self._client = client
        self._tool_handlers = tool_handlers or {}

    async def chat(
        self,
        user_message: str,
        user_context: dict,
        conversation_history: list[dict],
    ) -> str:
        """Send a message to Sage and get a response, with tool use loop."""
        system = self._build_system_prompt(user_context)
        messages = conversation_history + [{"role": "user", "content": user_message}]

        # Tool use loop — Claude may request multiple rounds of tools
        while True:
            response = await self._client.messages.create(
                model=self.MODEL,
                max_tokens=1024,
                system=system,
                tools=TOOLS,
                messages=messages,
            )

            # If Claude wants to use tools, execute them and loop back
            if response.stop_reason == "tool_use":
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = await self._execute_tool(block.name, block.input)
                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": str(result),
                            }
                        )

                # Append assistant turn + tool results and continue the loop
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": tool_results})
                continue

            # No more tool calls — extract the final text response
            text_parts = [
                block.text for block in response.content if block.type == "text"
            ]
            return "\n".join(text_parts)

    async def _execute_tool(self, name: str, input_data: dict) -> dict:
        """Dispatch a tool call to the registered handler."""
        handler = self._tool_handlers.get(name)
        if handler:
            return await handler(input_data)
        return {"error": f"Unknown tool: {name}"}

    def _build_system_prompt(self, context: dict) -> str:
        """Interpolate user context into the system prompt."""
        return SAGE_SYSTEM_PROMPT.format(
            user_name=context.get("display_name", "there"),
            experience_level=context.get("experience_level", "beginner"),
            region=context.get("region", "the UK"),
            postcode=context.get("postcode", ""),
            soil_type=context.get("soil_type", "unknown"),
            garden_type=context.get("garden_type", "garden"),
            plants_summary=context.get("plants_summary", "none yet"),
            current_month=datetime.now().strftime("%B %Y"),
        )
