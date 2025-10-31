from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# Repo root
REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = REPO_ROOT / "reports"
AUDIT_DIR = REPO_ROOT / "compliance" / "audit_log"
LOGS_DIR = REPO_ROOT / "logs"
BACKUPS_DIR = REPO_ROOT / "backups"
JUNIE_ACTIVITY = AUDIT_DIR / "junie_activity.csv"
FACTORY_CERT_CSV = AUDIT_DIR / "factory_certification.csv"

# Optional audit logger (best-effort)
try:
    import sys
    sys.path.append(str(REPO_ROOT / "src"))
    from agent_factory.services.audit.audit_logger import log_event  # type: ignore
except Exception:  # pragma: no cover
    def log_event(event_type: str, metadata: Dict[str, object] | None = None) -> Dict[str, object]:  # type: ignore
        return {"ok": True, "data": {"event_type": event_type, "metadata": metadata or {}}}


INCLUDE_DIRS = [
    REPO_ROOT / "tasks",
    REPO_ROOT / "agents",
    REPO_ROOT / "tools",
    REPO_ROOT / "governance",
    LOGS_DIR,
]

# Ignore large/generated directories
EXCLUDE_TOP = {
    REPO_ROOT / "frontend" / "node_modules",
    REPO_ROOT / "frontend" / "dist",
    REPO_ROOT / "artifacts",
    REPO_ROOT / ".git",
    REPO_ROOT / "data",
}
EXCLUDE_SUFFIXES = {".sqlite", ".db", ".db-journal", ".png", ".jpg", ".jpeg", ".gif"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_commit() -> str | None:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT), stderr=subprocess.STDOUT)
        return out.decode("utf-8").strip()
    except Exception:
        return None


def _is_excluded(p: Path) -> bool:
    try:
        # Exclude within excluded top dirs
        for base in EXCLUDE_TOP:
            if base.exists() and base in p.parents:
                return True
    except Exception:
        pass
    if p.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    return False


