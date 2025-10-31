from __future__ import annotations

"""Archy Sentinel — Ethical Drift Monitor (Phase 37)

Watches artisan/genesis activity logs and emits alerts when an ethical_drift
metric exceeds threshold (default 0.05).

Usage:
  python -S factory_agents/archy.py --once
  python -S factory_agents/archy.py --interval 5
"""

import argparse
import json
import os
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from utils.paths import PROJECT_ROOT, LOGS_DIR

ARTISAN_LOG = LOGS_DIR / "artisan_activity.jsonl"
GENESIS_LOG = LOGS_DIR / "genesis_activity.jsonl"
ALERTS_LOG = PROJECT_ROOT / "alerts" / "ethical_drift.jsonl"
EVENT_BUS = PROJECT_ROOT / "governance" / "event_bus.jsonl"


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tail_lines(path: Path, max_lines: int = 200) -> Iterable[str]:
    try:
        text = path.read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return lines[-max_lines:]
    except Exception:
        return []


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _scan_once(threshold: float = 0.05) -> int:
    count = 0
    for src in (ARTISAN_LOG, GENESIS_LOG):
        for ln in _tail_lines(src, 500):
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            drift = None
            # Accept both top-level or nested numeric fields
            if isinstance(obj, dict):
                if isinstance(obj.get("ethical_drift"), (int, float)):
                    drift = float(obj["ethical_drift"])
                elif isinstance(obj.get("data"), dict) and isinstance(obj["data"].get("ethical_drift"), (int, float)):
                    drift = float(obj["data"]["ethical_drift"])
            if drift is not None and drift > threshold:
                _append_jsonl(ALERTS_LOG, {
                    "ts": _iso(),
                    "source_log": str(src.relative_to(PROJECT_ROOT)),
                    "ethical_drift": drift,
                    "threshold": threshold,
                })
                # Mirror to governance event bus
                try:
                    import json as _json
                    import uuid as _uuid
                    EVENT_BUS.parent.mkdir(parents=True, exist_ok=True)
                    with EVENT_BUS.open("a", encoding="utf-8") as f:
                        f.write(_json.dumps({
                            "ts": _iso(),
                            "agent": "Archy",
                            "type": "ethical_drift_alert",
                            "status": "alert",
                            "ethical_drift": drift,
                            "trace_id": _uuid.uuid4().hex,
                            "phase": "38.5"
                        }, ensure_ascii=False) + "\n")
                except Exception:
                    pass
                count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Archy Sentinel Drift Monitor")
    p.add_argument("--threshold", type=float, default=0.05)
    # Allow env override for reflection/sentinel interval
    _env_interval = os.getenv("REFLECTION_INTERVAL_SECONDS") or os.getenv("ARCHY_INTERVAL_SECONDS")
    try:
        _default_interval = float(_env_interval) if _env_interval else 10.0
    except Exception:
        _default_interval = 10.0
    p.add_argument("--interval", type=float, default=_default_interval, help="Seconds between scans; if <=0, run once")
    p.add_argument("--once", action="store_true", help="Run a single scan and exit")
    args = p.parse_args(argv)

    if args.once or args.interval <= 0:
        _scan_once(args.threshold)
        return 0

    while True:
        try:
            _scan_once(args.threshold)
            time.sleep(max(1.0, float(args.interval)))
        except KeyboardInterrupt:
            break
        except Exception:
            time.sleep(2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
