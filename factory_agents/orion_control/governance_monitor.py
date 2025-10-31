from __future__ import annotations

import json
import pathlib
from typing import Dict, List


class GovernanceMonitor:
    """Reads federation manifest v7.5 and reports missing required fields per agent.

    Output written to governance/audits/governance_drift.json with a mapping:
    { "AgentName": ["missing_field_a", ...], ... }
    """

    REQUIRED = ["role", "version", "alignment"]

    def __init__(self, repo_root: pathlib.Path) -> None:
        self.repo_root = pathlib.Path(repo_root)
        self.manifest = self.repo_root / "governance" / "federation_manifest_v7_5.json"
        self.report_file = self.repo_root / "governance" / "audits" / "governance_drift.json"
        self.report_file.parent.mkdir(parents=True, exist_ok=True)

    def check_drift(self) -> Dict[str, List[str]]:
        try:
            data = json.loads(self.manifest.read_text(encoding="utf-8"))
            result: Dict[str, List[str]] = {}
            if isinstance(data, list):
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    agent = str(entry.get("agent") or "<unknown>")
                    missing = [k for k in self.REQUIRED if k not in entry]
                    if missing:
                        result[agent] = missing
            else:
                result = {"error": ["manifest_not_list"]}  # type: ignore[assignment]
        except Exception as e:
            self.report_file.write_text(json.dumps({"error": str(e)}, indent=2), encoding="utf-8")
            return {"error": [str(e)]}  # type: ignore[return-value]

        try:
            self.report_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
        except Exception:
            pass
        return result
