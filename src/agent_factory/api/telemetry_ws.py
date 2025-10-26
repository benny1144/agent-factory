from __future__ import annotations

import asyncio
import json
import os
from fastapi import APIRouter, WebSocket
from agent_factory.api.auth import require_bearer_ws

router = APIRouter(prefix="/api/ws", tags=["telemetry"]) 


@router.websocket("/telemetry")
async def telemetry_stream(ws: WebSocket) -> None:
    """Stream simple governance heartbeat events.

    Behavior:
    - Validates optional Bearer token if OPERATOR_TOKEN is set.
    - Accepts the websocket connection.
    - Immediately sends a welcome heartbeat for quick client/tests responsiveness.
    - Then emits a heartbeat every WS_INTERVAL_SEC seconds (default: 5).
    """
    # Optional bearer check prior to accepting connection
    try:
        await require_bearer_ws(ws)
    except Exception:
        return
    await ws.accept()
    try:
        interval = float(os.getenv("WS_INTERVAL_SEC", "5"))
        # Send immediate welcome event for tests/UX responsiveness
        await ws.send_text(json.dumps({"type": "audit", "message": "[AUDIT] governance heartbeat (welcome)"}))
        while True:
            event = {"type": "audit", "message": "[AUDIT] governance heartbeat"}
            await ws.send_text(json.dumps(event))
            await asyncio.sleep(max(0.01, interval))
    except Exception:
        try:
            await ws.close()
        except Exception:
            pass
