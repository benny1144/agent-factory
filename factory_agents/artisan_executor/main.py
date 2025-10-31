from __future__ import annotations

"""Artisan Executor — Canonical Entrypoint (Phase 38.8)

Runs the normalized executor loop and provides a --test mode to validate
runtime logging and directory layout without executing tasks.
"""

import argparse
import sys
from pathlib import Path

# Repo-safe imports
try:
    from utils.paths import PROJECT_ROOT
except Exception:  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve()
    while PROJECT_ROOT.name != "agent-factory" and PROJECT_ROOT.parent != PROJECT_ROOT:
        PROJECT_ROOT = PROJECT_ROOT.parent

from factory_agents.artisan_executor.core import run_loop, RUNTIME_LOG


def _write_test_event() -> None:
    RUNTIME_LOG.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_LOG.write_text("", encoding="utf-8") if not RUNTIME_LOG.exists() else None
    # append a test line via simple write
    with RUNTIME_LOG.open("a", encoding="utf-8") as f:
        f.write('{"ts":"TEST","event":"self_test","ok":true}' + "\n")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Artisan Executor Entrypoint (Phase 38.8)")
    p.add_argument("--test", action="store_true", help="Perform a self-test (logging) and exit")
    p.add_argument("--poll", type=float, default=10.0, help="Polling interval seconds")
    args = p.parse_args(argv or sys.argv[1:])

    if args.test:
        _write_test_event()
        print(str(RUNTIME_LOG))
        return 0

    run_loop(poll_seconds=float(args.poll))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