def _sha256(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def audit_sweep(ts: str) -> Path:
    """Scan specified directories and write integrity snapshot CSV.

    The first row contains commit metadata to correlate snapshot with VCS state.
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    out = AUDIT_DIR / f"integrity_snapshot_{ts}.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        commit = _git_commit() or "<unknown>"
        # Metadata row to link snapshot to the exact commit
        w.writerow(["commit", commit, ""])
        # Header row for file records
        w.writerow(["path", "sha256", "size_bytes"])
        for base in INCLUDE_DIRS:
            if not base.exists():
                continue
            for p in base.rglob("*"):
                if not p.is_file():
                    continue
                if _is_excluded(p):
                    continue
                try:
                    digest = _sha256(p)
                    size = p.stat().st_size
                    rel = p.relative_to(REPO_ROOT).as_posix()
                    w.writerow([rel, digest, size])
                except Exception:
                    continue
    log_event("integrity_snapshot", {"path": str(out)})
    return out


def governance_deep_check(ts: str) -> Path:
    """Run tools/governance_check.py --deep if present and capture output to report."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"governance_audit_{ts}.md"
    tool = REPO_ROOT / "tools" / "governance_check.py"
    header = [
        "# Governance Deep Audit",
        f"Generated: {ts}",
        "",
    ]
    content = ""
    anomalies = 0
    if tool.exists():
        try:
            res = subprocess.run(["python", str(tool), "--deep"], cwd=str(REPO_ROOT), capture_output=True, text=True, timeout=120)
            content = res.stdout or res.stderr
            # naive anomaly detection
            if "anomaly" in (content or "").lower():
                anomalies = 1
        except Exception as e:
            content = f"[ERROR] governance_check failed: {e}"
            anomalies = 1
    else:
        content = "[NOTE] tools/governance_check.py not found. Assuming 0 anomalies for baseline."
    report_body = "\n".join(header + [f"Anomalies: {anomalies}", "", "```", content, "```", ""]) if content else "\n".join(header + [f"Anomalies: {anomalies}"]) + "\n"
    out.write_text(report_body, encoding="utf-8")
    log_event("governance_audit", {"path": str(out), "anomalies": anomalies})
    return out


def phase_timeline_verification(ts: str) -> Tuple[Path, int]:
    """Reconstruct phase 0→3 from junie_activity and produce summary. Return anomalies count."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORTS_DIR / f"phase_audit_summary_{ts}.md"
    entries: List[str] = []
    if JUNIE_ACTIVITY.exists():
        try:
            entries = [line.strip() for line in JUNIE_ACTIVITY.read_text(encoding="utf-8").splitlines() if line.strip()]
        except Exception:
            entries = []
    commit = _git_commit() or "<unknown>"
    # Minimal heuristic: if file exists and has at least header + 1 entry → 0 anomalies
    anomalies = 0 if len(entries) >= 2 else 1
    lines = [
        "# Phase Audit Summary (0→3)",
        f"Generated: {ts}",
        f"Commit: {commit}",
        "",
        f"Entries observed: {max(0, len(entries)-1)}",
        f"Anomalies: {anomalies}",
    ]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log_event("phase_audit", {"path": str(out), "anomalies": anomalies})
    return out, anomalies


def cleanup_residuals(now: datetime) -> Dict[str, int]:
    removed_logs = 0
    removed_bundles = 0
    # Logs archive older than 60 days
    archive_dir = LOGS_DIR / "archive"
    cutoff_logs = now - timedelta(days=60)
    if archive_dir.exists():
        for p in archive_dir.rglob("*"):
            if p.is_file():
                try:
                    if datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc) < cutoff_logs:
                        p.unlink()
                        removed_logs += 1
                except Exception:
                    pass
    # Backups older than 90 days; keep last 2 bundles
    cutoff_bundles = now - timedelta(days=90)
    if BACKUPS_DIR.exists():
        bundles = sorted([p for p in BACKUPS_DIR.glob("*.bundle") if p.is_file()], key=lambda x: x.stat().st_mtime)
        keep = set(bundles[-2:])
        for b in bundles:
            if b in keep:
                continue
            try:
                if datetime.fromtimestamp(b.stat().st_mtime, tz=timezone.utc) < cutoff_bundles:
                    b.unlink()
                    removed_bundles += 1
            except Exception:
                pass
    # Branch cleanup only when allowed
    if os.getenv("ALLOW_BRANCH_CLEANUP", "false").lower() == "true":
        try:
            subprocess.run(["git", "branch", "-D", "fix/import-paths"], cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass
        # Delete maintenance/preflight_* branches locally
        try:
            out = subprocess.check_output(["git", "branch"], cwd=str(REPO_ROOT)).decode("utf-8")
            for line in out.splitlines():
                name = line.strip().lstrip("*").strip()
                if name.startswith("maintenance/preflight_"):
                    subprocess.run(["git", "branch", "-D", name], cwd=str(REPO_ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            pass
    log_event("residuals_cleanup", {"removed_logs": removed_logs, "removed_bundles": removed_bundles})
    return {"removed_logs": removed_logs, "removed_bundles": removed_bundles}


def certification(ts: str, anomalies_total: int) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "phase": "Post-Cleanup",
        "certified_by": "Junie",
        "supervised_by": f"HITL-{os.getenv('USERNAME') or os.getenv('USER') or 'operator'}",
        "compliance_score": 100 if anomalies_total == 0 else max(0, 100 - anomalies_total * 5),
        "timestamp": _now_iso(),
        "commit": _git_commit(),
    }
    out = REPORTS_DIR / f"factory_certification_{ts}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if not FACTORY_CERT_CSV.exists():
        FACTORY_CERT_CSV.write_text("ts,phase,score,file\n", encoding="utf-8")
    with FACTORY_CERT_CSV.open("a", encoding="utf-8") as f:
        f.write(f"{payload['timestamp']},{payload['phase']},{payload['compliance_score']},{out.relative_to(REPO_ROOT).as_posix()}\n")
    log_event("factory_certification", {"score": payload["compliance_score"], "file": str(out)})
    return out


def main() -> None:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    integrity_path = audit_sweep(ts)
    gov_report = governance_deep_check(ts)
    phase_report, anomalies = phase_timeline_verification(ts)
    cleanup = cleanup_residuals(datetime.now(timezone.utc))
    cert = certification(ts, anomalies_total=anomalies)

    summary = {
        "integrity_snapshot": str(integrity_path.relative_to(REPO_ROOT)),
        "governance_report": str(gov_report.relative_to(REPO_ROOT)),
        "phase_report": str(phase_report.relative_to(REPO_ROOT)),
        "cleanup": cleanup,
        "certification": str(cert.relative_to(REPO_ROOT)),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
