from __future__ import annotations
import os
import hmac
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse

try:
    from factory_agents.archivist.reasoning_core import get_reflective_metrics
except Exception:  # pragma: no cover
    def get_reflective_metrics() -> Dict[str, Any]:  # type: ignore
        return {"reflective_sync_runs_total": 0}

router = APIRouter()
ROOT = Path(__file__).resolve().parents[2]


def _append_line(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


@router.post("/governance/approve")
async def approve_governance(event_id: str, reviewer: str, decision: str) -> Dict[str, Any]:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_id": event_id,
        "reviewer": reviewer,
        "decision": decision,
    }
    log_path = ROOT / "governance" / "firewall_audit.log"
    _append_line(log_path, json.dumps(record, ensure_ascii=False))
    return {"ok": True, "logged": True}


@router.get("/dashboard", response_class=HTMLResponse)
async def governance_dashboard() -> str:
    # Minimal inline HTML dashboard (no Jinja dependency)
    log_path = ROOT / "governance" / "firewall_audit.log"
    lines = []
    if log_path.exists():
        try:
            lines = log_path.read_text(encoding="utf-8").splitlines()[-50:]
        except Exception:
            lines = []
    html_rows = "".join(f"<tr><td>{i}</td></tr>" for i in lines)
    return f"""
    <html><head><title>Governance Dashboard</title></head>
    <body>
      <h1>Governance Dashboard</h1>
      <h2>Recent Firewall Audit (last 50)</h2>
      <table border='1' cellpadding='6'>{html_rows}</table>
    </body></html>
    """


# --- Federation with JWT validation (HS256) ---
# Validates exp/iat/nbf and logs activity to logs/federation_activity.jsonl
from typing import Optional
from fastapi import Request, Body
from pydantic import BaseModel
import jwt


def _jwt_secret() -> str:
    # Prefer explicit JWT secret, fallback to legacy FEDERATION_SECRET, else dev default
    return os.getenv("FEDERATION_JWT_SECRET") or os.getenv("FEDERATION_SECRET") or "dev-secret"


def _decode_jwt(token: str) -> Dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            _jwt_secret(),
            algorithms=["HS256"],
            options={"require": ["exp", "iat", "nbf"]},
        )
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.ImmatureSignatureError:
        raise HTTPException(status_code=401, detail="token not yet valid (nbf)")
    except jwt.InvalidIssuedAtError:
        raise HTTPException(status_code=401, detail="invalid iat")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"invalid token: {e}")


class FederationEvent(BaseModel):
    event: str
    agent_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


@router.post("/federation/broadcast")
async def federation_broadcast(request: Request, body: FederationEvent = Body(...)) -> Dict[str, Any]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = auth.split(" ", 1)[1].strip()
    claims = _decode_jwt(token)
    agent_id = body.agent_id or str(claims.get("sub") or claims.get("agent_id") or "unknown")

    # Log activity
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "agent_id": agent_id,
        "event": body.event,
        "claims": {k: v for k, v in claims.items() if k not in {"exp", "nbf", "iat"}},
        "data": body.data or {},
        "source": "federation.broadcast",
    }
    log_path = ROOT / "logs" / "federation_activity.jsonl"
    _append_line(log_path, json.dumps(rec, ensure_ascii=False))

    # Also append CSV audit (backward compatibility)
    path = ROOT / "compliance" / "audit_log" / "federation_updates.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    line = f"{rec['ts']},{agent_id},{json.dumps({'event': body.event}, ensure_ascii=False)}"
    _append_line(path, line)
    return {"ok": True, "accepted": True, "meta": {"agent_id": agent_id}}


@router.post("/federation/subscribe")
async def federation_subscribe(agent_id: str) -> Dict[str, Any]:
    # Minimal subscription registry (append-only text)
    path = ROOT / "governance" / "federation_subscribers.txt"
    _append_line(path, f"{datetime.now(timezone.utc).isoformat()},{agent_id}")
    return {"ok": True}


# --- AutoGen Bridge endpoint ---
class AutoGenRunRequest(BaseModel):
    task: str
    params: Optional[Dict[str, Any]] = None


@router.post("/autogen/run")
async def autogen_run(req: AutoGenRunRequest) -> Dict[str, Any]:
    try:
        from services.autogen.bridge import AutoGenBridge
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"autogen bridge unavailable: {e}")
    bridge = AutoGenBridge()
    result = bridge.run(req.task, req.params or {})
    return result


@router.get("/archivist/metrics", response_class=PlainTextResponse)
async def archivist_metrics() -> str:
    metrics = get_reflective_metrics()
    # Expose as Prometheus-style
    out = []
    for k, v in metrics.items():
        if isinstance(v, (int, float)):
            out.append(f"{k} {v}")
    return "\n".join(out) + "\n"


@router.get("/metrics", response_class=PlainTextResponse)
async def unified_metrics() -> str:
    """Unified metrics aggregator for Prometheus scraping.
    Combines ReflectiveSync counters + compliance summaries + drift score.
    """
    lines: list[str] = []
    # ReflectiveSync
    try:
        m = get_reflective_metrics()
        for k, v in m.items():
            if isinstance(v, (int, float)):
                lines.append(f"archivist_{k} {v}")
    except Exception:
        pass
    # Compliance metrics file (from scheduler)
    try:
        cm_path = ROOT / "logs" / "compliance_metrics.json"
        if cm_path.exists():
            obj = json.loads(cm_path.read_text(encoding="utf-8"))
            if isinstance(obj.get("ledger_entries"), (int, float)):
                lines.append(f"archivist_compliance_ledger_entries_total {obj['ledger_entries']}")
            if isinstance(obj.get("firewall_events"), (int, float)):
                lines.append(f"archivist_compliance_firewall_events_total {obj['firewall_events']}")
            if obj.get("last_drift_score") is not None:
                try:
                    lines.append(f"archivist_persona_drift_last_score {float(obj['last_drift_score'])}")
                except Exception:
                    pass
    except Exception:
        pass
    # Fallback ledger count if metrics file missing
    try:
        root = ROOT
        ledger = root / "governance" / "compliance_ledger.jsonl"
        if ledger.exists() and not any(s.startswith("archivist_compliance_ledger_entries_total") for s in lines):
            cnt = sum(1 for _ in ledger.open("r", encoding="utf-8"))
            lines.append(f"archivist_compliance_ledger_entries_total {cnt}")
    except Exception:
        pass
    return "\n".join(lines) + "\n"