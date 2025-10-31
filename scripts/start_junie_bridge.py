from __future__ import annotations
from threading import Thread
from flask import Flask, jsonify

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

# Repo-safe path resolution
try:
    from utils.paths import PROJECT_ROOT
except Exception:
    PROJECT_ROOT = Path(__file__).resolve()
    while PROJECT_ROOT.name != "agent-factory" and PROJECT_ROOT.parent != PROJECT_ROOT:
        PROJECT_ROOT = PROJECT_ROOT.parent

LOGS_DIR = PROJECT_ROOT / "logs"
TASKS_DIR = PROJECT_ROOT / "tasks"
FROM_EXPERT_DIR = TASKS_DIR / "from_expert"
TO_EXPERT_DIR = TASKS_DIR / "to_expert"
GOV_AUDIT = PROJECT_ROOT / "governance" / "federation_audit.jsonl"
CONTROL_PLANE = LOGS_DIR / "control_plane_activity.jsonl"
MANIFEST = PROJECT_ROOT / "federation" / "context_manifest.json"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_stamp() -> str:
    # Windows-safe timestamp (no colons)
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        # best-effort logging
        pass


def _repo_rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
    except Exception:
        return p.as_posix()


def _canonical_agent(agent: str) -> str:
    a = (agent or "").strip()
    if a.lower() in {"expert", "agentfactoryexpert", "agent_factory_expert"}:
        return "AgentFactoryExpert"
    if a.lower() == "archy":
        return "Archy"
    if a.lower() == "genesis":
        return "Genesis"
    return a or "AgentFactoryExpert"


@dataclass
class BridgeConfig:
    federation_on: bool = True
    agent: str = "AgentFactoryExpert"
    poll_interval_s: float = 1.5
    heartbeat_interval_s: float = 30.0


