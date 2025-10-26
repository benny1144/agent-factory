from __future__ import annotations

from fastapi import APIRouter, Request
from agent_factory.api.auth import require_bearer

router = APIRouter(prefix="/api/gpt", tags=["gpt"])


@router.post("/query")
async def gpt_query(request: Request) -> dict:
    """Stub GPT-5 assistant query endpoint.

    Accepts JSON body with either {"query": "..."} or {"question": "..."} and
    returns a deterministic stub response without calling external services.
    """
    # Optional bearer auth gate (development-friendly): requires OPERATOR_TOKEN if set
    await require_bearer(request)
    data = await request.json()
    query = str(data.get("query") or data.get("question") or "").strip()
    return {"response": f"[GPT-5] received query: {query}"}
