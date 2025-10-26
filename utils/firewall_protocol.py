from __future__ import annotations

import functools
import json
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar, cast

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


# -------------------------------
# Reflective Maturity: Risk scoring
# -------------------------------
_CRITICALITY_MAP = {
    "low": 0.2,
    "medium": 0.6,
    "high": 1.0,
}

_SENSITIVITY_MAP = {
    "public": 0.1,
    "internal": 0.4,
    "confidential": 0.7,
    "restricted": 1.0,
}


def risk_score(confidence: Optional[float], criticality: str | None, sensitivity: str | None) -> Dict[str, Any]:
    """Compute a normalized risk score [0,1] and oversight tier.

    Inputs:
      - confidence: model confidence in [0,1] (lower confidence ⇒ higher risk). None treated as 0.5
      - criticality: low|medium|high (default medium)
      - sensitivity: public|internal|confidential|restricted (default internal)
    Output:
      {"score": float, "tier": "HITL|HOTL|HOOTL", "factors": {...}}
    """
    try:
        c = float(confidence) if confidence is not None else 0.5
    except Exception:
        c = 0.5
    c = 0.0 if c < 0 else 1.0 if c > 1 else c
    # Lower confidence means higher risk contribution
    conf_risk = 1.0 - c

    crit = (criticality or "medium").strip().lower()
    sens = (sensitivity or "internal").strip().lower()
    crit_risk = _CRITICALITY_MAP.get(crit, 0.6)
    sens_risk = _SENSITIVITY_MAP.get(sens, 0.4)

    # Weighted blend
    score = 0.5 * conf_risk + 0.3 * crit_risk + 0.2 * sens_risk
    if score >= 0.66:
        tier = EscalationLevel.HITL
    elif score >= 0.40:
        tier = EscalationLevel.HOTL
    else:
        tier = EscalationLevel.HOOTL

    return {
        "score": float(score),
        "tier": tier,
        "factors": {
            "confidence": c,
            "conf_risk": conf_risk,
            "criticality": crit,
            "crit_risk": crit_risk,
            "sensitivity": sens,
            "sens_risk": sens_risk,
        },
    }


def evaluate_risk_before_action(context: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate risk given a context and emit an audit event.

    Expected context keys include (optional):
      - goal, action, actor
      - llm_confidence: float in [0,1]
      - criticality: str (low|medium|high)
      - sensitivity: str (public|internal|confidential|restricted)
    Returns the risk payload with score and tier.
    """
    llm_conf = context.get("llm_confidence")
    crit = context.get("criticality")
    sens = context.get("sensitivity")
    result = risk_score(
        confidence=llm_conf if isinstance(llm_conf, (int, float)) else None,
        criticality=str(crit) if crit is not None else None,
        sensitivity=str(sens) if sens is not None else None,
    )

    # Persona-aware override floor: if persona policy is stricter than computed tier, honor stricter
    try:
        persona = os.getenv("AGENT_PERSONA", "Architect")
        persona_default = load_persona_risk(persona)
    except Exception:
        persona_default = _get_escalation_level()
    # Order: HITL > HOTL > HOOTL
    order = {EscalationLevel.HITL: 2, EscalationLevel.HOTL: 1, EscalationLevel.HOOTL: 0}
    if order.get(persona_default, 2) > order.get(result["tier"], 0):
        result["tier"] = persona_default
        result.setdefault("notes", []).append("persona_floor_applied") if isinstance(result.get("notes"), list) else result.update({"notes": ["persona_floor_applied"]})

    meta = {"context": {k: v for k, v in context.items() if k in {"goal", "action", "actor", "criticality", "sensitivity"}}, "result": result}
    try:
        log_event("risk_evaluated", meta)
    except Exception:
        pass
    return result


__all__ = [
    "require_hitl",
    "EscalationLevel",
    "require_risk",
    "load_persona_risk",
    "risk_score",
    "evaluate_risk_before_action",
]