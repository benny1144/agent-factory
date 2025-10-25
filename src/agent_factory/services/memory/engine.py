from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from agent_factory.services.audit.audit_logger import log_event
from utils.procedural_memory_pg import insert_memory_event, init_db
from utils.firewall_protocol import require_risk

# Adapter imports (stubs)
from .faiss_adapter import FaissMemoryAdapter
from .qdrant_adapter import QdrantMemoryAdapter
from .redis_adapter import RedisMemoryAdapter


class MemoryEngine:
    """Federated Memory Engine that routes to a selected backend.

    Backends: faiss | qdrant | redis
    Selected via env var MEMORY_BACKEND; defaults to faiss.

    All operations emit audit events and are recorded into procedural memory (memory_events table).
    """

    def __init__(self, backend: str | None = None):
        init_db()  # ensure DB exists
        self.backend = (backend or os.getenv("MEMORY_BACKEND") or "faiss").strip().lower()
        if self.backend == "qdrant":
            self.adapter = QdrantMemoryAdapter()
        elif self.backend == "redis":
            self.adapter = RedisMemoryAdapter()
        else:
            self.backend = "faiss"
            self.adapter = FaissMemoryAdapter()
        self.adapter.connect()

    def _record(self, event_type: str, details: Dict[str, Any]) -> None:
        # Audit log
        log_event(f"memory_{event_type}", {"backend": self.backend, **details})
        # DB record
        try:
            insert_memory_event(
                backend=self.backend,
                event_type=event_type,
                details_json=details,
            )
        except Exception:
            # Non-fatal: keep runtime resilient
            pass

    def add_documents(self, docs: Iterable[Any], metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """Add documents to memory.

        Args:
            docs: Iterable of strings or objects with "page_content" and optional "metadata".
            metadata: Optional metadata applied to all docs.
        Returns:
            Adapter-specific result dict (deterministic stub schema: {"ids": [...], "count": int}).
        """
        docs_list = list(docs)
        meta = metadata or {}
        result = self.adapter.add_documents(docs_list, meta)
        self._record("insert", {"count": result.get("count", len(docs_list)), "meta": meta})
        return result

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        results = self.adapter.query(query=query, top_k=top_k)
        self._record("search", {"query": query, "top_k": top_k, "result_count": len(results)})
        return results

    @require_risk("HIGH")
    def delete(self, filter: Dict[str, Any]) -> Dict[str, Any]:
        result = self.adapter.delete(filter)
        self._record("delete", {"filter": filter, "deleted": result.get("deleted", 0)})
        return result


__all__ = ["MemoryEngine"]
