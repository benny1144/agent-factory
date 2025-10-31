from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict

import sys

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None  # type: ignore

# Best-effort audit import
# Ensure repo-root and src are on sys.path for absolute imports
try:
    import tools.startup  # type: ignore  # noqa: F401
except Exception:
    # Fallback: manually add repo root and src
    _root = Path(__file__).resolve().parents[1]
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    _src = _root / "src"
    if _src.exists() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

# Best-effort audit import
try:
    from agent_factory.services.audit.audit_logger import log_event
except Exception:  # pragma: no cover
    def log_event(event_type: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        payload = {"event_type": event_type, "metadata": metadata or {}}
        print(f"[AUDIT] {json.dumps(payload)}")
        return payload


def ensure_dirs() -> Path:
    root = Path(__file__).resolve().parents[1]
    out_dir = root / "artifacts" / "payloads"
    out_dir.mkdir(parents=True, exist_ok=True)
    # ensure compliance log dir
    (root / "compliance" / "audit_log").mkdir(parents=True, exist_ok=True)
    return out_dir


REQUIRED_FIELDS = {
    "agent_name": str,
    "codename": str,
    "purpose": str,
    "capabilities": list,
    "constraints": dict,
    "implementation_targets": list,
    "dependencies": list,
    "coordination": dict,
    "verification": dict,
}


def validate_payload(p: Dict[str, Any]) -> None:
    # Required top-level keys and types
    for k, t in REQUIRED_FIELDS.items():
        if k not in p:
            raise ValueError(f"missing field: {k}")
        if not isinstance(p[k], t):
            raise TypeError(f"field {k} must be {t.__name__}")
    # Minimal nested checks
    c = p["constraints"]
    for ck in ("code_execution", "system_modifications", "file_writes_logged", "governance_hooks_required"):
        if ck not in c:
            raise ValueError(f"constraints.{ck} missing")
        if not isinstance(c[ck], bool):
            raise TypeError(f"constraints.{ck} must be bool")
    v = p["verification"]
    for vk in ("junie_validation_pass", "governance_registry_entry", "health_check_endpoint"):
        if vk not in v:
            raise ValueError(f"verification.{vk} missing")
    if not isinstance(v["junie_validation_pass"], bool) or not isinstance(v["governance_registry_entry"], bool):
        raise TypeError("verification booleans invalid")
    if not isinstance(v["health_check_endpoint"], str):
        raise TypeError("verification.health_check_endpoint must be str")


def append_activity(action: str, detail: str) -> None:
    root = Path(__file__).resolve().parents[1]
    log_path = root / "compliance" / "audit_log" / "junie_activity.csv"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            from datetime import datetime, timezone
            ts = datetime.now(timezone.utc).isoformat()
            f.write(f"{ts},{action},{detail}\n")
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and send Archivist build payload to Genesis")
    parser.add_argument("payload", help="Path to JSON payload", nargs="?", default=str(Path("payloads") / "archivist_creation_request.json"))
    parser.add_argument("--validate", action="store_true", help="Validate payload only")
    parser.add_argument("--send", action="store_true", help="Send payload to Genesis at localhost:5055/build_agent")
    parser.add_argument("--endpoint", default="http://localhost:5055/build_agent", help="Genesis build endpoint")
    args = parser.parse_args()

    payload_path = Path(args.payload)
    if not payload_path.exists():
        print(f"[ERROR] payload file not found: {payload_path}")
        return 1

    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] invalid JSON: {e}")
        return 1

    try:
        validate_payload(payload)
    except Exception as e:
        print(f"[ERROR] payload schema invalid: {e}")
        log_event("payload_validation_failed", {"payload": payload_path.name, "error": str(e)})
        return 1

    print("[Validation] Archivist payload schema valid.")
    log_event("payload_validation_ok", {"payload": payload_path.name, "agent": payload.get("agent_name"), "codename": payload.get("codename")})
    append_activity("payload_validation_ok", payload_path.name)

    if not args.send:
        return 0

    if httpx is None:
        print("[ERROR] httpx not available. Install httpx to enable sending.")
        return 1

    ensure_dirs()
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(args.endpoint, json=payload)
            if resp.status_code >= 400:
                print(f"[ERROR] Genesis responded with {resp.status_code}: {resp.text}")
                log_event("genesis_build_request_failed", {"status": resp.status_code, "text": resp.text[:500]})
                return 1
            data = resp.json()
    except Exception as e:
        print(f"[ERROR] Failed to send request: {e}")
        log_event("genesis_build_request_error", {"error": str(e)})
        return 1

    out_dir = ensure_dirs()
    out_file = out_dir / "archivist_build_response.json"
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"[OK] Genesis acknowledged. Response saved to {out_file}")
    log_event("genesis_build_request_ok", {"response_path": out_file.as_posix(), "status": "ack"})
    append_activity("genesis_build_request_ok", out_file.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
