from __future__ import annotations
"""
Lightweight bootstrap to ensure repository root and src/ are available on sys.path.

Import this module at the top of entrypoints (agents, scripts) to stabilize imports
without relying on environment-specific PYTHONPATH settings.
"""
import sys
from pathlib import Path

# Resolve repo root (parent of tools/)
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC = _REPO_ROOT / "src"

# Prepend to sys.path if not present
repo_str = str(_REPO_ROOT)
src_str = str(_SRC)
if repo_str not in sys.path:
    sys.path.insert(0, repo_str)
if src_str not in sys.path:
    sys.path.insert(0, src_str)
