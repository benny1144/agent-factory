from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Repo-root safe resolution
try:
    from utils.paths import PROJECT_ROOT as _PR
    PROJECT_ROOT: Path = _PR
except Exception:
    PROJECT_ROOT = Path(__file__).resolve()
    while PROJECT_ROOT.name != "agent-factory" and PROJECT_ROOT.parent != PROJECT_ROOT:
        PROJECT_ROOT = PROJECT_ROOT.parent

LOGS_DIR = PROJECT_ROOT / "logs"
GOV_DIR = PROJECT_ROOT / "governance"
TASKS_DIR = PROJECT_ROOT / "tasks"
FROM_DIR = TASKS_DIR / "from_expert"
TO_DIR = TASKS_DIR / "to_expert"
CONTROL_PLANE = LOGS_DIR / "control_plane_activity.jsonl"
GOV_AUDIT = GOV_DIR / "federation_audit.jsonl"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_stamp() -> str:
    # Windows-safe timestamp (no colons)
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        # best-effort logging; never raise
        pass


def _repo_rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return p.as_posix()


def _log_cp(event: str, agent: str, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
    _append_jsonl(CONTROL_PLANE, {
        "ts": _iso_now(),
        "event": event,
        "agent": agent,
        "ok": error is None,
        "data": data or {},
        "error": error,
        "source": "juno_listener",
    })


def _audit(origin: str, target: str, typ: str, status: str, agent: str, extra: Optional[Dict[str, Any]] = None) -> None:
    rec: Dict[str, Any] = {
        "timestamp": _iso_now(),
        "origin": origin,
        "target": target,
        "type": typ,
        "status": status,
        "bridge_agent": agent,
    }
    if extra:
        rec.update(extra)
    _append_jsonl(GOV_AUDIT, rec)


def _whitelist() -> Dict[str, Optional[List[str]]]:
    py = sys.executable or "python"
    return {
        # quick unit tests
        "pytest -q": [py, "-m", "pytest", "-q"],
        # autogen bridge smoke
        "python -m services.autogen.bridge --test": [py, "-m", "services.autogen.bridge", "--test"],
        # knowledge indexer scan
        "python utils/knowledge_indexer.py --scan": [py, "utils/knowledge_indexer.py", "--scan"],
        # noop action
        "noop": None,
    }


def _run_exec(cmd: str, timeout_s: int = 120) -> Tuple[int, str, str]:
    wl = _whitelist()
    if cmd not in wl:
        return 9001, "", f"command_not_allowed: {cmd}"
    if cmd == "noop" or wl[cmd] is None:
        return 0, "noop-ok", ""
    args = wl[cmd] or []
    try:
        proc = subprocess.run(
            args,
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_s,
            shell=False,
        )
        return proc.returncode, proc.stdout[-8000:] if proc.stdout else "", proc.stderr[-8000:] if proc.stderr else ""
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:
        return 1, "", f"exec_error: {type(e).__name__}: {e}"


def _write_response(agent: str, payload: Dict[str, Any]) -> Path:
    TO_DIR.mkdir(parents=True, exist_ok=True)
    out = TO_DIR / f"{agent}_Response_{_safe_stamp()}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def federation_listener(agent_name: str = "Juno") -> None:
    # Ensure directories
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    GOV_DIR.mkdir(parents=True, exist_ok=True)
    FROM_DIR.mkdir(parents=True, exist_ok=True)
    TO_DIR.mkdir(parents=True, exist_ok=True)

    # Online logs
    _log_cp("Agent Listener Online", agent_name, {"from_dir": _repo_rel(FROM_DIR), "to_dir": _repo_rel(TO_DIR)})
    _audit(agent=agent_name, origin="system", target=agent_name, typ="online", status="active", extra={"scope": "agent_listener"})

    print(f"[{agent_name}] Federation listener active → {FROM_DIR.as_posix()}")

    while True:
        try:
            for task_file in sorted(FROM_DIR.glob("*.json")):
                if not task_file.is_file():
                    continue
                try:
                    text = task_file.read_text(encoding="utf-8")
                    data = json.loads(text)
                except Exception as e:
                    _log_cp("error", agent_name, {"file": _repo_rel(task_file)}, error=f"invalid_json: {e}")
                    # mark as processed by renaming or deleting (best-effort)
                    try:
                        task_file.unlink()
                    except Exception:
                        pass
                    continue

                origin = str(data.get("origin") or "")
                target = str(data.get("target") or "")
                typ = str(data.get("type") or "")
                if target != agent_name:
                    # not for Juno
                    continue

                # Process directive
                reply_payload: Dict[str, Any]
                if typ == "ping":
                    reply_payload = {
                        "ok": True,
                        "reply": "pong",
                        "agent": agent_name,
                        "origin": origin,
                        "target": target,
                        "ts": _iso_now(),
                        "meta": {"source": "juno_listener", "request_file": _repo_rel(task_file)},
                    }
                    out = _write_response(agent_name, reply_payload)
                    _log_cp("processed", agent_name, {"type": typ, "origin": origin, "target": target, "response_file": _repo_rel(out)})
                    _audit(origin=origin, target=target, typ=typ, status="ok", agent=agent_name)
                elif typ == "connectivity-test-004":
                    reply_payload = {
                        "ok": True,
                        "reply": "online",
                        "agent": agent_name,
                        "origin": origin,
                        "target": target,
                        "ts": _iso_now(),
                        "meta": {"source": "juno_listener", "request_file": _repo_rel(task_file), "test": typ},
                    }
                    out = _write_response(agent_name, reply_payload)
                    _log_cp("processed", agent_name, {"type": typ, "origin": origin, "target": target, "response_file": _repo_rel(out)})
                    _audit(origin=origin, target=target, typ=typ, status="ok", agent=agent_name)
                elif typ == "exec":
                    cmd = str(data.get("cmd") or "").strip()
                    _log_cp("exec_start", agent_name, {"cmd": cmd, "origin": origin})
                    code, stdout, stderr = _run_exec(cmd)
                    reply_payload = {
                        "ok": code == 0,
                        "reply": "exec_done",
                        "agent": agent_name,
                        "origin": origin,
                        "target": target,
                        "ts": _iso_now(),
                        "data": {"cmd": cmd, "exit_code": code, "stdout": stdout, "stderr": stderr},
                        "meta": {"source": "juno_listener", "request_file": _repo_rel(task_file)},
                    }
                    out = _write_response(agent_name, reply_payload)
                    _log_cp("exec_done", agent_name, {"cmd": cmd, "exit_code": code, "response_file": _repo_rel(out)})
                    _audit(origin=origin, target=target, typ=typ, status=("ok" if code == 0 else "error"), agent=agent_name)
                else:
                    reply_payload = {
                        "ok": False,
                        "reply": "unsupported_type",
                        "agent": agent_name,
                        "origin": origin,
                        "target": target,
                        "ts": _iso_now(),
                        "error": f"unsupported_type: {typ}",
                        "meta": {"source": "juno_listener", "request_file": _repo_rel(task_file)},
                    }
                    out = _write_response(agent_name, reply_payload)
                    _log_cp("ignored", agent_name, {"type": typ, "origin": origin, "response_file": _repo_rel(out)})
                    _audit(origin=origin, target=target, typ=typ, status="ignored", agent=agent_name)
                # best-effort cleanup
                try:
                    task_file.unlink()
                except Exception:
                    pass
        except KeyboardInterrupt:
            _log_cp("Agent Listener Offline", agent_name, {"reason": "KeyboardInterrupt"})
            break
        except Exception as e:
            _log_cp("error", agent_name, {"where": "run_loop"}, error=str(e))
            time.sleep(1.0)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Juno — Autonomous Implementation Agent (federation listener)")
    parser.add_argument("--mode", default="federation", help="Run mode: federation")
    args = parser.parse_args(argv)
    if args.mode != "federation":
        print("Juno only supports --mode federation at this time.")
        return 2
    federation_listener("Juno")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