class JunieBridge:
    def __init__(self, cfg: BridgeConfig):
        self.cfg = cfg
        self._processed: Set[str] = set()
        # Ensure dirs
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        FROM_EXPERT_DIR.mkdir(parents=True, exist_ok=True)
        TO_EXPERT_DIR.mkdir(parents=True, exist_ok=True)
        GOV_AUDIT.parent.mkdir(parents=True, exist_ok=True)

    def _log_cp(self, event: str, data: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        rec = {
            "ts": _iso_now(),
            "event": event,
            "agent": self.cfg.agent,
            "ok": error is None,
            "data": data or {},
            "error": error,
            "source": "junie_bridge",
        }
        _append_jsonl(CONTROL_PLANE, rec)

    def _audit(self, origin: str, target: str, typ: str, status: str, extra: Optional[Dict[str, Any]] = None) -> None:
        rec = {
            "timestamp": _iso_now(),
            "origin": origin,
            "target": target,
            "type": typ,
            "status": status,
            "bridge_agent": self.cfg.agent,
        }
        if extra:
            rec.update(extra)
        _append_jsonl(GOV_AUDIT, rec)

    def _manifest_check(self) -> None:
        present = MANIFEST.exists()
        agents: list[str] = []
        try:
            if present:
                obj = json.loads(MANIFEST.read_text(encoding="utf-8"))
                agents = list(obj.get("agents") or [])
        except Exception:
            pass
        self._log_cp(
            "manifest_check",
            {
                "manifest": _repo_rel(MANIFEST),
                "present": present,
                "includes_agent": self.cfg.agent in agents,
                "agents": agents,
            },
        )

    def start(self) -> None:
        self._manifest_check()
        self._log_cp(
            "Bridge Online",
            {
                "federation": "on" if self.cfg.federation_on else "off",
                "from_dir": _repo_rel(FROM_EXPERT_DIR),
                "to_dir": _repo_rel(TO_EXPERT_DIR),
            },
        )
        # Verbose console banner for operators
        print(f"[Federation Active] Agent '{self.cfg.agent}' registered. Listening for /tasks/from_expert/...")

    def _handle_ping(self, payload: Dict[str, Any], src_file: Path) -> None:
        origin = str(payload.get("origin") or "")
        target = str(payload.get("target") or "")
        typ = str(payload.get("type") or "")
        ts_iso = _iso_now()
        stamp = _safe_stamp()
        # Response file name expected pattern: Archy_Response_<timestamp>.json
        name_target = target or "Unknown"
        resp_path = TO_EXPERT_DIR / f"{name_target}_Response_{stamp}.json"
        response = {
            "ok": True,
            "reply": "pong",
            "origin": origin,
            "target": target,
            "ts": ts_iso,
            "meta": {
                "source": "junie_bridge",
                "request_file": _repo_rel(src_file),
            },
        }
        resp_path.write_text(json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8")
        self._audit(origin=origin, target=target, typ=typ, status="ok")
        self._log_cp("processed", {"type": typ, "origin": origin, "target": target, "response_file": _repo_rel(resp_path)})

    def _process_file(self, p: Path) -> None:
        key = f"{p.name}:{p.stat().st_mtime_ns}"
        if key in self._processed:
            return
        try:
            text = p.read_text(encoding="utf-8")
            obj = json.loads(text)
        except Exception as e:
            self._log_cp("error", {"file": _repo_rel(p)}, error=f"invalid_json: {e}")
            self._processed.add(key)
            return
        typ = str(obj.get("type") or "")
        if typ == "ping":
            try:
                self._handle_ping(obj, p)
            except Exception as e:
                self._log_cp("error", {"file": _repo_rel(p), "type": typ}, error=str(e))
        else:
            self._log_cp("ignored", {"file": _repo_rel(p), "type": typ})
        self._processed.add(key)

    def run_loop(self) -> None:
        # Heartbeat timer
        last_hb = 0.0
        while True:
            try:
                now = time.time()
                if now - last_hb >= self.cfg.heartbeat_interval_s:
                    self._log_cp("heartbeat", {"alive": True})
                    last_hb = now
                # Scan for new files
                for p in sorted(FROM_EXPERT_DIR.glob("*.json")):
                    if p.is_file():
                        self._process_file(p)
                time.sleep(self.cfg.poll_interval_s)
            except KeyboardInterrupt:
                print("\nBridge shutting down...")
                self._log_cp("Bridge Offline", {"status": "stopped", "reason": "KeyboardInterrupt"})
                break
            except Exception as e:
                # Non-fatal; keep the loop alive
                self._log_cp("error", {"where": "run_loop"}, error=str(e))
                time.sleep(max(1.0, self.cfg.poll_interval_s))


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Junie Federation Bridge Daemon")
    parser.add_argument("--federation", choices=["on", "off"], default="on", help="Enable federation mode")
    parser.add_argument("--agent", choices=["Expert", "Archy", "Genesis"], default="Expert", help="Bridge agent identity")
    parser.add_argument("--poll", type=float, default=1.5, help="Polling interval seconds")
    parser.add_argument("--heartbeat", type=float, default=30.0, help="Heartbeat interval seconds")
    return parser.parse_args(argv)

def start_http_health(port: int = 5050):
    """Lightweight background HTTP server for health checks."""
    app = Flask("JunieBridgeHealth")

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "bridge": "AgentFactoryExpert"}), 200

    @app.route("/")
    def index():
        return "Junie Bridge active", 200

    t = Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    )
    t.daemon = True
    t.start()

def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    agent = _canonical_agent(args.agent)
    cfg = BridgeConfig(
        federation_on=(args.federation == "on"),
        agent=agent,
        poll_interval_s=float(args.poll),
        heartbeat_interval_s=float(args.heartbeat),
    )
    bridge = JunieBridge(cfg)
    # 🚀 start health HTTP server
    start_http_health(port=5050)

    bridge.start()
    bridge.run_loop()
    return 0



if __name__ == "__main__":
    raise SystemExit(main())
