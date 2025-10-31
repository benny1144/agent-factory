from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB


def _rotate_if_needed(path: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    try:
        if path.exists() and path.stat().st_size > max_bytes:
            # rotate to .1, overwrite if exists
            rot = path.with_suffix(path.suffix + ".1")
            try:
                rot.unlink(missing_ok=True)  # type: ignore[attr-defined]
            except Exception:
                try:
                    if rot.exists():
                        rot.unlink()
                except Exception:
                    pass
            path.rename(rot)
    except Exception:
        # best-effort; ignore rotation errors
        pass


def append_jsonl(path: Path, record: Dict[str, Any], max_bytes: int = DEFAULT_MAX_BYTES) -> None:
    """Append a dict as JSON to a JSONL file with size-based rotation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _rotate_if_needed(path, max_bytes=max_bytes)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # fallback: try minimal string write
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(str(record) + "\n")
        except Exception:
            pass


def jsonl_logger(agent_name: str) -> Path:
    """Return a path for daily JSONL log for the given agent name."""
    base = Path(os.getenv("LOGS_DIR") or (Path(__file__).resolve().parents[1] / "logs"))
    base.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone

    day = datetime.now(timezone.utc).date().isoformat()
    return base / f"{agent_name}_{day}.jsonl"


__all__ = ["append_jsonl", "jsonl_logger"]
