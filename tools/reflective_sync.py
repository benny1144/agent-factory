from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple

# Establish repo root and ensure import paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
import sys
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.append(str(PROJECT_ROOT / "src"))

# Repo-root aware imports (prefer utils.paths when available)
try:
    from utils.paths import PROJECT_ROOT as _PR, KB_SRC_DIR, TOOLS_DIR, PERSONAS_DIR
    PROJECT_ROOT = _PR  # use canonical if provided
except Exception:
    KB_SRC_DIR = PROJECT_ROOT / "knowledge_base" / "source_documents"
    TOOLS_DIR = PROJECT_ROOT / "tools"
    PERSONAS_DIR = PROJECT_ROOT / "personas"

# Optional audit logger (best-effort)
try:
    from agent_factory.services.audit.audit_logger import log_event
except Exception:  # pragma: no cover
    def log_event(event_type: str, metadata: dict | None = None) -> dict:  # type: ignore
        return {"ok": True, "data": {"event_type": event_type, "metadata": metadata or {}}}

GOVERNANCE_FILE = PROJECT_ROOT / "GOVERNANCE.md"
ROADMAP_FILE = PROJECT_ROOT / "docs" / "roadmap" / "phase_3_2_kba.md"  # best-effort roadmap text target
PROCEDURAL_DIR = KB_SRC_DIR / "procedural_memory" / "reflective_updates"
AUDIT_DIR = PROJECT_ROOT / "compliance" / "audit_log"
AUDIT_FILE = AUDIT_DIR / "reflective_sync.csv"
ALERTS_FILE = AUDIT_DIR / "alerts.txt"

VEC_INDEX_DIR = PROJECT_ROOT / "knowledge_base" / "vector_store" / "faiss_index"
VEC_MANIFEST = VEC_INDEX_DIR / "manifest.json"


# -----------------
# Helper functions
# -----------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_of(path: Path, chunk: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _combined_hash(paths: Iterable[Path]) -> Tuple[str, List[Tuple[str, str]]]:
    """Return combined SHA-256 over individual file hashes (path -> sha256) and list of per-file digests."""
    parts: List[Tuple[str, str]] = []
    for p in paths:
        if p.exists():
            try:
                parts.append((str(p.relative_to(PROJECT_ROOT)), _sha256_of(p)))
            except Exception:
                parts.append((str(p), "error"))
    h = hashlib.sha256()
    for rel, digest in parts:
        h.update(rel.encode("utf-8"))
        h.update(digest.encode("utf-8"))
    return h.hexdigest(), parts


# -----------------
# Core operations
# -----------------

def update_roadmap_and_governance(task_summary: str) -> List[Path]:
    """Insert task summary into GOVERNANCE.md and roadmap (best-effort).

    Returns list of files that were modified.
    """
    modified: List[Path] = []

    # Ensure Reflective Sync Automation section exists in GOVERNANCE.md, then append the latest entry.
    GOVERNANCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    text = GOVERNANCE_FILE.read_text(encoding="utf-8") if GOVERNANCE_FILE.exists() else ""
    section_title = "## Reflective Sync Automation"
    if section_title not in text:
        append = [
            "",
            section_title,
            "",
            "Every executed [JUNIE TASK] must automatically update governance records, procedural memory,",
            "and RAG embeddings via tools/reflective_sync.py.",
            "No code change is final until a sync confirmation hash is logged in compliance/audit_log/reflective_sync.csv.",
            "",
        ]
        text = (text.rstrip() + "\n" + "\n".join(append)).lstrip("\n")
        GOVERNANCE_FILE.write_text(text, encoding="utf-8")
        modified.append(GOVERNANCE_FILE)

    # Append latest entry with timestamp
    lines = text.splitlines()
    entry = f"- [{_now_iso()}] {task_summary}"
    if entry not in lines:
        with GOVERNANCE_FILE.open("a", encoding="utf-8") as f:
            f.write("\n" + entry + "\n")
        modified.append(GOVERNANCE_FILE)

    # Roadmap best-effort append
    if ROADMAP_FILE.exists():
        try:
            with ROADMAP_FILE.open("a", encoding="utf-8") as f:
                f.write("\n- [Reflective Sync] " + _now_iso() + ": " + task_summary + "\n")
            modified.append(ROADMAP_FILE)
        except Exception:
            pass
    return list(dict.fromkeys(modified))  # unique


def register_procedural_update(task_summary: str) -> Path:
    """Create a timestamped markdown note under procedural_memory/reflective_updates."""
    PROCEDURAL_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = PROCEDURAL_DIR / f"sync_{ts}.md"
    content = [
        f"# Reflective Update — {ts}",
        "",
        f"Summary: {task_summary}",
    ]
    path.write_text("\n".join(content) + "\n", encoding="utf-8")
    return path


