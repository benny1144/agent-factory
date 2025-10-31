from __future__ import annotations
"""
agent_factory.utils.paths

Wrapper to expose top-level utils.paths under the agent_factory namespace.
Do not duplicate logic here; import and re-export everything from utils.paths.
"""
from utils.paths import *  # type: ignore  # noqa: F401,F403
