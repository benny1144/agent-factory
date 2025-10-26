from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from agent_factory.utils.procedural_memory_pg import adjust_memory_weight, init_db
from agent_factory.utils.telemetry import TELEMETRY_DIR, log_metric

try:
    # Prefer repo-root-safe resolution for config
    from agent_factory.utils.paths import PROJECT_ROOT
except Exception:  # fallback
    PROJECT_ROOT = Path(__file__).resolve().parents[3]


CONFIG_PATH = PROJECT_ROOT / "config" / "optimization_thresholds.json"


@dataclass
class OptimizationConfig:
    window: int = 10
    drift_threshold: float = 0.35


def _load_config() -> OptimizationConfig:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return OptimizationConfig(
                window=int(data.get("optimization_window", 10)),
                drift_threshold=float(data.get("ethical_drift", 0.35)),
            )
        except Exception:
            pass
    return OptimizationConfig()


class FeedbackLoop:
    """Adaptive optimization using telemetry + drift data.

    Reads ethical drift telemetry from artifacts/telemetry/ethical_drift.jsonl (Phase 3),
    computes an average drift over a sliding window, adjusts procedural memory
    weights via adjust_memory_weight(), and logs an optimization_adjustment metric.
    """

    def __init__(self, window: int | None = None, drift_threshold: float | None = None):
        cfg = _load_config()
        self.window = int(window if window is not None else cfg.window)
        self.drift_threshold = float(drift_threshold if drift_threshold is not None else cfg.drift_threshold)
        self.engine = init_db()

    def collect_recent_drift(self) -> List[Dict[str, Any]]:
        file = TELEMETRY_DIR / "ethical_drift.jsonl"
        if not file.exists():
            return []
        try:
            lines = [json.loads(l) for l in file.read_text(encoding="utf-8").splitlines() if l.strip()]
        except Exception:
            return []
        return lines[-self.window :]

    def optimize(self) -> Dict[str, Any]:
        drift_records = self.collect_recent_drift()
        if not drift_records:
            # Emit a telemetry note for observability even when no data
            log_metric("optimization_adjustment", {"avg_drift": None, "action": "no_data"})
            print("[OPTIMIZE] status=no_data (no drift telemetry found)")
            return {"status": "no_data"}

        try:
            scores = [float(r.get("data", {}).get("score", 0.0)) for r in drift_records]
        except Exception:
            scores = []
        if not scores:
            log_metric("optimization_adjustment", {"avg_drift": None, "action": "no_scores"})
            print("[OPTIMIZE] status=no_scores (drift records missing scores)")
            return {"status": "no_scores"}

        avg_drift = sum(scores) / len(scores)
        status = "decrease_weights" if avg_drift > self.drift_threshold else "increase_weights"
        delta = -0.05 if status == "decrease_weights" else 0.05

        # Adjust procedural memory weights for Prometheus ethical alignment context
        adjust_memory_weight(
            agent="Prometheus",
            context_key="ethical_alignment",
            delta=delta,
            engine=self.engine,
        )
        log_metric("optimization_adjustment", {"avg_drift": avg_drift, "action": status})
        print(f"[OPTIMIZE] avg_drift={avg_drift:.4f} action={status}")
        return {"avg_drift": avg_drift, "action": status}


def _main() -> None:
    loop = FeedbackLoop()
    try:
        loop.optimize()
    except Exception as e:
        # Keep CI resilient; print error and exit without exception
        print(f"[OPTIMIZE] error={e}")


if __name__ == "__main__":
    _main()

__all__ = ["FeedbackLoop"]
