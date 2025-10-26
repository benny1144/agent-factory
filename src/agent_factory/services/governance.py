from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Repo-root aware paths
try:
    from agent_factory.utils.paths import PROJECT_ROOT
except Exception:  # fallback for isolated execution
    PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
VALIDATION_LOGS_DIR = PROJECT_ROOT / "validation" / "logs"
AGENTS_FILE = DATA_DIR / "agents.json"


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_agents() -> Dict[str, Any]:
    """Return the list of registered agents from data/agents.json.

    Returns a payload: {"agents": [...]}
    """
    agents: List[Dict[str, Any]] = _read_json(AGENTS_FILE, default=[])
    if not isinstance(agents, list):
        agents = []
    return {"agents": agents}


def create_agent(name: str, role: str) -> Dict[str, Any]:
    """Append a new agent record into data/agents.json with timestamp and id.

    Args:
        name: Agent display name
        role: Agent role description
    Returns:
        The created agent record.
    """
    name = (name or "").strip()
    role = (role or "").strip()
    if not name:
        return {"ok": False, "error": "name_required"}

    agents: List[Dict[str, Any]] = _read_json(AGENTS_FILE, default=[])
    if not isinstance(agents, list):
        agents = []
    agent = {
        "id": f"a-{len(agents)+1:04d}",
        "name": name,
        "role": role,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    agents.append(agent)
    _write_json(AGENTS_FILE, agents)
    return {"ok": True, "agent": agent}


def get_audit_logs(limit: int = 100) -> Dict[str, Any]:
    """Collect recent [AUDIT] lines from artifacts/*.log and validation/logs/*.

    Args:
        limit: max lines to return
    Returns:
        {"entries": ["[AUDIT] ...", ...], "count": n}
    """
    entries: List[str] = []

    # validation/logs
    if VALIDATION_LOGS_DIR.exists():
        for f in sorted(VALIDATION_LOGS_DIR.rglob("*.log")):
            try:
                for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if "[AUDIT]" in line:
                        entries.append(line)
            except Exception:
                pass

    # artifacts logs (flat scan)
    if ARTIFACTS_DIR.exists():
        for f in sorted(ARTIFACTS_DIR.rglob("*.log")):
            try:
                for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if "[AUDIT]" in line:
                        entries.append(line)
            except Exception:
                pass

    entries = entries[-limit:] if limit and limit > 0 else entries
    return {"entries": entries, "count": len(entries)}


__all__ = ["list_agents", "create_agent", "get_audit_logs"]
