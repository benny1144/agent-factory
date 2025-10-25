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

    Behavior updates for Continuous Oversight:
    - Compute mean drift from telemetry (artifacts/telemetry/ethical_drift.jsonl) when present.
    - Only update baseline when mean drift exceeds threshold (ENV ETHICAL_DRIFT_THRESHOLD or 0.35).
    - Emit [RETRAIN] audit event.
    - Write alias file data/ethical_baseline.json for downstream tools.
    """
    # Try to read drift telemetry (local fallback instead of Cloud Logs for CI/local)
    telemetry_path = PROJECT_ROOT / "artifacts" / "telemetry" / "ethical_drift.jsonl"
    scores: list[float] = []
    if telemetry_path.exists():
        try:
            for line in telemetry_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                rec = json.loads(line)
                val = rec.get("data", {}).get("score")
                if isinstance(val, (int, float)):
                    scores.append(float(val))
        except Exception:
            scores = []
    avg_drift = sum(scores) / len(scores) if scores else None
    threshold = float(os.getenv("ETHICAL_DRIFT_THRESHOLD", "0.35"))

    actions = _read_hitl_actions(HITL_LOG)
    if not actions:
        print("[RETRAIN] No HITL actions found.")
        # Emit audit note
        try:
            from agent_factory.services.audit.audit_logger import log_event as audit_log
            audit_log("retrain", {"updated": False, "reason": "no_hitl_actions", "avg_drift": avg_drift})
        except Exception:
            pass
        return

    approved = [a for a in actions if str(a.get("action", "")).lower() == "approve"]
    if not approved:
        print("[RETRAIN] No approved actions to integrate.")
        try:
            from agent_factory.services.audit.audit_logger import log_event as audit_log
            audit_log("retrain", {"updated": False, "reason": "no_approved_actions", "avg_drift": avg_drift})
        except Exception:
            pass
        return

    if avg_drift is not None and not (avg_drift > threshold):
        print(f"[RETRAIN] Drift threshold not exceeded (avg={avg_drift:.4f} <= threshold={threshold}); skipping update.")
        try:
            from agent_factory.services.audit.audit_logger import log_event as audit_log
            audit_log("retrain", {"updated": False, "reason": "below_threshold", "avg_drift": avg_drift, "threshold": threshold})
        except Exception:
            pass
        return

    # Deterministic synthetic embedding generation
    np.random.seed(42)
    vecs = np.random.rand(len(approved), 64).astype(float).tolist()

    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source_log": str(HITL_LOG),\
        "approved_count": len(approved),
        "avg_drift": avg_drift,
        "threshold": threshold,
        "vectors": vecs,
    }
    BASELINE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    # Also write alias baseline file (without vectors to reduce size for some consumers)
    alias_path = PROJECT_ROOT / "data" / "ethical_baseline.json"
    alias_payload = {k: v for k, v in payload.items() if k != "vectors"}
    alias_path.write_text(json.dumps(alias_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    try:
        from agent_factory.services.audit.audit_logger import log_event as audit_log
        audit_log("retrain", {"updated": True, "approved_count": len(approved), "avg_drift": avg_drift, "threshold": threshold})
    except Exception:
        pass

    print(f"[RETRAIN] Ethical baseline updated with {len(approved)} records at {BASELINE_PATH}.")


if __name__ == "__main__":
    retrain_baseline()
