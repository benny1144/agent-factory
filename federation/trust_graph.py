from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from agent_factory.services.audit.audit_logger import log_event
except Exception:  # pragma: no cover - fallback for static tools
    def log_event(event_type: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:  # type: ignore
        return {"ok": True, "data": {"event_type": event_type, "metadata": metadata or {}}}


@dataclass
class TrustGraph:
    """Federated Trust Graph across Genesis instances.

    - Nodes represent Genesis instances and may carry a policy embedding vector.
    - Edges represent signed attestations with weights in [0,1].
    - Reconciliation compares node policy vectors; on drift, it reduces edge weights and logs events.
    """

    nodes: Dict[str, List[float]] = field(default_factory=dict)
    edges: Dict[Tuple[str, str], float] = field(default_factory=dict)

    def add_node(self, node_id: str, policy_vector: List[float] | None = None) -> None:
        if policy_vector is not None:
            self.nodes[node_id] = [float(x) for x in policy_vector]
        else:
            self.nodes.setdefault(node_id, [])

    def add_attestation(self, src: str, dst: str, weight: float, signature: str | None = None) -> None:
        w = max(0.0, min(1.0, float(weight)))
        self.edges[(src, dst)] = w
        # Log creation for audit trail
        try:
            log_event("trust_attestation", {"src": src, "dst": dst, "weight": w, "signature": signature})
        except Exception:
            pass

    @staticmethod
    def _cosine(a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        num = sum(x * y for x, y in zip(a, b))
        den1 = sum(x * x for x in a) ** 0.5
        den2 = sum(y * y for y in b) ** 0.5
        if den1 == 0 or den2 == 0:
            return 0.0
        v = num / (den1 * den2)
        # Clamp numeric noise
        return max(-1.0, min(1.0, float(v)))

    def reconcile_drift(self, threshold: float = 0.95) -> Dict[str, Any]:
        """Reduce trust weights when policy vectors diverge (cosine < threshold).

        Returns a summary dict with changed edges and similarity stats.
        """
        changes: List[Dict[str, Any]] = []
        for (src, dst), w in list(self.edges.items()):
            v_src = self.nodes.get(src) or []
            v_dst = self.nodes.get(dst) or []
            sim = self._cosine(v_src, v_dst)
            if sim < threshold:
                new_w = max(0.0, w * 0.5)  # conservative reduction
                self.edges[(src, dst)] = new_w
                changes.append({"src": src, "dst": dst, "old": w, "new": new_w, "similarity": sim})
        payload = {"threshold": threshold, "changes": changes}
        try:
            log_event("trust_reconcile", payload)
        except Exception:
            pass
        return payload

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": {k: v for k, v in self.nodes.items()},
            "edges": [[a, b, w] for (a, b), w in self.edges.items()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrustGraph":
        tg = cls()
        for nid, vec in (data.get("nodes", {}) or {}).items():
            tg.nodes[nid] = [float(x) for x in vec]
        for entry in data.get("edges", []) or []:
            if isinstance(entry, (list, tuple)) and len(entry) >= 3:
                a, b, w = entry[0], entry[1], float(entry[2])
                tg.edges[(str(a), str(b))] = max(0.0, min(1.0, w))
        return tg

    def save(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "TrustGraph":
        p = Path(path)
        if not p.exists():
            return cls()
        try:
            return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            return cls()


__all__ = ["TrustGraph"]
