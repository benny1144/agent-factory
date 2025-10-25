from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Local imports (repo-root safe; pytest.ini adds src to pythonpath)
try:
    from utils.procedural_memory_pg import record_governance_event, init_db
    from utils.paths import PROJECT_ROOT
except Exception:  # pragma: no cover - fallback
    record_governance_event = None  # type: ignore
    PROJECT_ROOT = Path(__file__).resolve().parents[3]

HITL_LOG_PATH = PROJECT_ROOT / "artifacts" / "hitl_actions.jsonl"
HITL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_hitl_action(agent: str, action: str, reason: str, approver: str) -> None:
    """Log human-in-the-loop actions for governance oversight.

    This writes an append-only JSONL record under artifacts/hitl_actions.jsonl and,
    when available, mirrors the event into the procedural memory database
    (utils.procedural_memory_pg.governance_history).
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "action": action,
        "reason": reason,
        "approver": approver,
    }
    # Append-only write
    with open(HITL_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Mirror to DB if available
    try:
        if record_governance_event is not None:
            init_db()  # ensure tables exist
            record_governance_event(agent=agent, action=action, reason=reason, approver=approver)
    except Exception:
        # Non-fatal: logging to file is the primary persistence; DB mirroring is best-effort
        pass

    print(f"[HITL] {approver} {action} for {agent}: {reason}")


def _demo() -> None:
    """Emit a sample HITL record for CI smoke tests.

    Reads env overrides for fields if present to allow customization.
    """
    agent = os.getenv("HITL_DEMO_AGENT", "GenesisCrew")
    action = os.getenv("HITL_DEMO_ACTION", "approve")
    reason = os.getenv("HITL_DEMO_REASON", "CI governance check")
    approver = os.getenv("HITL_DEMO_APPROVER", "ci-bot")
    log_hitl_action(agent=agent, action=action, reason=reason, approver=approver)


if __name__ == "__main__":
    _demo()


__all__ = ["log_hitl_action", "HITL_LOG_PATH"]
