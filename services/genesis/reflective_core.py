from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Repo-root resolution
PROJECT_ROOT = Path(__file__).resolve()
while PROJECT_ROOT.name != "agent-factory" and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent

LOGS_DIR = PROJECT_ROOT / "logs"
GOVERNANCE_DIR = PROJECT_ROOT / "governance"
KB_DIR = PROJECT_ROOT / "knowledge_base"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
GOVERNANCE_DIR.mkdir(parents=True, exist_ok=True)
KB_DIR.mkdir(parents=True, exist_ok=True)

GENESIS_LOG = LOGS_DIR / "genesis_orchestration.jsonl"
GENESIS_AUDIT = GOVERNANCE_DIR / "genesis_audit.jsonl"
GENESIS_LEARNING = KB_DIR / "genesis_learning.jsonl"
CONFIG_PATH = PROJECT_ROOT / "config" / "genesis_config.yaml"


_reflective_thread: Optional[threading.Thread] = None
_reflective_stop = threading.Event()
_counter = 0


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def _load_config() -> Dict[str, Any]:
    """Best-effort YAML loader; falls back to defaults if unavailable or invalid."""
    try:
        if CONFIG_PATH.exists():
            try:
                import yaml  # type: ignore
                data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
                return data
            except Exception:
                # try JSON subset
                try:
                    import json as _json
                    return _json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
                except Exception:
                    pass
    except Exception:
        pass
    # Defaults
    return {
        "reflection": {"enabled": True, "interval_s": 60},
    }


def _reflective_loop(interval_s: int) -> None:
    global _counter
    # Online events
    _append_jsonl(GENESIS_LOG, {
        "ok": True,
        "data": {"event": "ReflectiveCore Online"},
        "error": None,
        "meta": {"ts": _iso_now(), "component": "reflective_core"},
    })
    _append_jsonl(GENESIS_AUDIT, {"ts": _iso_now(), "event": "reflective_core_online", "status": "active"})
    while not _reflective_stop.is_set():
        _counter += 1
        # orchestration log
        _append_jsonl(GENESIS_LOG, {
            "ok": True,
            "data": {"tick": _counter},
            "error": None,
            "meta": {"ts": _iso_now(), "component": "reflective_core", "action": "tick"},
        })
        # learning log (append-only JSONL)
        _append_jsonl(GENESIS_LEARNING, {
            "ts": _iso_now(),
            "reflective_tick": _counter,
            "note": "Periodic reflection heartbeat.",
        })
        # sleep
        stop = _reflective_stop.wait(timeout=max(1, int(interval_s)))
        if stop:
            break
    # offline event
    _append_jsonl(GENESIS_LOG, {
        "ok": True,
        "data": {"event": "ReflectiveCore Offline"},
        "error": None,
        "meta": {"ts": _iso_now(), "component": "reflective_core"},
    })


def start_daemon(interval_s: Optional[int] = None) -> Dict[str, Any]:
    """Start the reflective core daemon in a background thread (idempotent)."""
    global _reflective_thread
    if _reflective_thread and _reflective_thread.is_alive():
        return {"ok": True, "data": {"status": "already_running"}, "error": None, "meta": {"ts": _iso_now()}}
    conf = _load_config()
    enabled = bool(((conf.get("reflection") or {}).get("enabled", True)))
    if not enabled:
        return {"ok": True, "data": {"status": "disabled"}, "error": None, "meta": {"ts": _iso_now()}}
    iv = int(interval_s or (conf.get("reflection") or {}).get("interval_s", 60))
    _reflective_stop.clear()
    _reflective_thread = threading.Thread(target=_reflective_loop, args=(iv,), daemon=True)
    _reflective_thread.start()
    return {"ok": True, "data": {"status": "started", "interval_s": iv}, "error": None, "meta": {"ts": _iso_now()}}


def stop_daemon() -> None:
    _reflective_stop.set()
    t = _reflective_thread
    if t and t.is_alive():
        try:
            t.join(timeout=2.0)
        except Exception:
            pass
