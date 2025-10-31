from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from utils.paths import PROJECT_ROOT, TASKS_COMPLETE_DIR, TASKS_REVIEWS_DIR, LOGS_DIR


def sync_phase_reviews(overwrite: bool = False) -> int:
    """Mirror all phase_*.json reports from tasks/tasks_complete to tasks/reviews.

    Args:
        overwrite: If True, overwrite existing files in reviews; otherwise skip existing.

    Returns:
        Number of files written to tasks/reviews.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    written = 0
    for src in TASKS_COMPLETE_DIR.glob("phase_*.json"):
        dst = TASKS_REVIEWS_DIR / src.name
        if dst.exists() and not overwrite:
            continue
        try:
            data = json.loads(src.read_text(encoding="utf-8"))
            dst.write_text(json.dumps(data, indent=2), encoding="utf-8")
            written += 1
        except Exception:
            # Non-fatal; continue mirroring others
            continue
    return written


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Sync phase reports into tasks/reviews")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing reviews files")
    args = parser.parse_args(argv)

    count = sync_phase_reviews(overwrite=args.overwrite)
    print(f"Synced {count} review report(s) into {TASKS_REVIEWS_DIR.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
