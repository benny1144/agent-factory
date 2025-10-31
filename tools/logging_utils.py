from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from utils.paths import LOGS_DIR, PROJECT_ROOT


@dataclass
class LogEnvelope:
    ok: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


class JsonlLogger:
    """Minimal JSONL logger writing standard envelope lines to a file.

    Creates parent directories on first use. Thread/process safety is not guaranteed; this
    is a simple append-only writer suitable for local development and CI logs.
    """

    def __init__(self, log_file: Path | str = LOGS_DIR / "junie_execution.jsonl") -> None:
        self.log_path = Path(log_file)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, ok: bool, data: Dict[str, Any], *, error: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> None:
        env = LogEnvelope(ok=ok, data=data, error=error, meta=meta or {})
        ts = datetime.now(timezone.utc).isoformat()
        # Always include ts and repo_root-relative source path in meta
        env.meta.setdefault("ts", ts)
        env.meta.setdefault("source", str(self.log_path.relative_to(PROJECT_ROOT)) if self._is_subpath(self.log_path, PROJECT_ROOT) else str(self.log_path))
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(env.to_json() + "\n")

    @staticmethod
    def _is_subpath(p: Path, root: Path) -> bool:
        try:
            p.relative_to(root)
            return True
        except Exception:
            return False


class Timer:
    """Context manager to time operations in ms."""

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._end = time.perf_counter()

    @property
    def duration_ms(self) -> int:
        end = getattr(self, "_end", time.perf_counter())
        return int((end - self._start) * 1000)


__all__ = ["JsonlLogger", "LogEnvelope", "Timer"]
