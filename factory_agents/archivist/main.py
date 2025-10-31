from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# Prefer repo-root safe paths
try:
    from utils.paths import PROJECT_ROOT as _PR
    PROJECT_ROOT = _PR
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Logs and audit paths
LOGS_DIR = PROJECT_ROOT / "logs"
CONTROL_PLANE = LOGS_DIR / "control_plane_activity.jsonl"
GOV_AUDIT = PROJECT_ROOT / "governance" / "federation_audit.jsonl"


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def federation_listener(agent_name: str = "Archy") -> None:
    tasks_dir = PROJECT_ROOT / "tasks" / "from_expert"
    responses_dir = PROJECT_ROOT / "tasks" / "to_expert"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)
    # Emit control-plane and governance audit log entries on startup
    _append_jsonl(CONTROL_PLANE, {
        "timestamp": _iso_now(),
        "agent": agent_name,
        "event": "Agent Listener Online",
        "status": "active",
        "source": "agent_listener"
    })
    _append_jsonl(GOV_AUDIT, {
        "timestamp": _iso_now(),
        "agent": agent_name,
        "event": "Agent Listener Online",
        "status": "active",
        "scope": "agent_listener"
    })
    print(f"[{agent_name}] Federation listener active → {tasks_dir.as_posix()}")
    while True:
        for task_file in tasks_dir.glob("*.json"):
            try:
                text = task_file.read_text(encoding="utf-8")
                data = json.loads(text)
                if str(data.get("target")) == agent_name:
                    print(f"[{agent_name}] Received task: {task_file.name}")
                    response = {
                        "agent": agent_name,
                        "received": _iso_now(),
                        "status": "ok",
                        "type": "response",
                        "task": data,
                    }
                    out = responses_dir / f"{agent_name}_Response_{int(time.time())}.json"
                    out.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
                    try:
                        task_file.unlink()
                    except Exception:
                        pass
            except Exception as e:
                print(f"[{agent_name}] Error handling {task_file.name}: {e}")
        time.sleep(2)


def run():
    print("Hello from Archy!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="normal", help="Run mode: normal|federation")
    args = parser.parse_args()
    if args.mode == "federation":
        federation_listener("Archy")
    else:
        run()
