from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from tools.logging_utils import JsonlLogger
from utils.paths import PROJECT_ROOT, LOGS_DIR
from artisan_engine.policy import is_allowed

TASKS_FROM = PROJECT_ROOT / "tasks" / "from_orion"
TASKS_TO = PROJECT_ROOT / "tasks" / "to_orion"
PENDING_DIR = PROJECT_ROOT / "tasks" / "pending_human"
LOG_PATH = LOGS_DIR / "artisan_activity.jsonl"
EVENT_BUS = PROJECT_ROOT / "governance" / "event_bus.jsonl"

logger = JsonlLogger(log_file=LOG_PATH)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: Dict[str, Any]) -> None:
    logger.log(True, {"ts": _iso(), **msg})
    # Mirror critical events to governance event bus
    try:
        EVENT_BUS.parent.mkdir(parents=True, exist_ok=True)
        with EVENT_BUS.open("a", encoding="utf-8") as f:
            # Map some known events to standardized governance event types
            evt_type = msg.get("event")
            gov = None
            if evt_type in {"artisan_start", "artisan_stop", "task_success", "task_failed", "task_blocked"}:
                import uuid as _uuid
                agent = "Artisan"
                status = "ok"
                if evt_type in {"task_failed"}:
                    status = "error"
                elif evt_type in {"task_blocked"}:
                    status = "blocked"
                gov = {"ts": _iso(), "agent": agent, "type": evt_type, "status": status, "trace_id": _uuid.uuid4().hex}
            if gov:
                f.write(json.dumps(gov, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _ensure_dirs() -> None:
    TASKS_FROM.mkdir(parents=True, exist_ok=True)
    TASKS_TO.mkdir(parents=True, exist_ok=True)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def execute_task(task_file: Path) -> None:
    try:
        data = json.loads(task_file.read_text(encoding="utf-8"))
    except Exception as e:
        log({"event": "task_parse_error", "task": task_file.name, "error": str(e)})
        return

    command = data.get("command")
    task_id = task_file.stem
    approved_marker = PENDING_DIR / f"{task_id}.approved"
    awaiting_path = PENDING_DIR / f"{task_id}.awaiting"

    if not command:
        log({"event": "task_no_command", "task": task_file.name})
        # Archive anyway so Orion queue drains predictably
        try:
            dest = TASKS_TO / f"{task_file.name}.done"
            os.replace(str(task_file), str(dest))
            log({"event": "task_archived", "dest": dest.name})
        except Exception as e:
            log({"event": "archive_error", "task": task_file.name, "error": str(e)})
        return

    allowed = is_allowed(str(command))
    approved = approved_marker.exists()

    if not allowed and not approved:
        # Move to pending human approval
        try:
            data["blocked"] = True
            data["policy"] = "allowlist_v1.1"
            awaiting_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            log({"event": "pending_write_error", "task": task_file.name, "error": str(e)})
        # Leave the original task file in place; it will be retried when approved marker appears.
        log({"event": "task_blocked", "task": task_file.name, "command": command, "blocked": True})
        return

    # Execute (either allowed, or approved override)
    try:
        subprocess.run(str(command), shell=True, check=True)
        log({"event": "task_success", "task": task_file.name, "command": command, "approved_override": (not allowed and approved)})
    except subprocess.CalledProcessError as e:
        log({"event": "task_failed", "task": task_file.name, "command": command, "error": str(e)})

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
        log({"event": "task_archived", "dest": dest.name})
    except Exception as e:
        log({"event": "archive_error", "task": task_file.name, "error": str(e)})


def main() -> int:
    _ensure_dirs()
    log({"event": "artisan_start", "watch_dir": str(TASKS_FROM.relative_to(PROJECT_ROOT))})
    while True:
        try:
            for file in sorted(TASKS_FROM.glob("*.json")):
                if file.is_file():
                    execute_task(file)
            time.sleep(10)
        except KeyboardInterrupt:
            log({"event": "artisan_stop", "reason": "KeyboardInterrupt"})
            break
        except Exception as e:
            log({"event": "loop_error", "error": str(e)})
            time.sleep(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
