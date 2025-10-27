from __future__ import annotations

import asyncio
import json
import os
from typing import Set
from fastapi import APIRouter, WebSocket
from agent_factory.api.auth import require_bearer_ws

router = APIRouter(prefix="/api/ws", tags=["telemetry"]) 

# Track connected websockets for broadcast
_active_clients: Set[WebSocket] = set()


def ws_broadcast(message: dict) -> None:
    """Broadcast a JSON-serializable message to all active websocket clients.
    Best-effort: failures on individual sockets are ignored.
    """
    text = json.dumps(message)
    stale: list[WebSocket] = []
    for client in list(_active_clients):
        try:
            # schedule send without await (fire-and-forget); will be awaited by loop callbacks
            asyncio.create_task(client.send_text(text))
        except Exception:
            stale.append(client)
    for s in stale:
        try:
            _active_clients.discard(s)
        except Exception:
            pass


@router.websocket("/telemetry")
async def telemetry_stream(ws: WebSocket) -> None:
    """Stream simple governance heartbeat events and enable broadcast to clients.

    Behavior:
    - Validates optional Bearer token if OPERATOR_TOKEN is set.
    - Accepts the websocket connection and registers it in an in-memory set.
    - Immediately sends a welcome heartbeat for quick client/tests responsiveness.
    - Then emits a heartbeat every WS_INTERVAL_SEC seconds (default: 5).
    """
    # Optional bearer check prior to accepting connection
    try:
        await require_bearer_ws(ws)
    except Exception:
        return
    await ws.accept()
    _active_clients.add(ws)
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
    finally:
        try:
            _active_clients.discard(ws)
        except Exception:
            pass


def emit_federation_event(event_type: str, payload: dict) -> None:
    """Helper to emit a federation event to all connected clients.
    Category is fixed to 'federation'.
    """
    ws_broadcast({"category": "federation", "event": event_type, "data": payload})
