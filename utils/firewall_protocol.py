from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any, Callable, TypeVar, cast

# Audit logger for governance trace (lazy import to avoid static resolution issues)
import importlib

def log_event(event_type: str, metadata: dict | None = None):  # default no-op fallback
    return {"ok": True, "data": {"event_type": event_type, "metadata": metadata or {}}}

try:
    _mod = importlib.import_module("agent_factory.services.audit.audit_logger")
    if hasattr(_mod, "log_event"):
        log_event = getattr(_mod, "log_event")  # type: ignore
except Exception:
    # keep fallback
    pass

# Paths
try:
    from utils.paths import PROJECT_ROOT
    RISK_MATRIX_PATH = PROJECT_ROOT / "personas" / "risk_matrix.json"
except Exception:
    RISK_MATRIX_PATH = Path("personas") / "risk_matrix.json"

F = TypeVar("F", bound=Callable[..., Any])


class EscalationLevel:
    HITL = "HITL"   # Human-in-the-Loop (must approve)
    HOTL = "HOTL"   # Human-on-the-Loop (notify, optional approve)
    HOOTL = "HOOTL" # Human-out-of-the-Loop (no prompt)


def _get_escalation_level(default: str | None = None) -> str:
    lvl = os.getenv("ESCALATION_LEVEL") or default or EscalationLevel.HITL
    lvl = lvl.upper()
    if lvl not in {EscalationLevel.HITL, EscalationLevel.HOTL, EscalationLevel.HOOTL}:
        lvl = EscalationLevel.HITL
    return lvl


def load_persona_risk(persona: str) -> str:
    """Return escalation tier for given persona from personas/risk_matrix.json.

    Falls back to environment ESCALATION_LEVEL or HITL when file/persona not found.
    """
    if not RISK_MATRIX_PATH.exists():
        return _get_escalation_level()
    try:
        data = json.loads(RISK_MATRIX_PATH.read_text(encoding="utf-8"))
        pconf = data.get(persona.title()) or {}
        return (pconf.get("default") or _get_escalation_level()).upper()
    except Exception:
        return _get_escalation_level()


def require_hitl(func: F) -> F:
    """Decorator enforcing Human Firewall escalation based on env.

    - HITL: Requires explicit "approve" typed by operator.
    - HOTL: Displays notice; continues unless HITL_APPROVE=false AND operator rejects.
    - HOOTL: No prompt; proceed.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        lvl = _get_escalation_level()
        if lvl == EscalationLevel.HOOTL:
            return func(*args, **kwargs)
        if lvl == EscalationLevel.HOTL:
            print("[FIREWALL] HOTL: Proceeding unless blocked by operator...")
            if os.getenv("HITL_APPROVE", "true").lower() != "true":
                resp = input("Type 'approve' to continue (HOTL): ")
                if resp.strip().lower() != "approve":
                    raise PermissionError("Operation not approved under HOTL policy.")
            return func(*args, **kwargs)
        # Default HITL
        if os.getenv("HITL_APPROVE", "false").lower() != "true":
            resp = input("Type 'approve' to continue (HITL): ")
            if resp.strip().lower() != "approve":
                raise PermissionError("Operation not approved under HITL policy.")
        return func(*args, **kwargs)

    return cast(F, wrapper)


def require_risk(level: str = "LOW"):
    """Decorator enforcing tiered Human Firewall based on risk level with persona awareness.

    - level="HIGH": Always enforce HITL approval (strongest gate).
    - level!="HIGH": Use persona-level default escalation when available, else fallback to ESCALATION_LEVEL.
    Also emits an [AUDIT] persona_escalation event for governance trace.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            lvl = (level or "LOW").upper()
            if lvl == "HIGH":
                # Strict HITL approval path
                if os.getenv("HITL_APPROVE", "false").lower() != "true":
                    resp = input("Type 'approve' to continue (HITL/HIGH RISK): ")
                    if resp.strip().lower() != "approve":
                        raise PermissionError("Operation not approved under HIGH risk policy.")
                return func(*args, **kwargs)

            # Persona-aware path for non-HIGH operations
            persona = os.getenv("AGENT_PERSONA", "Architect")
            esc = load_persona_risk(persona)
            try:
                log_event("persona_escalation", {"persona": persona, "escalation": esc})
            except Exception:
                pass

            if esc == EscalationLevel.HOOTL:
                return func(*args, **kwargs)
            if esc == EscalationLevel.HOTL:
                print("[FIREWALL] HOTL (persona policy): Proceeding unless blocked by operator...")
                if os.getenv("HITL_APPROVE", "true").lower() != "true":
                    resp = input("Type 'approve' to continue (HOTL/persona): ")
                    if resp.strip().lower() != "approve":
                        raise PermissionError("Operation not approved under HOTL persona policy.")
                return func(*args, **kwargs)
            # Default HITL
            if os.getenv("HITL_APPROVE", "false").lower() != "true":
                resp = input("Type 'approve' to continue (HITL/persona): ")
                if resp.strip().lower() != "approve":
                    raise PermissionError("Operation not approved under HITL persona policy.")
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


__all__ = ["require_hitl", "EscalationLevel", "require_risk", "load_persona_risk"]