from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np  # runtime dependency provided in CI workflow

# Ensure src-relative imports resolve in tests (pytest.ini adds src to pythonpath)
from utils.telemetry import log_metric
from utils.paths import PROJECT_ROOT


class EthicalDriftMonitor:
    """Detects deviations from the baseline ethical dataset.

    Computes a simple Euclidean norm difference between new embeddings and
    the baseline vectors. Emits telemetry records for downstream analysis.
    """

    def __init__(self, baseline_path: str | os.PathLike[str] = PROJECT_ROOT / "data" / "ethical_baseline.json", threshold: float = 0.35):
        self.baseline_path = str(baseline_path)
        self.threshold = float(threshold)
        self.baseline = self._load_baseline()

    def _load_baseline(self) -> List[List[float]]:
        p = Path(self.baseline_path)
        if not p.exists():
            return []
        try:
            with p.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # Expecting list[list[float]]
            if isinstance(data, list):
                return data
        except Exception:
            pass
        return []

    def compute_drift(self, new_embeddings: List[List[float]]) -> Dict[str, Any]:
        """Compare new embeddings to baseline vectors and compute drift score.

        Always emits a telemetry metric named "ethical_drift" and prints a
        one-line [DRIFT] message for CI visibility.
        """
        status: str
        drift_score: float
        if not self.baseline:
            drift_score = 0.0
            status = "no_baseline"
        else:
            baseline_vecs = np.array(self.baseline, dtype=float)
            new_vecs = np.array(new_embeddings, dtype=float)
            if len(new_vecs) == 0:
                drift_score = 0.0
                status = "no_data"
            else:
                # Align lengths by truncating to the shorter side
                n = min(len(new_vecs), len(baseline_vecs))
                diffs = np.linalg.norm(new_vecs[:n] - baseline_vecs[:n], axis=1)
                drift_score = float(np.mean(diffs)) if len(diffs) > 0 else 0.0
                status = "alert" if drift_score > self.threshold else "ok"

        # Telemetry emission
        payload = {"score": drift_score, "status": status}
        log_metric("ethical_drift", payload)
        print(f"[DRIFT] ethical_drift score={drift_score:.4f} status={status}")
        return {"drift_score": drift_score, "status": status}


def _simulate_run() -> None:
    """Simulate a drift computation so CI can exercise telemetry pathway."""
    monitor = EthicalDriftMonitor()
    # If no baseline file, generate a small synthetic baseline to compare
    if not monitor.baseline:
        baseline = [[0.0, 0.0, 0.0], [0.1, 0.1, 0.1]]
        # Do not write to repo in CI; just use in-memory comparison by creating a new monitor instance with this baseline injected
        monitor.baseline = baseline
    # Generate synthetic new embeddings with small noise
    rng = np.random.default_rng(42)
    new_embs = (rng.normal(0, 0.05, size=(2, 3))).astype(float).tolist()
    monitor.compute_drift(new_embs)


if __name__ == "__main__":
    _simulate_run()


__all__ = ["EthicalDriftMonitor"]
