# Archy Validation CLI (Phase 38.5 Certified)
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

# Repo root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
LOGS_DIR = PROJECT_ROOT / "logs"
AUDITS_DIR = PROJECT_ROOT / "governance" / "audits"
EVENT_BUS = PROJECT_ROOT / "governance" / "event_bus.jsonl"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
AUDITS_DIR.mkdir(parents=True, exist_ok=True)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, obj: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _healthcheck() -> bool:
    # Try local FastAPI health endpoints
    import urllib.request
    for url in [
        "http://127.0.0.1:8000/health",
        "http://127.0.0.1:8000/healthcheck",
    ]:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:  # nosec B310
                if resp.status == 200:
                    return True
        except Exception:
            continue
    return False


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Archy — Production Validation CLI (Phase 38.5)")
    p.add_argument("--test", action="store_true", help="Run validation checks and emit certification event")
    args = p.parse_args(argv or sys.argv[1:])

    if args.test:
        ok = _healthcheck()
        # 1) Append reflection audit line
        reflection = {
            "ts": _iso(),
            "agent": "Archy",
            "phase": "38.5",
            "event": "archivist_reflection",
            "ok": ok,
        }
        _append_jsonl(AUDITS_DIR / "archivist_reflection.jsonl", reflection)

        # 2) Emit agent_certified event on the governance bus
        _append_jsonl(EVENT_BUS, {
            "ts": _iso(),
            "agent": "Archy",
            "type": "agent_certified",
            "status": "ok" if ok else "error",
            "phase": "38.5"
        })

        # 3) Print result
        print(json.dumps({"ok": ok, "details": reflection}, indent=2))
        return 0 if ok else 1

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
