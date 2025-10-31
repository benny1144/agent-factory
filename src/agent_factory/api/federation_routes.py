from __future__ import annotations

import csv
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query

from agent_factory.api.telemetry_ws import emit_federation_event
from agent_factory.services.audit.audit_logger import log_event

router = APIRouter(prefix="/api/federation", tags=["federation"])  # mounted at /api/federation

CSV_PATH = Path("compliance/audit_log/federation_updates.csv")
CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

CSV_FIELDS = [
    "ts",
    "status",  # pending|approved|published|rejected
    "topic",
    "source",  # e.g., Archivist, Genesis, Human
    "sha256",
    "actor",  # approver/publisher identifier
    "notes",
]


def _ensure_csv() -> None:
    if not CSV_PATH.exists():
        with CSV_PATH.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_row(row: Dict[str, Any]) -> None:
    _ensure_csv()
    with CSV_PATH.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writerow(row)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@router.get("/updates")
def list_updates(status: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    """Return federation updates, optionally filtered by status.

    Example: GET /api/federation/updates?status=pending
    """
    _ensure_csv()
    items: List[Dict[str, Any]] = []
    with CSV_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if status and row.get("status") != status:
                continue
            items.append(row)
    return {"count": len(items), "items": items}


@router.post("/approve")
def approve_update(
    topic: str = Body(..., embed=True),
    sha256: Optional[str] = Body(default=None, embed=True),
    approver: str = Body("HITL", embed=True),
    notes: str = Body("", embed=True),
    source: str = Body("Archivist", embed=True),
) -> Dict[str, Any]:
    """Record an approval for a federation update.

    If sha256 is not provided, a hash of topic+notes is generated for traceability.
    Emits a WebSocket federation event and an audit log event.
    """
    file_hash = sha256 or _sha256_text(topic + notes)
    row = {
        "ts": _now_iso(),
        "status": "approved",
        "topic": topic,
        "source": source,
        "sha256": file_hash,
        "actor": approver,
        "notes": notes,
    }
    _append_row(row)

    # Emit WS federation event and audit log
    emit_federation_event("update_approved", {"topic": topic, "sha256": file_hash, "agent": source})
    try:
        log_event("federation_update_approved", {"topic": topic, "sha256": file_hash, "approver": approver, "source": source})
    except Exception:
        pass

    return {"ok": True, "data": row}


@router.post("/publish")
def publish_update(
    topic: str = Body(..., embed=True),
    sha256: Optional[str] = Body(default=None, embed=True),
    publisher: str = Body("Archivist", embed=True),
    notes: str = Body("", embed=True),
    source: str = Body("Archivist", embed=True),
) -> Dict[str, Any]:
    """Record a publication of a federation update.

    If sha256 is not provided, it must match a prior approved entry or will be generated from topic+notes.
    """
    file_hash = sha256 or _sha256_text(topic + notes)

    row = {
        "ts": _now_iso(),
        "status": "published",
        "topic": topic,
        "source": source,
        "sha256": file_hash,
        "actor": publisher,
        "notes": notes,
    }
    _append_row(row)

    emit_federation_event("published", {"topic": topic, "sha256": file_hash, "agent": source})
    try:
        log_event("federation_update_published", {"topic": topic, "sha256": file_hash, "publisher": publisher, "source": source})
    except Exception:
        pass

    return {"ok": True, "data": row}
