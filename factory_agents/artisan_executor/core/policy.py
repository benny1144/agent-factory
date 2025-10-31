from __future__ import annotations

"""Artisan Executor Policy (v1.1)

Minimal allowlist-based command policy for safe execution.
This file is the canonical location under factory_agents/artisan_executor/core/.
"""
from typing import List

# Commands must start with one of these program names to be allowed automatically.
ALLOWLIST: List[str] = ["pytest", "python", "git", "echo"]


def is_allowed(cmd: str) -> bool:
    """Return True if the command is allowed by policy.

    A command is considered allowed when its stripped text begins with any
    of the allowlisted program tokens (exact prefix match).
    """
    if not isinstance(cmd, str):
        return False
    s = cmd.strip()
    return any(s.startswith(prefix) for prefix in ALLOWLIST)


__all__ = ["ALLOWLIST", "is_allowed"]
