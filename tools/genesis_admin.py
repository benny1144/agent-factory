from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure repo root + src on path
import tools.startup  # noqa: F401

# Optional audit logger (best-effort)
try:
    from agent_factory.services.audit.audit_logger import log_event  # type: ignore
except Exception:  # pragma: no cover
    def log_event(event_type: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:  # type: ignore
        return {"ok": True, "data": {"event_type": event_type, "metadata": metadata or {}}}

# Import Genesis interface
try:
    from factory_agents.architect_genesis.main import GenesisOrchestrator  # type: ignore
except Exception as e:  # pragma: no cover
    # Provide a helpful error if import fails (e.g., crewai not installed)
    raise SystemExit(
        f"[ERROR] Could not import GenesisOrchestrator from factory_agents.architect_genesis.main: {e}\n"
        "Ensure repository paths are correct and required dependencies for Genesis are installed."
    )

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPLIANCE_DIR = REPO_ROOT / "compliance" / "audit_log"
COMPLIANCE_DIR.mkdir(parents=True, exist_ok=True)
ADMIN_CSV = COMPLIANCE_DIR / "genesis_admin_activity.csv"
if not ADMIN_CSV.exists():
    ADMIN_CSV.write_text("ts,action,outcome,details\n", encoding="utf-8")

FIREWALL_YAML = REPO_ROOT / "config" / "human_firewall.yaml"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_yaml_flag(path: Path, key: str, default: bool = False) -> bool:
    if not path.exists():
        return default
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        val = data.get(key)
        return str(val).lower() == "true"
    except Exception:
        # Fallback naive parse
        try:
            txt = path.read_text(encoding="utf-8").lower()
            # Find a line like "allow_genesis_reactivation: true"
            return f"{key.lower()}: true" in txt
        except Exception:
            return default


def _append_admin_audit(action: str, outcome: str, details: Dict[str, Any]) -> None:
    row = {
        "ts": _now(),
        "action": action,
        "outcome": outcome,
        "details": json.dumps(details, ensure_ascii=False),
    }
    with ADMIN_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ts", "action", "outcome", "details"])
        w.writerow(row)
    try:
        log_event("genesis_admin", {"action": action, "outcome": outcome, **details})
    except Exception:
        pass


def cmd_status(orch: GenesisOrchestrator) -> int:
    st = orch.get_status()
    print(json.dumps(st, indent=2))
    _append_admin_audit("status", "ok", st)
    return 0


def cmd_ping(orch: GenesisOrchestrator) -> int:
    # For now, treat ping as status check + reachable flag
    st = orch.get_status()
    resp = {"reachable": True, "status": st}
    print(json.dumps(resp, indent=2))
    _append_admin_audit("ping", "ok", resp)
    return 0


def cmd_reactivate(orch: GenesisOrchestrator, mode: Optional[str], listen_port: Optional[int]) -> int:
    allowed = _read_yaml_flag(FIREWALL_YAML, "allow_genesis_reactivation", default=False)
    if not allowed:
        msg = {
            "error": "reactivation_blocked",
            "reason": "allow_genesis_reactivation flag not true in config/human_firewall.yaml",
        }
        print(json.dumps(msg, indent=2))
        _append_admin_audit("reactivate", "blocked", msg)
        return 2
    mode = (mode or "architect_mode").strip()
    try:
        res = orch.reactivate(mode, listen_port=listen_port)
        print(json.dumps(res, indent=2))
        details = dict(res)
        if listen_port:
            details["requested_listen_port"] = listen_port
        _append_admin_audit("reactivate", "ok", details)
        return 0
    except Exception as e:
        err = {"error": "reactivate_failed", "detail": str(e), "requested_listen_port": listen_port}
        print(json.dumps(err, indent=2))
        _append_admin_audit("reactivate", "error", err)
        return 1


def cmd_shutdown(orch: GenesisOrchestrator) -> int:
    try:
        res = orch.shutdown()
        print(json.dumps(res, indent=2))
        _append_admin_audit("shutdown", "ok", res)
        return 0
    except Exception as e:
        err = {"error": "shutdown_failed", "detail": str(e)}
        print(json.dumps(err, indent=2))
        _append_admin_audit("shutdown", "error", err)
        return 1


def cmd_logs(orch: GenesisOrchestrator) -> int:
    try:
        lines = orch.tail_logs(20)
        if isinstance(lines, list):
            for ln in lines:
                print(ln.rstrip("\n"))
        else:
            print(str(lines))
        _append_admin_audit("logs", "ok", {"lines": len(lines) if isinstance(lines, list) else 0})
        return 0
    except Exception as e:
        err = {"error": "logs_failed", "detail": str(e)}
        print(json.dumps(err, indent=2))
        _append_admin_audit("logs", "error", err)
        return 1


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Genesis Admin Interface Tool")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--status", action="store_true", help="Print current Genesis operational state")
    g.add_argument("--reactivate", nargs="?", const="architect_mode", help='Reactivate Genesis with mode ("architect_mode" or "observer_mode")')
    g.add_argument("--shutdown", action="store_true", help="Gracefully stop Genesis orchestrator")
    g.add_argument("--ping", action="store_true", help="Test connection to Genesis process/API")
    g.add_argument("--logs", action="store_true", help="Show last 20 lines of genesis session log")
    # Optional listener port when reactivating
    p.add_argument("--listen", type=int, default=None, help="Start Genesis intake listener on the given port (e.g., 5055) after reactivation")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    orch = GenesisOrchestrator()
    if args.status:
        raise SystemExit(cmd_status(orch))
    if args.ping:
        raise SystemExit(cmd_ping(orch))
    if args.shutdown:
        raise SystemExit(cmd_shutdown(orch))
    if isinstance(args.reactivate, str) or args.reactivate is not None:
        raise SystemExit(cmd_reactivate(orch, args.reactivate, args.listen))
    if args.logs:
        raise SystemExit(cmd_logs(orch))


if __name__ == "__main__":
    main()
