from __future__ import annotations

import os
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GIT_DIR = REPO_ROOT / ".git"
HOOKS_DIR = GIT_DIR / "hooks"
HOOK_FILE = HOOKS_DIR / "post-commit"

HOOK_CONTENT = """#!/usr/bin/env bash
# Agent Factory — Reflective Sync post-commit hook
# Automatically triggers reflective sync after each commit.
# Note: Git hooks are not versioned. Ensure this file is installed on each developer machine.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$REPO_ROOT" ]; then
  REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
fi
cd "$REPO_ROOT" || exit 0

# Respect opt-out flag; do not fail the commit
python tools/reflective_sync.py --auto >/dev/null 2>&1 || true
"""


def main() -> None:
    if not GIT_DIR.exists():
        print("[HOOK] .git directory not found. Run this script from a git repository.")
        return
    HOOKS_DIR.mkdir(parents=True, exist_ok=True)
    HOOK_FILE.write_text(HOOK_CONTENT, encoding="utf-8")
    # Make executable
    mode = os.stat(HOOK_FILE).st_mode
    os.chmod(HOOK_FILE, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"[HOOK] Installed post-commit hook at {HOOK_FILE}")


if __name__ == "__main__":
    main()
