from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import sys

# Repo-root aware
REPO_ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = REPO_ROOT / "tasks" / "reviews"
REVIEW_DIR.mkdir(parents=True, exist_ok=True)
RECORDS = REPO_ROOT / "artifacts" / "genesis_reviews.jsonl"
RECORDS.parent.mkdir(parents=True, exist_ok=True)

# Best-effort audit logger import
try:
    sys.path.append(str(REPO_ROOT / "src"))
    from agent_factory.services.audit.audit_logger import log_event  # type: ignore
except Exception:  # pragma: no cover
    def log_event(event_type: str, metadata: dict | None = None) -> dict:  # type: ignore
        return {"ok": True, "data": {"event_type": event_type, "metadata": metadata or {}}}


def submit(task_title: str, review_doc_rel: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "ts": now,
        "type": "genesis_review_request",
        "task": task_title,
        "review_doc": review_doc_rel,
        "status": "SUBMITTED",
        "submitter": "Junie",
    }
    # Append to JSONL for traceability
    with open(RECORDS, "a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    # Emit structured audit event
    try:
        log_event("genesis_review_request", payload)
    except Exception:
        pass
    print(json.dumps({"ok": True, "record": payload}, indent=2))
    return payload


def main() -> None:
    # Defaults for this request per issue description
    task_title = "Deploy Archivist Agent — Read/Write Curator Implementation"
    review_doc = "tasks/reviews/2025-10-26_genesis_review_archivist.md"
    submit(task_title, review_doc)


if __name__ == "__main__":
    main()
