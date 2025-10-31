from __future__ import annotations

import json
from dataclasses import dataclass
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


@dataclass
class AgentSpec:
    goal: str
    name: str
    version: str
    skills: list[str]
    constraints: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "name": self.name,
            "version": self.version,
            "skills": self.skills,
            "constraints": self.constraints,
        }


def propose(goal: str) -> Dict[str, Any]:
    """Propose a deterministic agent spec from a goal (no network).

    Returns standard envelope: {ok, data, error, meta}
    """
    try:
        goal_s = (goal or "").strip()
        version = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
        name = f"genesis_{abs(hash(goal_s)) % 10000:04d}"
        spec = AgentSpec(
            goal=goal_s or "hello-world",
            name=name,
            version=version,
            skills=["plan", "design", "verify"],
            constraints=["no_secrets", "hitl_optional"],
        )
        payload = {
            "ok": True,
            "data": {"spec": spec.to_dict()},
            "error": None,
            "meta": {"ts": _iso_now(), "component": "agent_designer", "action": "propose"},
        }
        _append_jsonl(GENESIS_LOG, payload)
        return payload
    except Exception as e:  # pragma: no cover - defensive
        err = {"ok": False, "data": {}, "error": str(e), "meta": {"ts": _iso_now(), "component": "agent_designer"}}
        _append_jsonl(GENESIS_LOG, err)
        return err
