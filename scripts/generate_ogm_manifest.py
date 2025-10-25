from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]

# Files required for OGM v1.0 archival (some may be absent depending on CI history)
CANDIDATES = [
    REPO_ROOT / "artifacts" / "telemetry" / "ethical_drift.jsonl",
    REPO_ROOT / "artifacts" / "telemetry" / "optimization_adjustment.jsonl",
    REPO_ROOT / "artifacts" / "hitl_actions.jsonl",
    REPO_ROOT / "data" / "ethical_baseline_v2.json",
    REPO_ROOT / "docs" / "phase2_validation_report.md",
    REPO_ROOT / "docs" / "phase3_validation_report.md",
    REPO_ROOT / "docs" / "phase4_validation_report.md",
    REPO_ROOT / "docs" / "phase5_validation_report.md",
    REPO_ROOT / "docs" / "phase6_validation_report.md",
    REPO_ROOT / "docs" / "operational_readiness_report.md",
]

MANIFEST_PATH = REPO_ROOT / "docs" / "ogm_v1_artifacts_manifest.json"


def sha256_of(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main() -> None:
    manifest: Dict[str, Dict[str, str]] = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "OGM v1.0",
        },
        "artifacts": {},
    }
    for p in CANDIDATES:
        rel = p.relative_to(REPO_ROOT).as_posix()
        if p.exists():
            try:
                digest = sha256_of(p)
                manifest["artifacts"][rel] = {
                    "sha256": digest,
                    "size_bytes": str(p.stat().st_size),
                }
            except Exception as e:
                manifest["artifacts"][rel] = {"error": f"hash_error: {e}"}
        else:
            manifest["artifacts"][rel] = {"missing": True}

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[OGM] Manifest written to {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