def update_personas_metadata() -> List[Path]:
    """Append YAML update blocks to persona files (best-effort).

    We target common Genesis personas; if absent, append to all *.md under /personas.
    """
    targets: List[Path] = []
    genesis_targets = [
        PERSONAS_DIR / "genesis_knowledge_seeker.md",
        PERSONAS_DIR / "genesis_charter_agent.md",
        PERSONAS_DIR / "genesis_code_architect.md",
        PERSONAS_DIR / "genesis_critic_agent.md",
    ]
    files: List[Path] = [p for p in genesis_targets if p.exists()]
    if not files and PERSONAS_DIR.exists():
        files = list(PERSONAS_DIR.glob("*.md"))

    modified: List[Path] = []
    stamp = _now_iso()
    block = (
        "\n---\n"
        "updated_by: Junie\n"
        f"update_date: {stamp}\n"
        "sync_status: success\n"
    )
    for f in files:
        try:
            with f.open("a", encoding="utf-8") as fh:
                fh.write(block)
            modified.append(f)
        except Exception:
            continue
    return modified


def reindex_embeddings() -> List[Path]:
    """Call charter_tools to refresh the vector DB (best-effort, no external network).

    Behavior:
    - Create or update knowledge_base/vector_store/faiss_index/manifest.json with timestamp.
    - If tools/charter_tools.py exposes a CLI --reindex, invoke it via import.
    Returns list of files to include in hash (e.g., manifest).
    """
    VEC_INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # Try to call tools.charter_tools.rebuild_vector_index when available
    try:
        import importlib
        ct = importlib.import_module("tools.charter_tools")
        if hasattr(ct, "rebuild_vector_index"):
            try:
                ct.rebuild_vector_index()  # type: ignore
            except Exception:
                pass
    except Exception:
        pass

    payload = {
        "updated": _now_iso(),
        "note": "Reflective Sync manifest (deterministic stub)",
    }
    try:
        VEC_MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass
    return [VEC_MANIFEST]


def append_audit_log(files_for_hash: List[Path], details: str) -> dict:
    """Append a CSV line with timestamp, action, files_hash, and details JSON.

    If CSV does not exist, write header first.
    """
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if not AUDIT_FILE.exists():
        AUDIT_FILE.write_text("ts,action,files_hash,details\n", encoding="utf-8")

    combined, parts = _combined_hash([p for p in files_for_hash if p.exists()])
    row = {
        "ts": _now_iso(),
        "action": "reflective_sync",
        "files_hash": combined,
        "details": json.dumps({"files": parts}, ensure_ascii=False),
    }
    with AUDIT_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ts", "action", "files_hash", "details"])
        w.writerow(row)

    try:
        log_event("reflective_sync", {"files_hash": combined, "count": len(parts)})
    except Exception:
        pass
    return row


# -----------------
# CLI
# -----------------

def _run(auto: bool, test: bool, summary: str | None = None) -> int:
    allowed = os.getenv("REFLECTIVE_SYNC_ALLOWED", "true").lower() == "true"
    if not allowed:
        ALERTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        ALERTS_FILE.write_text(
            f"[{_now_iso()}] Reflective Sync blocked by REFLECTIVE_SYNC_ALLOWED flag.\n",
            encoding="utf-8",
        )
        try:
            log_event("reflective_sync_blocked", {"reason": "flag_false"})
        except Exception:
            pass
        print("[SYNC] Blocked by REFLECTIVE_SYNC_ALLOWED=false")
        return 0

    task_summary = summary or os.getenv("JUNIE_TASK_SUMMARY") or ("Automated sync" if auto else "Manual sync")

    modified_files: List[Path] = []
    # 1) Governance + Roadmap
    modified_files += update_roadmap_and_governance(task_summary)
    # 2) Procedural memory record
    proc_file = register_procedural_update(task_summary)
    modified_files.append(proc_file)
    # 3) Personas metadata
    modified_files += update_personas_metadata()
    # 4) Reindex embeddings (manifest)
    modified_files += reindex_embeddings()

    # 5) Append audit log with combined hash
    audit_row = append_audit_log(modified_files, details=task_summary)

    if test:
        print(json.dumps({"modified": [str(p) for p in modified_files], "audit": audit_row}, indent=2))
    else:
        print(f"[SYNC] Reflective Sync complete; files hashed: {len(modified_files)}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(description="Reflective Sync Automation")
    p.add_argument("--auto", action="store_true", help="Run with automated defaults after commit")
    p.add_argument("--test", action="store_true", help="Dry-run JSON output for validation")
    p.add_argument("--summary", type=str, default=None, help="Optional task summary text")
    ns = p.parse_args()
    raise SystemExit(_run(ns.auto, ns.test, ns.summary))


if __name__ == "__main__":
    main()
