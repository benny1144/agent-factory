from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# Local project root resolution
PROJECT_ROOT = Path(__file__).resolve()
while PROJECT_ROOT.name != "agent-factory" and PROJECT_ROOT.parent != PROJECT_ROOT:
    PROJECT_ROOT = PROJECT_ROOT.parent

LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
TRACE_LOG = LOGS_DIR / "autogen_bridge.jsonl"


def _append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


@dataclass
class BridgeResult:
    ok: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    meta: Dict[str, Any] = None  # type: ignore[assignment]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "data": self.data,
            "error": self.error,
            "meta": self.meta or {},
        }


class AutoGenBridge:
    """Lightweight orchestration facade for AutoGen-style task runs.

    This implementation avoids hard external dependencies and network calls by default.
    It integrates with archivist reasoning_core.llm_generate when available, and always
    emits structured trace logs to logs/autogen_bridge.jsonl.
    """

    def __init__(self, trace_log: Path | None = None):
        self.trace_log = trace_log or TRACE_LOG

    def run(self, task: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ts = time.time()
        params = params or {}
        run_id = f"autogen-{int(ts*1000)}"
        record: Dict[str, Any] = {
            "ts": ts,
            "run_id": run_id,
            "task": task,
            "params": params,
            "phase": "start",
        }
        _append_jsonl(self.trace_log, record)

        # Try to utilize reasoning_core.llm_generate for a deterministic local result
        summary = None
        provider = None
        try:
            from factory_agents.archivist import reasoning_core as rc
            result = rc.llm_generate(f"Summarize task: {task}")
            provider = result.get("provider")
            summary = (result.get("data") or {}).get("text")
        except Exception as e:
            summary = None

        if not summary:
            # Deterministic fallback: echo task
            summary = f"[local-fallback] {task.strip()}"
            provider = provider or "local"

        out: BridgeResult = BridgeResult(
            ok=True,
            data={
                "run_id": run_id,
                "task": task,
                "summary": summary,
            },
            error=None,
            meta={"provider": provider, "duration_ms": int((time.time() - ts) * 1000)},
        )

        _append_jsonl(self.trace_log, {"ts": time.time(), "run_id": run_id, "phase": "end", "result": out.to_dict()})
        return out.to_dict()


def _cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="AutoGen Bridge test runner")
    parser.add_argument("--test", action="store_true", help="run a simple self-test")
    parser.add_argument("--task", type=str, default="sample", help="task to run")
    args = parser.parse_args(argv)

    bridge = AutoGenBridge()
    if args.test:
        res = bridge.run(args.task)
        print(json.dumps(res, ensure_ascii=False))
        return 0
    else:
        print("Specify --test to run a smoke test", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(_cli(sys.argv[1:]))

__all__ = ["AutoGenBridge", "BridgeResult"]
