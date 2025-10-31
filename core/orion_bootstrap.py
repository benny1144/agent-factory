from __future__ import annotations

import argparse
import json
import os
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from tools.logging_utils import JsonlLogger
from utils.paths import PROJECT_ROOT, LOGS_DIR

LOG_FILE = LOGS_DIR / "orion_activity.jsonl"
TASKS_FROM = PROJECT_ROOT / "tasks" / "from_orion"
TASKS_TO = PROJECT_ROOT / "tasks" / "to_orion"
MANIFEST = PROJECT_ROOT / "federation" / "context_manifest_v2.json"
EVENT_BUS = PROJECT_ROOT / "governance" / "event_bus.jsonl"
AUDITS_DIR = PROJECT_ROOT / "governance" / "audits"

exec_logger = JsonlLogger(log_file=LOG_FILE)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(event: Dict[str, Any]) -> None:
    exec_logger.log(True, {"ts": _iso(), **event})


def _append_bus(event: Dict[str, Any]) -> None:
    try:
        import uuid as _uuid
        EVENT_BUS.parent.mkdir(parents=True, exist_ok=True)
        payload = {"ts": _iso(), **event}
        payload.setdefault("trace_id", _uuid.uuid4().hex)
        with EVENT_BUS.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def ensure_dirs() -> None:
    (PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    TASKS_FROM.mkdir(parents=True, exist_ok=True)
    TASKS_TO.mkdir(parents=True, exist_ok=True)
    EVENT_BUS.parent.mkdir(parents=True, exist_ok=True)
    AUDITS_DIR.mkdir(parents=True, exist_ok=True)


def _process_task_file(path: Path) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        log_event({"event": "read_error", "file": str(path), "error": str(e)})
        return
    log_event({"event": "task_received", "task_file": path.name, "content": content})
    # If this is an execution task (contains a command), leave it for Artisan to consume
    try:
        obj = json.loads(content)
    except Exception:
        obj = None
    if isinstance(obj, dict) and ("command" in obj):
        _append_bus({"agent": "Orion", "type": "task_enqueued", "status": "ok"})
        return
    # Otherwise, archive to Orion outbox as before (informational messages, etc.)
    try:
        dest = TASKS_TO / f"{path.name}.done"
        os.replace(str(path), str(dest))
        log_event({"event": "task_archived", "dest": dest.name})
    except Exception as e:
        log_event({"event": "rename_error", "file": str(path), "error": str(e)})


def _listdir_safe(p: Path) -> list[Path]:
    try:
        return [x for x in p.iterdir() if x.is_file()]
    except Exception:
        return []


def ping_genesis() -> None:
    try:
        rc = os.system("python -S factory_agents/architect_genesis/api.py --ping > NUL 2>&1")
        evt = {"event": "genesis_ping", "ok": (rc == 0)}
        log_event(evt)
        _append_bus({"agent": "Orion", "type": "heartbeat_ping", "status": "ok" if rc == 0 else "error"})
    except Exception as e:
        log_event({"event": "genesis_ping_error", "error": str(e)})
        _append_bus({"agent": "Orion", "type": "heartbeat_ping", "status": "error", "error": str(e)})


def heartbeat_cycle() -> None:
    while True:
        try:
            log_event({"event": "heartbeat", "agents": ["Orion", "Artisan", "Genesis", "Archy"], "heartbeat": True})
            _append_bus({"agent": "Orion", "type": "heartbeat", "status": "ok"})
            ping_genesis()
            time.sleep(30)
        except Exception as e:
            log_event({"event": "heartbeat_error", "error": str(e)})
            _append_bus({"agent": "Orion", "type": "heartbeat", "status": "error", "error": str(e)})
            time.sleep(30)


def run_loop(dry_run: bool = False) -> None:
    ensure_dirs()
    log_event({"phase": 36, "status": "bootstrap_start"})
    print("🜂 Orion: Headless mode active. Watching /tasks/from_orion …")

    # Start heartbeat thread (continuous)
    hb = threading.Thread(target=heartbeat_cycle, daemon=True)
    hb.start()

    # Governance handoff record
    try:
        AUDITS_DIR.mkdir(parents=True, exist_ok=True)
        handoff = {
            "ts": _iso(),
            "phase": 38,
            "handoff": "complete",
            "controller": "Orion",
        }
        handoff_path = AUDITS_DIR / "federation_handoff_v7_5.json"
        handoff_path.write_text(json.dumps(handoff, indent=2), encoding="utf-8")
        _append_bus({"agent": "Orion", "type": "handoff", "status": "complete"})
    except Exception as e:
        log_event({"event": "handoff_write_error", "error": str(e)})

    iteration = 0
    while True:
        for f in _listdir_safe(TASKS_FROM):
            _process_task_file(f)
        # Also ping genesis on main loop iteration (redundant but cheap)
        ping_genesis()
        iteration += 1
        if dry_run:
            break
        time.sleep(5)


def _write_json(path: Path, obj: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    except Exception:
        pass


def verify_access() -> Dict[str, Any]:
    """Verify Orion's read access to repo root and governance directories only.

    Produces governance/audits/orion_activation.json with the verification result.
    """
    ensure_dirs()
    ok = True
    details: Dict[str, Any] = {"can_list_root": False, "can_list_governance": False}
    try:
        _ = [p.name for p in PROJECT_ROOT.iterdir()]
        details["can_list_root"] = True
    except Exception as e:
        ok = False
        details["root_error"] = f"{type(e).__name__}: {str(e)[:200]}"
    try:
        gov = PROJECT_ROOT / "governance"
        _ = [p.name for p in gov.iterdir()] if gov.exists() else []
        details["can_list_governance"] = True
    except Exception as e:
        ok = False
        details["governance_error"] = f"{type(e).__name__}: {str(e)[:200]}"

    rec = {"ts": _iso(), "action": "verify_access", "ok": ok, "details": details}
    _write_json(AUDITS_DIR / "orion_activation.json", rec)
    _append_bus({"agent": "Orion", "type": "verify_access", "status": "ok" if ok else "error"})
    print(json.dumps(rec, indent=2))
    return rec


essential_orion_entry = {
    "agent": "Orion",
    "role": "Control Plane",
    "version": "v1.0",
    "path": "factory_agents/orion_control/main.py",
    "alignment": "Watchtower",
    "status": "production",
}


def register_federation(federation: str | None = None) -> Dict[str, Any]:
    """Register Orion in governance/federation_manifest_v8.json (copy from v7_5 if present)."""
    v7p = PROJECT_ROOT / "governance" / "federation_manifest_v7_5.json"
    v8p = PROJECT_ROOT / "governance" / "federation_manifest_v8.json"
    try:
        if v7p.exists():
            data = json.loads(v7p.read_text(encoding="utf-8"))
        else:
            data = []
    except Exception:
        data = []

    # ensure Orion entry exists
    found = False
    for i, rec in enumerate(data if isinstance(data, list) else []):
        if isinstance(rec, dict) and rec.get("agent") == "Orion":
            found = True
            # update path/alignment if missing
            rec.setdefault("path", essential_orion_entry["path"])  # type: ignore[index]
            rec.setdefault("alignment", essential_orion_entry["alignment"])  # type: ignore[index]
    if not found and isinstance(data, list):
        data.append(essential_orion_entry)

    # Write v8 manifest
    _write_json(v8p, data)
    act = {
        "ts": _iso(),
        "action": "register",
        "federation": federation or "unknown",
        "manifest_v8": str(v8p.relative_to(PROJECT_ROOT)),
        "ok": True,
    }
    _write_json(AUDITS_DIR / "orion_activation.json", act)
    _append_bus({"agent": "Orion", "type": "register", "status": "ok", "federation": federation or "unknown"})
    print(json.dumps(act, indent=2))
    return act


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Orion Bootstrap (headless)")
    parser.add_argument("--dry-run", action="store_true", help="Run a single scan iteration and exit")
    parser.add_argument("--verify-access", action="store_true", help="Verify Orion filesystem access and write audit record")
    parser.add_argument("--register", action="store_true", help="Register Orion in federation manifest v8")
    parser.add_argument("--federation", type=str, default=None, help="Federation label (e.g., genesis)")
    args = parser.parse_args(argv or sys.argv[1:])

    if args.verify_access:
        verify_access()
        return 0
    if args.register:
        register_federation(args.federation)
        return 0

    run_loop(dry_run=bool(args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
