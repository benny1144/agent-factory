from __future__ import annotations

"""Governance Compliance Kernel CLI

Adds a CLI to snapshot current build state and archive required artifacts.
This file intentionally lives under governance/ to satisfy operator commands
(e.g., `python governance/compliance_kernel.py --snapshot <path>`), while
reusing shared logging and path helpers.
"""

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

from tools.logging_utils import JsonlLogger
from utils.paths import (
    PROJECT_ROOT,
    LOGS_DIR,
    TASKS_COMPLETE_DIR,
    POLICIES_DIR,
)

ARCHIVES_DIR = PROJECT_ROOT / "archives" / "factory_v7_final"
ARCHIVE_POLICIES = ARCHIVES_DIR / "policies"
ARCHIVE_LOGS = ARCHIVES_DIR / "logs"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _copy_if_exists(src: Path, dest: Path) -> bool:
    try:
        if src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return True
        if src.is_dir():
            # copytree requires dest not exist
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
            return True
    except Exception:
        return False
    return False


def build_snapshot() -> Dict[str, Any]:
    """Create an in-memory snapshot summary of relevant state."""
    def list_files(base: Path, max_n: int = 2000) -> List[str]:
        if not base.exists():
            return []
        items: List[str] = []
        for p in base.rglob("*"):
            try:
                rel = p.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
            except Exception:
                rel = str(p)
            items.append(rel)
            if len(items) >= max_n:
                break
        return items

    snapshot = {
        "ts": _iso(),
        "version": "v7_final",
        "paths": {
            "policies_dir": str(POLICIES_DIR),
            "logs_dir": str(LOGS_DIR),
            "tasks_complete_dir": str(TASKS_COMPLETE_DIR),
        },
        "contents": {
            "policies": list_files(POLICIES_DIR),
            "logs": [
                "logs/junie_execution.jsonl",
                "logs/junie_issues.jsonl",
                "logs/meta_heartbeat.jsonl",
                "logs/control_plane_activity.jsonl",
            ],
            "tasks_complete": list_files(TASKS_COMPLETE_DIR),
        },
    }
    return snapshot


def write_snapshot(snapshot_path: Path) -> Dict[str, Any]:
    snap = build_snapshot()
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    return snap


def archive_state(snapshot_path: Path) -> Dict[str, Any]:
    _ensure_dir(ARCHIVES_DIR)
    copied: Dict[str, Any] = {"policies": False, "logs": [], "snapshot": False}

    # policies -> /archives/factory_v7_final/policies/
    if POLICIES_DIR.exists():
        copied["policies"] = _copy_if_exists(POLICIES_DIR, ARCHIVE_POLICIES)

    # logs -> selective copy
    _ensure_dir(ARCHIVE_LOGS)
    for name in [
        "junie_execution.jsonl",
        "junie_issues.jsonl",
        "meta_heartbeat.jsonl",
        "control_plane_activity.jsonl",
    ]:
        src = LOGS_DIR / name
        if src.exists():
            dest = ARCHIVE_LOGS / name
            if _copy_if_exists(src, dest):
                copied["logs"].append(name)

    # snapshot -> archives root
    dest_snapshot = ARCHIVES_DIR / snapshot_path.name
    copied["snapshot"] = _copy_if_exists(snapshot_path, dest_snapshot)

    return copied


def _activate_watchtower() -> dict:
    """Activate Watchtower telemetry stream by writing an ACTIVE marker.

    Creates logs/governance/orion_audit.jsonl and appends an ACTIVE line.
    Also mirrors a human-readable line into logs/orion_activity.jsonl so that
    Watchtower log viewers can display the activation message.
    """
    gov_logs = LOGS_DIR / "governance"
    gov_logs.mkdir(parents=True, exist_ok=True)
    audit = gov_logs / "orion_audit.jsonl"
    payload = {
        "ts": _iso(),
        "component": "watchtower",
        "telemetry": "ACTIVE",
    }
    try:
        with audit.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # Mirror a readable line to orion activity log used by Watchtower API
    try:
        orion_log = LOGS_DIR / "orion_activity.jsonl"
        with orion_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"timestamp": _iso(), "agent": "Orion", "event": "Telemetry Stream: ACTIVE"}, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return {"ok": True, "audit_path": str(audit)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compliance Kernel — Snapshot, Archive, and Activation")
    parser.add_argument("--snapshot", type=str, help="Path to write final snapshot JSON")
    parser.add_argument("--activate-watchtower", action="store_true", help="Activate Watchtower telemetry and write audit log")
    args = parser.parse_args(argv)

    logger = JsonlLogger()

    if args.activate_watchtower:
        res = _activate_watchtower()
        logger.log(True, {"event": "watchtower_telemetry_activated", **res})
        print("Telemetry Stream: ACTIVE")
        # If no further args, exit early
        if not args.snapshot:
            return 0

    if not args.snapshot:
        parser.print_help()
        return 0

    snap_path = Path(args.snapshot)
    # Allow relative paths under governance/
    if not snap_path.is_absolute():
        snap_path = (PROJECT_ROOT / snap_path).resolve()

    snap = write_snapshot(snap_path)
    logger.log(True, {"event": "v7_final_snapshot_written", "path": str(snap_path)})

    copied = archive_state(snap_path)
    logger.log(True, {"event": "v7_final_archived", "archive_dir": str(ARCHIVES_DIR), "copied": copied})

    print(f"Snapshot written to {snap_path}")
    print(f"Archive prepared at {ARCHIVES_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
