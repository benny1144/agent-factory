from __future__ import annotations

from pathlib import Path

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

__all__ = [
    "PROJECT_ROOT",
    "PERSONAS_DIR",
    "KB_SRC_DIR",
    "KB_INDEX_DIR",
    "PROVENANCE_DIR",
    "TOOLS_DIR",
    "TESTS_DIR",
    "SRC_DIR",
]