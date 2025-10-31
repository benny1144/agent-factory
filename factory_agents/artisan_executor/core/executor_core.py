from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Paths
try:
    from utils.paths import PROJECT_ROOT, LOGS_DIR
except Exception:  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve()
    while PROJECT_ROOT.name != "agent-factory" and PROJECT_ROOT.parent != PROJECT_ROOT:
        PROJECT_ROOT = PROJECT_ROOT.parent
    LOGS_DIR = PROJECT_ROOT / "logs"

TASKS_FROM = PROJECT_ROOT / "tasks" / "from_orion"
TASKS_TO = PROJECT_ROOT / "tasks" / "to_orion"
PENDING_DIR = PROJECT_ROOT / "tasks" / "pending_human"
EVENT_BUS = PROJECT_ROOT / "governance" / "event_bus.jsonl"

# Canonical runtime log for Artisan (Phase 38.8)
RUNTIME_LOG_DIR = LOGS_DIR / "artisan"
RUNTIME_LOG = RUNTIME_LOG_DIR / "runtime.log"

# Compatibility JSONL activity log (kept for dashboards that tail this file)
ARTISAN_JSONL = LOGS_DIR / "artisan_activity.jsonl"

from .policy import is_allowed  # local policy under canonical path


# ---------- Utilities ---------- #

def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    for p in (TASKS_FROM, TASKS_TO, PENDING_DIR, RUNTIME_LOG_DIR, LOGS_DIR, EVENT_BUS.parent):
        p.mkdir(parents=True, exist_ok=True)


def _append_file(path: Path, line: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line)


def _write_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    try:
        _append_file(path, json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _log_runtime(event: str, **fields: Any) -> None:
    rec = {"ts": _iso(), "event": event, **fields}
    # Write primary runtime log
    _write_jsonl(RUNTIME_LOG, rec)
    # Mirror to legacy JSONL to preserve existing dashboards/metrics
    _write_jsonl(ARTISAN_JSONL, rec)


def _emit_bus(agent: str, typ: str, status: str = "ok", **fields: Any) -> None:
    payload = {"ts": _iso(), "agent": agent, "type": typ, "status": status, "trace_id": uuid.uuid4().hex}
    payload.update(fields)
    _write_jsonl(EVENT_BUS, payload)


# ---------- ModelRouter (compliance logging) ---------- #

def _router_log(task_id: str, prompt: str, risk: str = "low", phase: str = "38.8") -> None:
    """Emit a compliance-visible model_usage entry via ModelRouter.

    This does not depend on network availability; ModelRouter handles fallbacks
    and still writes compliance/event logs.
    """
    try:
        from agents.model_router import ModelRouter
        router = ModelRouter(agent_name="Artisan")
        meta = {"risk": risk, "tokens": 400, "task_id": task_id, "phase": phase}
        _ = router.route(meta, prompt)
    except Exception:
        # best-effort only
        pass


# ---------- Execution Core ---------- #

def execute_task(task_file: Path) -> None:
    try:
        data = json.loads(task_file.read_text(encoding="utf-8"))
    except Exception as e:
        _log_runtime("task_parse_error", task=task_file.name, error=f"{type(e).__name__}: {str(e)[:200]} (trace redacted)")
        return

    command = data.get("command")
    task_id = task_file.stem
    approved_marker = PENDING_DIR / f"{task_id}.approved"
    awaiting_path = PENDING_DIR / f"{task_id}.awaiting"

    if not command:
        _log_runtime("task_no_command", task=task_file.name)
        # Archive anyway so queue drains predictably
        try:
            dest = TASKS_TO / f"{task_file.name}.done"
            os.replace(str(task_file), str(dest))
            _log_runtime("task_archived", dest=dest.name)
        except Exception as e:
            _log_runtime("archive_error", task=task_file.name, error=f"{type(e).__name__}: {str(e)[:200]} (trace redacted)")
        return

    allowed = is_allowed(str(command))
    approved = approved_marker.exists()

    if not allowed and not approved:
        # Queue for human approval (HITL)
        try:
            data["blocked"] = True
            data["policy"] = "allowlist_v1.1"
            awaiting_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            _log_runtime("pending_write_error", task=task_file.name, error=f"{type(e).__name__}: {str(e)[:200]} (trace redacted)")
        _log_runtime("task_blocked", task=task_file.name, command=command, blocked=True)
        _emit_bus("Artisan", "task_blocked", status="blocked")
        _router_log(task_id, f"Blocked command pending approval: {command}")
        return

    # Execute (either allowlisted, or approved override)
    try:
        _router_log(task_id, f"Executing command: {command}")
        subprocess.run(str(command), shell=True, check=True)
        _log_runtime("task_success", task=task_file.name, command=command, approved_override=(not allowed and approved))
        _emit_bus("Artisan", "task_success", status="ok")
    except subprocess.CalledProcessError as e:
        _log_runtime("task_failed", task=task_file.name, command=command, error=f"{type(e).__name__}: {str(e)[:200]} (trace redacted)")
        _emit_bus("Artisan", "task_failed", status="error")

    # Move to done and clean up approval markers
    try:
        dest = TASKS_TO / f"{task_file.name}.done"
        os.replace(str(task_file), str(dest))
        if awaiting_path.exists():
            try:
                awaiting_path.unlink()
            except Exception:
                pass
        if approved_marker.exists():
            try:
                approved_marker.unlink()
            except Exception:
                pass
        _log_runtime("task_archived", dest=dest.name)
    except Exception as e:
        _log_runtime("archive_error", task=task_file.name, error=f"{type(e).__name__}: {str(e)[:200]} (trace redacted)")


def run_loop(poll_seconds: float = 10.0) -> None:
    _ensure_dirs()
    _log_runtime("artisan_start", watch_dir=str(TASKS_FROM.relative_to(PROJECT_ROOT)))
    _emit_bus("Artisan", "artisan_start", status="ok")
    while True:
        try:
            for file in sorted(TASKS_FROM.glob("*.json")):
                if file.is_file():
                    execute_task(file)
            time.sleep(max(1.0, float(poll_seconds)))
        except KeyboardInterrupt:
            _log_runtime("artisan_stop", reason="KeyboardInterrupt")
            _emit_bus("Artisan", "artisan_stop", status="ok")
            break
        except Exception as e:
            _log_runtime("loop_error", error=f"{type(e).__name__}: {str(e)[:200]} (trace redacted)")
            time.sleep(2)


__all__ = ["run_loop", "execute_task", "RUNTIME_LOG"]
