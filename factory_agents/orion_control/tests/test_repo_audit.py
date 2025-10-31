from __future__ import annotations

import json
import pathlib

from factory_agents.orion_control.repo_auditor import RepoAuditor


def test_audit_run() -> None:
    repo = pathlib.Path(__file__).resolve().parents[3]
    auditor = RepoAuditor(repo)
    report = auditor.audit_structure()
    assert "timestamp" in report
    assert "orphans" in report
    # File should be written
    out = repo / "governance" / "audits" / "repo_cleanup_recommendations.json"
    assert out.exists(), f"Expected audit file at {out}"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
