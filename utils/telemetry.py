from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

# Telemetry artifacts directory (stored in repo for CI artifacts upload)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_DIR = PROJECT_ROOT / "artifacts" / "telemetry"
TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)


def log_metric(metric_name: str, data: Dict[str, Any]) -> None:
    """Append a metric record to a JSONL file for Prometheus/audit ingestion.

    Args:
        metric_name: Short metric identifier (e.g., "ethical_drift").
        data: Arbitrary JSON-serializable payload containing metric data.
    """
    record = {
        "metric": metric_name,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    path = TELEMETRY_DIR / f"{metric_name}.jsonl"
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def summarize_metrics() -> Dict[str, Any]:
    """Aggregate and summarize collected telemetry counts per metric.

    Returns:
        A dict mapping metric name to count of records observed.
    """
    summary: Dict[str, Any] = {}
    for file in TELEMETRY_DIR.glob("*.jsonl"):
        try:
            with open(file, "r", encoding="utf-8") as f:
                lines = [json.loads(l) for l in f if l.strip()]
        except Exception:
            lines = []
        summary[file.stem] = len(lines)
    out_path = TELEMETRY_DIR / "telemetry_summary.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    return summary


__all__ = ["log_metric", "summarize_metrics", "TELEMETRY_DIR"]
