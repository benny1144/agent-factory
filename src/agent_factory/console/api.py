from __future__ import annotations

from fastapi import APIRouter
from pathlib import Path

router = APIRouter()


@router.get("/audit")
def list_audit_logs() -> dict:
    """List log files under artifacts/ that contain [AUDIT] lines.

    Security: Scope strictly to the local artifacts directory.
    Returns a JSON payload with relative file paths.
    """
    artifacts = Path("artifacts")
    results: list[str] = []
    if artifacts.exists():
        for f in artifacts.rglob("*.log"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "[AUDIT]" in text:
                results.append(str(f))
    return {"audit_files": results}
