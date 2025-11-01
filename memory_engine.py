# repo-root: memory_engine.py
from typing import List, Dict, Any
try:
    from factory_agents.archivist.audit_logger import log_knowledge_ingest
except Exception:  # pragma: no cover
    # fallback to root shim if module path differs
    from audit_logger import log_knowledge_ingest  # type: ignore


class MemoryEngine:
    """Simple in-memory document store used by tests.

    Methods
    -------
    add_documents(docs, metadata)
        Adds documents and emits an [AUDIT] knowledge_ingest line.
    """

    def __init__(self, backend: str | None = None):
        self.backend = backend or "inmem"
        self._docs: List[str] = []

    def add_documents(self, docs: List[str], metadata: Dict[str, Any] | None = None):
        self._docs.extend(docs)
        src = (metadata or {}).get("source", "unknown")
        log_knowledge_ingest(src, len(docs))
        return {"count": len(docs)}
