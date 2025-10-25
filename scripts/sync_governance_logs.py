from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Prefer repo-root aware paths
REPO_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = REPO_ROOT / "artifacts"
TELEMETRY_DIR = ARTIFACTS_DIR / "telemetry"
LOGS_DIR = REPO_ROOT / "validation" / "logs"
HITL_LOG = ARTIFACTS_DIR / "hitl_actions.jsonl"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except Exception:
        return []


def _collect_audit_files() -> Dict[str, Any]:
    summary: Dict[str, Any] = {"files": []}
    if LOGS_DIR.exists():
        for f in LOGS_DIR.rglob("*.log"):
            try:
                txt = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "[AUDIT]" in txt:
                summary["files"].append(str(f.relative_to(REPO_ROOT)))
    return summary


def build_daily_digest(now: datetime | None = None) -> Path:
    now = now or datetime.now(timezone.utc)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Telemetry
    drift = _read_jsonl(TELEMETRY_DIR / "ethical_drift.jsonl")
    optimize = _read_jsonl(TELEMETRY_DIR / "optimization_adjustment.jsonl")

    # HITL actions
    hitl = _read_jsonl(HITL_LOG)

    # Basic audit file list
    audit_files = _collect_audit_files()

    digest = {
        "ts": now.isoformat(),
        "counts": {
            "ethical_drift": len(drift),
            "optimization_adjustment": len(optimize),
            "hitl_actions": len(hitl),
        },
        "last": {
            "ethical_drift": drift[-5:] if drift else [],
            "optimization_adjustment": optimize[-5:] if optimize else [],
            "hitl_actions": hitl[-5:] if hitl else [],
        },
        "audit_files": audit_files.get("files", []),
    }

    out_path = ARTIFACTS_DIR / f"audit_digest_{now.date().isoformat()}.json"
    out_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def upload_to_gcs(path: Path) -> None:
    bucket_name = os.getenv("GCS_BUCKET", "")
    if not bucket_name:
        print("[SYNC] GCS_BUCKET not set; skipping upload.")
        return
    try:
        from google.cloud import storage  # type: ignore
    except Exception as e:  # pragma: no cover
        print(f"[SYNC] google-cloud-storage not available: {e}")
        return

    client = storage.Client()  # credentials must be provided by environment
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(path.name)
    blob.upload_from_filename(str(path))
    print(f"[SYNC] Uploaded {path.name} to gs://{bucket_name}/{path.name}")


def main() -> None:
    digest_path = build_daily_digest()
    # Attempt GCS upload if configured
    try:
        upload_to_gcs(digest_path)
    except Exception as e:
        print(f"[SYNC] Upload skipped or failed: {e}")


if __name__ == "__main__":
    main()
