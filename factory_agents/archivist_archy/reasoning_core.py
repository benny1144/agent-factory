from __future__ import annotations
"""
Compatibility wrapper for Archy consolidation (Phase 38.9).
Routes imports to the legacy module until full migration completes.
"""
# NOTE: Full implementation lives under factory_agents.archivist for now.
# Consolidation step exposes the same API under factory_agents.archivist_archy.
from factory_agents.archivist.reasoning_core import *  # type: ignore
