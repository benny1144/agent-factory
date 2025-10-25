from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import httpx
from fastapi import APIRouter, UploadFile, Form

# Local services
from agent_factory.services.governance import get_audit_logs, list_agents, create_agent

router = APIRouter()


@router.get("/api/agents")
async def get_agents() -> Dict[str, Any]:
    return list_agents()


@router.post("/api/agents")
async def post_agent(name: str = Form(...), role: str = Form("") ) -> Dict[str, Any]:
    return create_agent(name, role)


@router.get("/api/kba")
async def get_kba_index() -> Any:
    # Adapted path: our registry index lives under /registry/metadata_index.json
    path = Path("registry") / "metadata_index.json"
    if not path.exists():
        return {"ok": False, "error": "registry_missing", "path": str(path)}
    return json.loads(path.read_text(encoding="utf-8"))


@router.post("/api/upload_kba")
async def upload_kba(file: UploadFile):
    base = Path("knowledge_base") / "raw"
    base.mkdir(parents=True, exist_ok=True)
    dest = base / file.filename
    content = await file.read()
    dest.write_bytes(content)
    return {"status": "uploaded", "file": str(dest)}


@router.post("/api/junie")
async def send_to_junie(task: Dict[str, Any]) -> Dict[str, Any]:
    """Proxy structured [JUNIE TASK]s to the IntelliJ bridge if configured.

    Env:
      - BRIDGE_URL or JUNIE_BRIDGE_URL: Base URL for Junie Bridge (e.g., https://<subdomain>.trycloudflare.com)
      - JUNIE_TOKEN (optional): Token to include as X-Junie-Token header
    Behavior:
      - If no bridge is configured, append the task to artifacts/junie_tasks.jsonl and return stub.
    """
    bridge = os.getenv("BRIDGE_URL") or os.getenv("JUNIE_BRIDGE_URL")
    token = os.getenv("JUNIE_TOKEN") or os.getenv("BRIDGE_TOKEN")
    if not bridge:
        # Append to local artifacts as a fallback
        artifacts = Path("artifacts"); artifacts.mkdir(parents=True, exist_ok=True)
        out = artifacts / "junie_tasks.jsonl"
        try:
            line = json.dumps({"ts": __import__("datetime").datetime.utcnow().isoformat() + "Z", "task": task}, ensure_ascii=False)
            with out.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        return {"ok": False, "error": "bridge_unconfigured", "stored": True}

    # Normalize base URL (ensure no trailing slash)
    bridge = bridge.rstrip("/")
    url = f"{bridge}/messages/send"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Junie-Token"] = token
    payload = {"role": "user", "text": task.get("text") or task}
    try:
        async with httpx.AsyncClient(timeout=20.0, verify=False) as client:
            resp = await client.post(url, headers=headers, json=payload)
            ok = resp.status_code < 400
            return {"ok": ok, "status_code": resp.status_code, "data": (resp.json() if ok else resp.text)}
    except Exception as e:  # network failures should not crash API
        return {"ok": False, "error": str(e)}


