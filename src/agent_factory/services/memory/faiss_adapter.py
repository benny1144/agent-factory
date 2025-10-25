from __future__ import annotations

from typing import Any, Dict, Iterable, List


class FaissMemoryAdapter:
    """Stub FAISS adapter.

    Provides deterministic behavior without requiring a live FAISS index.
    """

    def __init__(self) -> None:
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def add_documents(self, docs: Iterable[Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        docs_list = list(docs)
        ids = [f"faiss-{i}" for i, _ in enumerate(docs_list)]
        return {"ids": ids, "count": len(ids)}

    def query(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Return deterministic mock results
        return [{"id": f"faiss-{i}", "score": 1.0 - i * 0.1, "text": f"Result {i} for {query}"} for i in range(top_k)]

    def delete(self, filter: Dict[str, Any]) -> Dict[str, Any]:
        # Deletion not actually performed in stub
        return {"deleted": 0}
