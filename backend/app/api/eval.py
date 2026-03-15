"""Eval dashboard API routes — SSE streaming, status, and run trigger."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse, StreamingResponse

from app.eval.event_log import EVENTS_FILE, EventLog

router = APIRouter(prefix="/api/eval", tags=["eval"])

# Track running eval state
_eval_state: dict = {
    "status": "idle",  # idle | running | completed
    "started_at": None,
    "total": 0,
    "completed": 0,
    "pid": None,
}

# Dashboard HTML path
DASHBOARD_PATH = Path(__file__).resolve().parent.parent / "eval" / "dashboard.html"


@router.get("/status")
async def eval_status():
    """Return current eval run status."""
    return {
        "status": _eval_state["status"],
        "started_at": _eval_state["started_at"],
        "total": _eval_state["total"],
        "completed": _eval_state["completed"],
    }


@router.post("/start")
async def eval_start(
    persona: str | None = Query(None, description="Filter personas by partial slug match"),
    repeat: int = Query(1, description="Run each persona N times"),
    turns: int | None = Query(None, description="Override turn count"),
    no_judge: bool = Query(False, description="Skip judge evaluation"),
):
    """Kick off an eval run in the background."""
    if _eval_state["status"] == "running":
        return {"error": "Eval already running", "status": "running"}

    _eval_state["status"] = "running"
    _eval_state["started_at"] = time.time()
    _eval_state["completed"] = 0

    asyncio.get_event_loop().create_task(
        _run_eval_background(persona, repeat, turns, no_judge)
    )

    return {"status": "started", "persona": persona, "repeat": repeat}


async def _run_eval_background(
    persona_filter: str | None,
    repeat: int,
    turns_override: int | None,
    no_judge: bool,
):
    """Run eval in background, updating state as it goes."""
    try:
        # Import here to avoid circular imports
        from app.eval.personas import PERSONAS
        from app.eval.run import _match_personas, _run_eval, _save_results, RESULTS_DIR

        personas = _match_personas(persona_filter)
        if not personas:
            _eval_state["status"] = "idle"
            return

        total = len(personas) * repeat
        _eval_state["total"] = total

        event_log = EventLog()

        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = RESULTS_DIR / timestamp
        output_dir.mkdir(parents=True, exist_ok=True)

        results = await _run_eval(
            personas, turns_override, repeat, not no_judge, output_dir, event_log
        )

        _save_results(results, timestamp, output_dir)
        _eval_state["status"] = "completed"
        _eval_state["completed"] = total

    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Background eval failed")
        _eval_state["status"] = "idle"


@router.get("/stream")
async def eval_stream():
    """Stream eval events via Server-Sent Events (tails the JSONL file)."""
    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _sse_generator():
    """Tail the events.jsonl file and yield SSE events."""
    last_pos = 0
    idle_count = 0

    # If file doesn't exist yet, wait for it
    while not EVENTS_FILE.exists():
        yield f"data: {json.dumps({'type': 'waiting', 'message': 'No eval run in progress'})}\n\n"
        await asyncio.sleep(2)
        idle_count += 1
        if idle_count > 150:  # 5 minutes
            return

    while True:
        try:
            file_size = EVENTS_FILE.stat().st_size
            if file_size > last_pos:
                with open(EVENTS_FILE, "r") as f:
                    f.seek(last_pos)
                    new_data = f.read()
                    last_pos = f.tell()

                for line in new_data.strip().split("\n"):
                    if line.strip():
                        yield f"data: {line}\n\n"

                        # Check if run completed
                        try:
                            event = json.loads(line)
                            if event.get("type") == "run_completed":
                                yield f"data: {json.dumps({'type': 'stream_end'})}\n\n"
                                return
                        except json.JSONDecodeError:
                            pass

                idle_count = 0
            else:
                idle_count += 1
                # Send keepalive every 10 idle cycles
                if idle_count % 10 == 0:
                    yield ": keepalive\n\n"
                # Stop after 10 minutes of no activity
                if idle_count > 600:
                    return

        except FileNotFoundError:
            pass

        await asyncio.sleep(1)
