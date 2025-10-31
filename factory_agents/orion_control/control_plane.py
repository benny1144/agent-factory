from __future__ import annotations

import json
import time
import pathlib
from typing import Any, Dict

from .repo_auditor import RepoAuditor
from .governance_monitor import GovernanceMonitor
from .federation_interface import FederationInterface


class OrionControlPlane:
    """Core Orion control loop.

    Periodically audits repository structure and governance manifest,
    logging results to logs/compliance/orion_activity.jsonl and
    announcing presence to Watchtower chat log.
    """

    def __init__(self) -> None:
        self.repo_root = pathlib.Path(__file__).resolve().parents[2]
        self.logs_dir = self.repo_root / "logs" / "compliance"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.activity_log = self.logs_dir / "orion_activity.jsonl"
        self.repo_auditor = RepoAuditor(self.repo_root)
        self.governance_monitor = GovernanceMonitor(self.repo_root)
        self.interface = FederationInterface(self.repo_root)

    def _log(self, msg: str, **fields: Any) -> None:
        entry: Dict[str, Any] = {"timestamp": time.time(), "agent": "Orion", "event": msg}
        if fields:
            entry.update(fields)
        with self.activity_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def initialize(self) -> None:
        self._log("Orion initialized and attached to Federation.")
        try:
            self.interface.announce_online()
        except Exception as e:  # best-effort
            self._log("interface_error", error=str(e))

    def run_forever(self) -> None:
        # Simple hourly loop
        while True:
            try:
                audit = self.repo_auditor.audit_structure()
                self._log("repo_audit", **{"orphans": len(audit.get("orphans", [])), "nonstandard": len(audit.get("nonstandard", []))})
            except Exception as e:
                self._log("repo_audit_error", error=str(e))
            try:
                self.governance_monitor.check_drift()
            except Exception as e:
                self._log("governance_monitor_error", error=str(e))
            time.sleep(3600)
