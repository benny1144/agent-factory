from __future__ import annotations

from typing import Any, Dict, Iterable, List


class QdrantMemoryAdapter:
    """Stub Qdrant adapter.

    This is a no-network placeholder implementing the required interface.
    """

    def __init__(self) -> None:
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def add_documents(self, docs: Iterable[Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        docs_list = list(docs)
        ids = [f"qdrant-{i}" for i, _ in enumerate(docs_list)]
        return {"ids": ids, "count": len(ids)}

    def query(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        return [{"id": f"qdrant-{i}", "score": 1.0 - i * 0.1, "text": f"Result {i} for {query}"} for i in range(top_k)]

    def delete(self, filter: Dict[str, Any]) -> Dict[str, Any]:
        return {"deleted": 0}
