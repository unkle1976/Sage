"""Live event logging for eval runs.

Writes JSONL events to a file that can be tailed by the SSE endpoint.
Each event is a single JSON line with a "type" field and a timestamp.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

# Default event log path (overwritten each run)
EVENTS_DIR = Path(__file__).resolve().parent.parent.parent / "eval" / "live"
EVENTS_FILE = EVENTS_DIR / "events.jsonl"


class EventLog:
    """Append-only JSONL event writer for eval runs."""

    def __init__(self, path: Path | None = None):
        self._path = path or EVENTS_FILE
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Overwrite on init (fresh run)
        self._path.write_text("")
        self._api_call_count = 0
        self._start_time = time.time()

    def _write(self, event_type: str, data: dict[str, Any]) -> None:
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "elapsed": round(time.time() - self._start_time, 2),
            **data,
        }
        with open(self._path, "a") as f:
            f.write(json.dumps(event, default=str) + "\n")

    def run_started(
        self, total_conversations: int, personas: list[str], run_judge: bool
    ) -> None:
        self._write("run_started", {
            "total_conversations": total_conversations,
            "personas": personas,
            "run_judge": run_judge,
        })

    def conversation_started(
        self, persona: str, run_number: int, total_runs: int, conversation_index: int
    ) -> None:
        self._write("conversation_started", {
            "persona": persona,
            "run_number": run_number,
            "total_runs": total_runs,
            "conversation_index": conversation_index,
        })

    def turn(
        self, role: str, content: str, turn_number: int, persona: str,
        conversation_index: int
    ) -> None:
        self._write("turn", {
            "role": role,
            "content": content,
            "turn_number": turn_number,
            "persona": persona,
            "conversation_index": conversation_index,
        })

    def api_call(self, call_type: str, persona: str, conversation_index: int) -> None:
        self._api_call_count += 1
        self._write("api_call", {
            "call_type": call_type,
            "persona": persona,
            "conversation_index": conversation_index,
            "api_call_count": self._api_call_count,
        })

    def conversation_completed(
        self,
        persona: str,
        conversation_index: int,
        rule_results: dict,
        judge_scores: dict | None,
        judge_average: float | None,
        rule_passed: bool,
        turns_completed: int,
        errors: list[str],
    ) -> None:
        self._write("conversation_completed", {
            "persona": persona,
            "conversation_index": conversation_index,
            "rule_results": rule_results,
            "judge_scores": judge_scores,
            "judge_average": judge_average,
            "rule_passed": rule_passed,
            "turns_completed": turns_completed,
            "errors": errors,
        })

    def run_completed(
        self,
        total: int,
        passed: int,
        failed: int,
        avg_judge_score: float | None,
    ) -> None:
        self._write("run_completed", {
            "total": total,
            "passed": passed,
            "failed": failed,
            "avg_judge_score": avg_judge_score,
            "total_api_calls": self._api_call_count,
        })
