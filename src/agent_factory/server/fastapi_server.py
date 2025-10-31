from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from fastapi import FastAPI, Request, Depends, HTTPException
from pydantic import BaseModel

# JWT Auth
try:
    from fastapi_jwt_auth import AuthJWT
    from pydantic import BaseModel as PydSettings
except Exception:  # pragma: no cover
    AuthJWT = None  # type: ignore
    PydSettings = None  # type: ignore

from agent_factory.core.file_access import safe_read, governed_write, list_dir
from agent_factory.services.audit.audit_logger import log_event

# Reuse the simple in-browser chat router from the Archivist agent
# (kept decoupled from core server code)
try:
    from factory_agents.archivist_archy.web_client import router as web_router  # type: ignore
except Exception:  # pragma: no cover
    web_router = None  # type: ignore


app = FastAPI(title="Agent Factory — Archy Server")

# JWT settings (optional dependency)
if AuthJWT and PydSettings:
    class Settings(PydSettings):
        authjwt_secret_key: str = os.getenv("ARCHIVIST_API_SECRET", "dev-secret-change-me")
    @AuthJWT.load_config  # type: ignore[attr-defined]
    def get_config():  # pragma: no cover - simple config provider
        return Settings()

if web_router:
    app.include_router(web_router)

# Optionally include modular API routers if present (best-effort)

def _try_include(module_path: str) -> None:
    try:
        mod = __import__(module_path, fromlist=["router"])  # dynamic import
        router = getattr(mod, "router", None)
        if router is not None:
            app.include_router(router)
    except Exception:
        # Silent optional inclusion to avoid hard dependency during local dev
        pass

for _mod in [
    "api.auth.auth_api",
    "api.billing.billing_controller",
    "api.agents.export",
    "api.agents.import",
    "api.marketplace.listings",
    "api.marketplace.listings_controller",
    "api.marketplace.upload",
    "api.marketplace.publish",
    "api.analytics.usage",
    "api.licenses.licenses",
]:
    _try_include(_mod)


@app.get("/health")
def health():
    return {"ok": True, "service": "archy-server"}

# Alias for health (Phase 38.5)
@app.get("/healthcheck")
def healthcheck():
    return {"ok": True, "service": "archy-server"}


# JWT-protected audit status (Phase 38.5)
if AuthJWT:
    @app.get("/audit_status")
    def audit_status(Authorize: AuthJWT = Depends()):  # type: ignore[name-defined]
        try:
            Authorize.jwt_required()  # type: ignore[attr-defined]
        except Exception as e:  # pragma: no cover
            raise HTTPException(status_code=401, detail="Unauthorized")
        return {"ok": True, "status": "ok"}
else:
    @app.get("/audit_status")
    def audit_status_unavailable():  # pragma: no cover
        raise HTTPException(status_code=501, detail="JWT auth not available")


@app.get("/")
def root():
    return "Agent Factory Console Active"


class ReadRequest(BaseModel):
    path: str


@app.post("/read_file")
async def read_file(req: ReadRequest):
    result = safe_read(req.path)
    log_event("file_read_api", {"path": req.path, "status": result.get("status")})
    return result


class ListRequest(BaseModel):
    path: Optional[str] = None


@app.post("/list_dir")
async def list_directory(req: ListRequest):
    result = list_dir(req.path)
    log_event("list_dir_api", {"path": req.path, "status": result.get("status")})
    return result


class WriteRequest(BaseModel):
    path: str
    content: str
    actor: Optional[str] = None


@app.post("/write_file")
async def write_file(req: WriteRequest):
    result = governed_write(req.path, req.content, actor=req.actor)
    log_event("file_write_api", {"path": req.path, "status": result.get("status")})
    return result


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    prompt = str(data.get("message", "")).strip()

    # Detect read intent: "read <path>"
    read_match = re.search(r"\bread\s+([\w\-/\\\.]+)", prompt, re.IGNORECASE)
    if read_match:
        path = read_match.group(1)
        result = safe_read(path)
        log_event("chat_file_read", {"path": path, "status": result.get("status")})
        if isinstance(result, dict) and result.get("status") == "success":
            content = str(result.get("content", ""))
            snippet = content[:800] + ("\n..." if len(content) > 800 else "")
            reply = f"📖 Read OK: {result.get('path')}\n\n" + snippet
        else:
            reply = f"❗ Read failed: {result}"
        return {"reply": reply}

    # Detect write intent: "write <path>: <content>" or "write <path> = <content>"
    write_match = re.search(r"\bwrite\s+([\w\-/\\\.]+)\s*[:=]\s*(.*)", prompt, re.IGNORECASE)
    if write_match:
        path, content = write_match.groups()
        result = governed_write(path, content)
        log_event("chat_file_write", {"path": path, "status": result.get("status")})
        if isinstance(result, dict):
            status = result.get("status")
            if status == "success":
                reply = f"✍️ Write OK: {result.get('path')}"
            elif status == "pending_approval":
                reply = f"⏳ Write pending HITL approval for: {result.get('path')}\nHint: set HITL_APPROVE=true to proceed."
            else:
                reply = f"❗ Write failed: {result}"
        else:
            reply = str(result)
        return {"reply": reply}

    # Detect list intent: "list <path>" or natural language like "show files" / "see my files"
    list_match = re.search(r"\blist\s+([\w\-/\\\.]+)", prompt, re.IGNORECASE)
    if list_match:
        lpath = list_match.group(1)
        result = list_dir(lpath)
        log_event("chat_list_dir", {"path": lpath, "status": result.get("status")})
        if isinstance(result, dict) and result.get("status") == "success":
            items = result.get("items", [])
            names = [f"{it.get('name')} ({it.get('type')})" for it in items]
            reply = "📁 Listing for " + str(result.get("path")) + "\n- " + "\n- ".join(names[:50])
        else:
            reply = f"❗ List failed: {result}"
        return {"reply": reply}

    # Natural-language hinting for file access
    lower = prompt.lower()
    if any(kw in lower for kw in ["show files", "see files", "see my files", "browse files", "what files", "list files", "agent factory files"]):
        roots_res = list_dir(None)
        roots = []
        if isinstance(roots_res, dict):
            roots = roots_res.get("roots", [])
        root_names = [os.path.basename(r.rstrip("/\\")) or r for r in roots]
        tip = "I can access governed project files. Roots: " + ", ".join(root_names) + ".\nTry: 'list knowledge_base' or 'read factory_governance/genesis_principles.yaml'"
        log_event("chat_hint_files", {"prompt_len": len(prompt)})
        return {"reply": tip}

    # Fallback generic response (no reasoning engine wired here by design)
    msg = "No file operation detected. Say 'read <path>', 'write <path>: <content>', or 'list <path>'."
    log_event("chat_noop", {"prompt_len": len(prompt)})
    return {"reply": msg}


if __name__ == "__main__":
    # Allow running directly for local smoke tests
    import uvicorn

    port = int(os.getenv("ARCHY_PORT", "5065"))
    uvicorn.run("agent_factory.server.fastapi_server:app", host="0.0.0.0", port=port, log_level="info")
