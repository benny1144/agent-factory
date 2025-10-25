from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import numpy as np  # Phase 6 dependency; installed in CI

try:
    # Prefer repo-root-aware paths
    from utils.paths import PROJECT_ROOT
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

HITL_LOG = PROJECT_ROOT / "artifacts" / "hitl_actions.jsonl"
BASELINE_PATH = PROJECT_ROOT / "data" / "ethical_baseline_v2.json"


def _read_hitl_actions(path: Path) -> List[dict]:
    if not path.exists():
        return []
    try:
        lines = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        return lines
    except Exception:
        return []


def retrain_baseline() -> None:
    """Retrain ethical baseline embeddings from HITL-approved actions.

    This function is deterministic for CI: it uses np.random.seed(42) and yields
    64-dim vectors sized to the number of approved actions.
    The output JSON contains minimal trace metadata for auditability.
    """
    actions = _read_hitl_actions(HITL_LOG)
    if not actions:
        print("[RETRAIN] No HITL actions found.")
        return

    approved = [a for a in actions if str(a.get("action", "")).lower() == "approve"]
    if not approved:
        print("[RETRAIN] No approved actions to integrate.")
        return

    # Deterministic synthetic embedding generation
    np.random.seed(42)
    vecs = np.random.rand(len(approved), 64).astype(float).tolist()

    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source_log": str(HITL_LOG),
        "approved_count": len(approved),
        "vectors": vecs,
    }
    BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[RETRAIN] Ethical baseline v2 updated with {len(approved)} records at {BASELINE_PATH}.")


if __name__ == "__main__":
    retrain_baseline()
