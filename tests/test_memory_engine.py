from __future__ import annotations

import builtins
import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from agent_factory.services.memory.engine import MemoryEngine  # type: ignore


def test_backend_selection_env(monkeypatch):
    for backend in ("faiss", "qdrant", "redis"):
        monkeypatch.setenv("MEMORY_BACKEND", backend)
        eng = MemoryEngine()
        assert eng.backend == backend


def test_add_documents_and_audit(monkeypatch, capsys):
    monkeypatch.setenv("MEMORY_BACKEND", "faiss")
    eng = MemoryEngine()
    res = eng.add_documents(["doc1", "doc2"], metadata={"source": "unit"})
    assert res["count"] == 2
    out = capsys.readouterr().out
    assert "[AUDIT]" in out
    assert "memory_insert" in out


def test_delete_high_risk_hotl_approved(monkeypatch):
    monkeypatch.setenv("MEMORY_BACKEND", "redis")
    # Allow without interactive prompt by setting HITL_APPROVE=true
    monkeypatch.setenv("HITL_APPROVE", "true")
    eng = MemoryEngine()
    res = eng.delete({"all": True})
    assert "deleted" in res
