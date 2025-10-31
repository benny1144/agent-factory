from __future__ import annotations

import json
import sys
from argparse import ArgumentParser
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.paths import (
    PROJECT_ROOT,
    TASKS_DIR,
    TASKS_COMPLETE_DIR,
    POLICIES_DIR,
    LOGS_DIR,
    resolve_path,
    TASKS_REVIEWS_DIR,
)
from tools.logging_utils import JsonlLogger, Timer
from scripts.phase_handlers import (
    run_phase_1,
    run_phase_2,
    run_phase_3,
    run_phase_4,
    run_phase_5,
    run_phase_6,
    run_phase_7,
    run_phase_8,
    run_phase_9,
    run_phase_10,
    run_phase_11,
    run_phase_12,
)


TASKS_FILE_DEFAULT = TASKS_DIR / "AgentFactory_MasterBuild_Phase0_35.json"
POLICY_FILE_DEFAULT = POLICIES_DIR / "junie_execution_policy.yaml"


@dataclass
class PhaseResult:
    phase: int
    title: str
    action: str
    status: str  # success | skipped | error | pending
    details: Dict[str, Any]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def slugify(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in text).strip("_")


def ensure_dirs() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_COMPLETE_DIR.mkdir(parents=True, exist_ok=True)
    TASKS_REVIEWS_DIR.mkdir(parents=True, exist_ok=True)


