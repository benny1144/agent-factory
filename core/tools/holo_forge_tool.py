from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Dict, Optional

# Optional import: allow tests to run without qdrant-client installed
try:  # pragma: no cover - exercised in environments with qdrant-client
    from qdrant_client import QdrantClient  # type: ignore
except Exception:  # pragma: no cover
    QdrantClient = None  # type: ignore


class HoloForgeSearchTool:
    """Governed tool for semantic retrieval from the HoloForge lattice.

    This implementation is resilient in environments without the qdrant-client
    dependency: it defers client usage to runtime. Tests may monkeypatch
    `run()` directly, so simply instantiating the tool should not error.
    """

    def __init__(self, host: str, api_key: str, collection: str):
        self.host = host
        self.api_key = api_key
        self.collection = collection
        self._client: Optional[QdrantClient] = None  # type: ignore[name-defined]
        if QdrantClient is not None:  # type: ignore[name-defined]
            try:
                self._client = QdrantClient(host=host, api_key=api_key)  # type: ignore[call-arg]
            except Exception:
                # Defer connection errors to first real call
                self._client = None

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        if QdrantClient is None:  # type: ignore[name-defined]
            raise RuntimeError("qdrant-client not available in this environment")
        # Lazy init
        self._client = QdrantClient(host=self.host, api_key=self.api_key)  # type: ignore[call-arg]
        return self._client

    def run(self, query_vector, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Search the configured collection using a query vector.

        Args:
            query_vector: List[float] or compatible vector for Qdrant.
            metadata: May include {"limit": int} and other fields for auditing.

        Returns a dict with either:
            {"results": [...], "latency_ms": <float>, "timestamp": <iso>} or
            {"error": <str>, "latency_ms": <float>, "timestamp": <iso>}.
        """
        t0 = time.time()
        try:
            client = self._ensure_client()
            limit = int(metadata.get("limit", 3) or 3)
            res = client.search(collection_name=self.collection, query_vector=query_vector, limit=limit)
            latency = round((time.time() - t0) * 1000, 2)
            return {
                "results": [getattr(r, "payload", None) or getattr(r, "dict", lambda: {})() for r in res],
                "latency_ms": latency,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:  # pragma: no cover - depends on env/network
            return {
                "error": str(e),
                "latency_ms": round((time.time() - t0) * 1000, 2),
                "timestamp": datetime.utcnow().isoformat(),
            }
