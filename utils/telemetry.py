from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from tools.logging_utils import JsonlLogger
from utils.paths import LOGS_DIR, PROJECT_ROOT

_log = JsonlLogger(log_file=LOGS_DIR / 'infra_health.jsonl')

GOV_LOG_DIR = LOGS_DIR / 'governance'
GOV_LOG_DIR.mkdir(parents=True, exist_ok=True)
TELEMETRY_AUDIT = GOV_LOG_DIR / 'orion_audit.jsonl'


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_health(service: str, ok: bool, **fields) -> None:
    data = {'event': 'service_health', 'service': service, 'ok': ok, **fields}
    _log.log(ok, data)


def activate_watchtower() -> dict:
    """Append an ACTIVE telemetry marker for Watchtower/Orion governance stream.

    Returns dict with ok flag and audit_path.
    """
    payload = {"ts": _iso(), "component": "watchtower", "telemetry": "ACTIVE"}
    try:
        with TELEMETRY_AUDIT.open('a', encoding='utf-8') as f:
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
        return {"ok": True, "audit_path": str(TELEMETRY_AUDIT)}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {str(e)[:200]}", "audit_path": str(TELEMETRY_AUDIT)}


def telemetry_status() -> dict:
    """Return current telemetry active status by reading the audit tail."""
    try:
        if not TELEMETRY_AUDIT.exists():
            return {"active": False}
        lines = [ln for ln in TELEMETRY_AUDIT.read_text(encoding='utf-8').splitlines() if ln.strip()]
        if not lines:
            return {"active": False}
        last = json.loads(lines[-1])
        return {"active": str(last.get('telemetry', '')).upper() == 'ACTIVE'}
    except Exception:
        return {"active": False}
