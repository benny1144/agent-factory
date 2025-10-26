from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Local imports (repo-root safe; pytest.ini adds src to pythonpath)
try:
    from agent_factory.utils.procedural_memory_pg import (
        record_governance_event,
        append_governance_event,
        init_db,
    )
    from agent_factory.utils.paths import PROJECT_ROOT
    from agent_factory.services.audit.audit_logger import log_event as audit_log_event
except Exception:  # pragma: no cover - fallback
    record_governance_event = None  # type: ignore
    append_governance_event = None  # type: ignore
    def audit_log_event(event_type: str, metadata: dict | None = None):  # type: ignore
        return {"ok": True, "data": {"event_type": event_type, "metadata": metadata or {}}}
    PROJECT_ROOT = Path(__file__).resolve().parents[3]

HITL_LOG_PATH = PROJECT_ROOT / "artifacts" / "hitl_actions.jsonl"
HITL_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_hitl_action(agent: str, action: str, reason: str, approver: str, risk_level: str = "HIGH") -> None:
    """Log human-in-the-loop actions for governance oversight.

    Behaviors:
    - Append-only JSONL under artifacts/hitl_actions.jsonl
    - Mirror into governance_history (back-compat) and governance_events (structured)
    - Emit [AUDIT] hitl_action for Cloud Logging ingestion
    """
    ts = datetime.now(timezone.utc).isoformat()
    record = {
        "timestamp": ts,
        "agent": agent,
        "action": action,
        "reason": reason,
        "approver": approver,
        "risk_level": risk_level,
    }
    # Append-only write
    with open(HITL_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Mirror to DB if available (append-only semantics)
    try:
        init_db()  # ensure tables exist
        if record_governance_event is not None:
            record_governance_event(agent=agent, action=action, reason=reason, approver=approver)
        if append_governance_event is not None:
            append_governance_event(
                agent_id=agent,
                event_type="hitl_action",
                risk_level=risk_level,
                approved_by=approver,
                details={"action": action, "reason": reason},
            )
    except Exception:
        # Non-fatal: logging to file is the primary persistence; DB mirroring is best-effort
        pass

    # Emit structured audit event for Cloud Logging
    try:
        audit_log_event("hitl_action", {
            "agent": agent,
            "action": action,
            "risk_level": risk_level,
            "approver": approver,
            "ts": ts,
        })
    except Exception:
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
    risk = os.getenv("HITL_DEMO_RISK", "HIGH")
    log_hitl_action(agent=agent, action=action, reason=reason, approver=approver, risk_level=risk)


def _parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="HITL Logger")
    p.add_argument("--simulate", action="store_true", help="Emit a demo HITL record")
    p.add_argument("--agent", default=None)
    p.add_argument("--action", default=None)
    p.add_argument("--reason", default=None)
    p.add_argument("--approver", default=None)
    p.add_argument("--risk", default=None)
    return p.parse_args()


if __name__ == "__main__":
    ns = _parse_cli()
    if ns.simulate or (ns.agent is None and ns.action is None):
        _demo()
    else:
        log_hitl_action(
            agent=ns.agent or "Agent",
            action=ns.action or "approve",
            reason=ns.reason or "manual",
            approver=ns.approver or "operator",
            risk_level=ns.risk or "HIGH",
        )


__all__ = ["log_hitl_action", "HITL_LOG_PATH"]
