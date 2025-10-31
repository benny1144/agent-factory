from __future__ import annotations

import json
import os
import pathlib
from typing import Dict, List


class RepoAuditor:
    """Scan factory_agents/* for standard layout and detect legacy orphans.

    Writes a recommendations report to governance/audits/repo_cleanup_recommendations.json.
    Also validates experimental modules listed under the Orion agent entry in
    governance/federation_manifest_v7_5.json and reports any missing paths.
    """

    def __init__(self, repo_root: pathlib.Path) -> None:
        self.repo_root = pathlib.Path(repo_root)
        self.audit_path = self.repo_root / "governance" / "audits" / "repo_cleanup_recommendations.json"
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_manifest(self) -> List[Dict]:
        path = self.repo_root / "governance" / "federation_manifest_v7_5.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _experimental_modules(self) -> List[str]:
        modules: List[str] = []
        for rec in self._read_manifest():
            try:
                if rec.get("agent") == "Orion":
                    for m in rec.get("experimental_modules", []) or []:
                        p = str(m.get("path", "")).strip()
                        if p:
                            modules.append(p)
            except Exception:
                continue
        return modules

    def audit_structure(self) -> Dict:
        report: Dict[str, object] = {
            "timestamp": pathlib.Path(__file__).stat().st_mtime,
            "orphans": [],
            "duplicates": [],
            "nonstandard": [],
            "experimental_modules_checked": [],
            "experimental_modules_missing": [],
        }

        agent_root = self.repo_root / "factory_agents"
        seen_names: List[str] = []

        if agent_root.exists():
            for path in agent_root.iterdir():
                if not path.is_dir():
                    continue
                name = path.name
                if name in seen_names:
                    report["duplicates"].append(name)
                else:
                    seen_names.append(name)
                if not (path / "main.py").exists():
                    report["nonstandard"].append(str(path))

        # Detect stray legacy folders in repo root
        legacy_dirs = [p for p in self.repo_root.iterdir() if (p.is_dir() and ("Execs" in p.name or "Log" in p.name))]
        report["orphans"] = [str(p) for p in legacy_dirs]

        # Validate experimental modules
        exp = self._experimental_modules()
        report["experimental_modules_checked"] = exp
        missing: List[str] = []
        for rel in exp:
            p = (self.repo_root / rel.replace("/", os.sep)).resolve()
            if not p.exists():
                missing.append(rel)
        report["experimental_modules_missing"] = missing

        # write file
        try:
            self.audit_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except Exception:
            # best-effort
            pass
        return report
