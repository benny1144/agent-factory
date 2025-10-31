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
LOGS_DIR.mkdir(parents=True, exist_ok=True)
GENESIS_LOG = LOGS_DIR / "genesis_orchestration.jsonl"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def dry_run(goal: str = "hello-world") -> Dict[str, Any]:
    """Perform a deterministic dry-run (no side effects beyond logging)."""
    payload = {
        "ok": True,
        "data": {
            "goal": goal,
            "result": f"dry-run-ok:{len(goal)}",
        },
        "error": None,
        "meta": {"ts": _iso_now(), "component": "mission_runner", "action": "dry_run"},
    }
    _append_jsonl(GENESIS_LOG, payload)
    return payload


def execute(crew: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a mock mission with the given crew (deterministic)."""
    name = ((crew or {}).get("crew") or {}).get("name") if "crew" in (crew or {}) else (crew or {}).get("name")
    res = {
        "crew": name or "genesis_agent",
        "status": "completed",
        "summary": "Mock mission executed successfully.",
    }
    payload = {
        "ok": True,
        "data": res,
        "error": None,
        "meta": {"ts": _iso_now(), "component": "mission_runner", "action": "execute"},
    }
    _append_jsonl(GENESIS_LOG, payload)
    return payload