def write_phase_report(result: PhaseResult) -> Path:
    fname = f"phase_{result.phase:02d}_{slugify(result.title or str(result.phase))}.json"
    path = TASKS_COMPLETE_DIR / fname
    with path.open("w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2)
    return path


def write_review_report(result: PhaseResult) -> Path:
    """Write a copy of the phase report into tasks/reviews as required by ISSUE DESCRIPTION."""
    fname = f"phase_{result.phase:02d}_{slugify(result.title or str(result.phase))}.json"
    path = TASKS_REVIEWS_DIR / fname
    with path.open("w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2)
    return path


def backfill_reviews(skip_if_exists: bool = True) -> int:
    """Mirror any existing tasks_complete reports into tasks/reviews.

    Returns the number of files written.
    """
    written = 0
    for src in TASKS_COMPLETE_DIR.glob("phase_*.json"):
        dst = TASKS_REVIEWS_DIR / src.name
        if skip_if_exists and dst.exists():
            continue
        try:
            data = json.loads(src.read_text(encoding="utf-8"))
            with dst.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            written += 1
        except Exception:
            # Non-fatal: continue
            continue
    return written


def run_phase_0(phase_spec: Dict[str, Any]) -> PhaseResult:
    from scripts.verify_project import verify_project

    with Timer() as t:
        report = verify_project()
    status = "success" if report.get("ok") else "error"
    details = {
        "duration_ms": t.duration_ms,
        "checks": report.get("checks", []),
        "errors": report.get("errors", []),
    }
    return PhaseResult(
        phase=phase_spec.get("phase", 0),
        title=phase_spec.get("title", "System Consolidation and Verification"),
        action=phase_spec.get("action", "Verify project"),
        status=status,
        details=details,
    )


def run_phase_default(phase_spec: Dict[str, Any]) -> PhaseResult:
    # Placeholder execution: document intent, mark as pending
    details = {
        "note": "Phase scaffolding not yet implemented in this run. See docs/masterbuild/ for plan and TODOs.",
        "source": phase_spec.get("source"),
        "action": phase_spec.get("action"),
    }
    return PhaseResult(
        phase=phase_spec.get("phase"),
        title=phase_spec.get("title", ""),
        action=phase_spec.get("action", ""),
        status="pending",
        details=details,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = ArgumentParser(description="Agent Factory MasterBuild Runner (Phases 0–35)")
    parser.add_argument("--tasks", type=str, default=str(TASKS_FILE_DEFAULT), help="Path to tasks JSON")
    parser.add_argument("--policy", type=str, default=str(POLICY_FILE_DEFAULT), help="Path to execution policy YAML")
    parser.add_argument("--start", type=int, default=0, help="Start phase number")
    parser.add_argument("--end", type=int, default=35, help="End phase number (inclusive)")
    parser.add_argument("--dry-run", action="store_true", help="Do not execute side-effects; only log")
    parser.add_argument("--force", action="store_true", help="Ignore skip_if_exists and re-execute phases in the range")

    args = parser.parse_args(argv)

    ensure_dirs()
    logger = JsonlLogger()

    tasks_path = resolve_path(args.tasks)
    policy_path = resolve_path(args.policy)

    # Backfill any existing reports into tasks/reviews prior to run
    try:
        backfilled = backfill_reviews(skip_if_exists=True)
        if backfilled:
            logger.log(True, {"event": "backfill_reviews", "written": backfilled})
    except Exception as e:
        logger.log(False, {"event": "backfill_reviews_error"}, error=str(e))

    # Load tasks
    tasks_obj = load_json(tasks_path)
    directives = tasks_obj.get("directives", {})
    phases = tasks_obj.get("phases", [])

    # Execution banner
    logger.log(True, {
        "event": "masterbuild_start",
        "tasks_file": str(tasks_path.relative_to(PROJECT_ROOT)),
        "policy_file": str(policy_path.relative_to(PROJECT_ROOT)) if policy_path.exists() else None,
        "range": {"start": args.start, "end": args.end},
        "dry_run": args.dry_run,
        "directives": directives,
    })

    # Iterate phases
    results: List[PhaseResult] = []
    for phase_spec in phases:
        pnum = int(phase_spec.get("phase"))
        if pnum < args.start or pnum > args.end:
            continue

        title = phase_spec.get("title", f"Phase {pnum}")
        logger.log(True, {"event": "phase_begin", "phase": pnum, "title": title})

        # Skip if exists
        report_path = TASKS_COMPLETE_DIR / f"phase_{pnum:02d}_{slugify(title)}.json"
        if directives.get("skip_if_exists") and report_path.exists() and not args.force:
            # Load existing to reflect status
            try:
                prev = json.loads(report_path.read_text(encoding="utf-8"))
                result = PhaseResult(**prev)
                result.status = result.status or "skipped"
            except Exception:
                result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status="skipped", details={"reason": "existing_report"})
        else:
            try:
                if pnum == 0:
                    result = run_phase_0(phase_spec) if not args.dry_run else PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status="pending", details={"note": "dry-run"})
                elif pnum == 1 and not args.dry_run:
                    status, details = run_phase_1()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 2 and not args.dry_run:
                    status, details = run_phase_2()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 3 and not args.dry_run:
                    status, details = run_phase_3()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 4 and not args.dry_run:
                    status, details = run_phase_4()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 5 and not args.dry_run:
                    status, details = run_phase_5()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 6 and not args.dry_run:
                    status, details = run_phase_6()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 7 and not args.dry_run:
                    status, details = run_phase_7()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 8 and not args.dry_run:
                    status, details = run_phase_8()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 9 and not args.dry_run:
                    status, details = run_phase_9()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 10 and not args.dry_run:
                    status, details = run_phase_10()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 11 and not args.dry_run:
                    status, details = run_phase_11()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                elif pnum == 12 and not args.dry_run:
                    status, details = run_phase_12()
                    result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status=status, details=details)
                else:
                    result = run_phase_default(phase_spec)
            except Exception as e:
                result = PhaseResult(phase=pnum, title=title, action=phase_spec.get("action", ""), status="error", details={"exception": str(e)})

        # Persist report and mirror to reviews, then log
        path = write_phase_report(result)
        review_path = write_review_report(result)
        results.append(result)
        logger.log(result.status != "error", {
            "event": "phase_end",
            "phase": pnum,
            "title": title,
            "status": result.status,
            "report": str(path.relative_to(PROJECT_ROOT)),
            "review_report": str(review_path.relative_to(PROJECT_ROOT)),
        }, error=None if result.status != "error" else json.dumps(result.details))

    # Completion
    logger.log(True, {"event": "masterbuild_end", "phases_processed": len(results)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
