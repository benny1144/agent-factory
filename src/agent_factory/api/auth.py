from __future__ import annotations

import os
from typing import Optional
from fastapi import Request, WebSocket


def _get_bearer_from_header(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    parts = value.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def is_authorized_bearer(token: Optional[str]) -> bool:
    required = os.getenv("OPERATOR_TOKEN")
    if not required:
        # If no token configured, allow (development mode)
        return True
    return token == required


async def require_bearer(request: Request) -> None:
    """Raise 401 if OPERATOR_TOKEN is set and Authorization does not match.

    Usage:
      await require_bearer(request)
    """
    token = _get_bearer_from_header(request.headers.get("authorization")) or request.query_params.get("token")
    if not is_authorized_bearer(token):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="unauthorized")


async def require_bearer_ws(ws: WebSocket) -> None:
    token = _get_bearer_from_header(ws.headers.get("authorization"))
    if not is_authorized_bearer(token):
        await ws.close(code=4401)
        raise RuntimeError("unauthorized")
