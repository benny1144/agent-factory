from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Repo-root resolution
PROJECT_ROOT = Path(__file__).resolve()
while PROJECT_ROOT.name != "agent-factory" and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent

LOGS_DIR = PROJECT_ROOT / "logs"
REGISTRY_DIR = PROJECT_ROOT / "registry"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
REGISTRY_DIR.mkdir(parents=True, exist_ok=True)
GENESIS_LOG = LOGS_DIR / "genesis_orchestration.jsonl"
AGENTS_CREATED = REGISTRY_DIR / "agents_created.jsonl"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def assemble(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble a mock crew from an agent spec (deterministic, no I/O side effects beyond logs).

    Returns standard envelope: {ok, data, error, meta}
    Also appends a creation record to registry/agents_created.jsonl
    """
    try:
        s = (spec or {}).get("spec") or spec or {}
        name = str(s.get("name") or "genesis_agent")
        crew = {
            "name": name,
            "members": [
                {"role": "designer", "skills": ["plan", "spec"]},
                {"role": "builder", "skills": ["compose", "wire"]},
                {"role": "runner", "skills": ["execute", "report"]},
            ],
            "version": s.get("version") or _iso_now(),
        }
        payload = {
            "ok": True,
            "data": {"crew": crew},
            "error": None,
            "meta": {"ts": _iso_now(), "component": "crew_builder", "action": "assemble"},
        }
        _append_jsonl(GENESIS_LOG, payload)
        _append_jsonl(AGENTS_CREATED, {"ts": _iso_now(), "agent": name, "event": "crew_assembled"})
        return payload
    except Exception as e:  # pragma: no cover
        err = {"ok": False, "data": {}, "error": str(e), "meta": {"ts": _iso_now(), "component": "crew_builder"}}
        _append_jsonl(GENESIS_LOG, err)
        return err
