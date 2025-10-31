from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

# Resolve project root by locating this utils/ directory and going up one level
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Common directories
PERSONAS_DIR = PROJECT_ROOT / "personas"
KB_SRC_DIR = PROJECT_ROOT / "knowledge_base" / "source_documents"
KB_INDEX_DIR = PROJECT_ROOT / "knowledge_base" / "vector_store" / "faiss_index"
PROVENANCE_DIR = PROJECT_ROOT / "knowledge_base" / "provenance"
TOOLS_DIR = PROJECT_ROOT / "tools"
TESTS_DIR = PROJECT_ROOT / "tests"
SRC_DIR = PROJECT_ROOT / "src"
LOGS_DIR = PROJECT_ROOT / "logs"
TASKS_DIR = PROJECT_ROOT / "tasks"
TASKS_COMPLETE_DIR = TASKS_DIR / "tasks_complete"
TASKS_REVIEWS_DIR = TASKS_DIR / "reviews"
GOVERNANCE_DIR = PROJECT_ROOT / "governance"
POLICIES_DIR = GOVERNANCE_DIR / "policies"


def resolve_path(file_path: str, base_dir: Optional[Path] = None, allowed_roots: Optional[Iterable[Path]] = None) -> Path:
    """Resolve a repository-safe absolute path and optionally enforce allowed roots.

    Args:
        file_path: User-provided relative or absolute path.
        base_dir: Base directory to resolve relative paths from (default: PROJECT_ROOT).
        allowed_roots: Optional iterable of directory roots under which the resolved path must lie.

    Returns:
        A resolved absolute Path within the repository.

    Raises:
        PermissionError: If the resolved path is outside the allowed_roots.
    """
    p = Path(file_path)
    base = base_dir or PROJECT_ROOT
    resolved = (p if p.is_absolute() else (base / p)).resolve()

    if allowed_roots:
        roots = [Path(r).resolve() for r in allowed_roots]
        if not any(str(resolved).startswith(str(root)) for root in roots):
            raise PermissionError(f"Path not within allowed roots: {resolved}")
    return resolved


__all__ = [
    "PROJECT_ROOT",
    "PERSONAS_DIR",
    "KB_SRC_DIR",
    "KB_INDEX_DIR",
    "PROVENANCE_DIR",
    "TOOLS_DIR",
    "TESTS_DIR",
    "SRC_DIR",
    "LOGS_DIR",
    "TASKS_DIR",
    "TASKS_COMPLETE_DIR",
    "TASKS_REVIEWS_DIR",
    "GOVERNANCE_DIR",
    "POLICIES_DIR",
    "resolve_path",
]