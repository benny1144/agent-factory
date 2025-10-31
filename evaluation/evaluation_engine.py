from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    from utils.paths import PROJECT_ROOT
except Exception:
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

CAUSAL_PATH = PROJECT_ROOT / "evaluation" / "causal_graph.json"

try:
    from agent_factory.services.audit.audit_logger import log_causal_analysis
except Exception:  # pragma: no cover
    def log_causal_analysis(details: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {"ok": True, "data": details}


@dataclass
class CausalGraph:
    nodes: List[str]
    edges: List[Tuple[str, str]]  # (cause -> effect)

    def to_dict(self) -> Dict[str, Any]:
        return {"nodes": self.nodes, "edges": [[a, b] for a, b in self.edges]}


def explain_decision_tree(trace: List[Any]) -> Dict[str, Any]:
    """Extract a simple causal graph from a linear reasoning trace.

    We treat each step (string or dict with 'step' or 'text') as a node and
    connect consecutive steps with directed edges to form a path graph.

    The function persists the graph under evaluation/causal_graph.json and
    returns a summary including basic causal metrics.
    """
    steps: List[str] = []
    for i, t in enumerate(trace):
        if isinstance(t, str):
            s = t.strip()
        elif isinstance(t, dict):
            s = str(t.get("step") or t.get("text") or f"step_{i}").strip()
        else:
            s = f"step_{i}"
        if not s:
            s = f"step_{i}"
        steps.append(s)

    # Deduplicate node labels while preserving order
    seen = set()
    nodes: List[str] = []
    for s in steps:
        if s not in seen:
            nodes.append(s)
            seen.add(s)

    # Edges between consecutive steps (original sequence)
    edges: List[Tuple[str, str]] = []
    for a, b in zip(steps, steps[1:]):
        edges.append((a, b))

    graph = CausalGraph(nodes=nodes, edges=edges)
    CAUSAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    CAUSAL_PATH.write_text(json.dumps(graph.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    metrics = {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "avg_path_length": float(len(edges)) if nodes else 0.0,
    }

    payload = {"graph_path": str(CAUSAL_PATH), "metrics": metrics}
    log_causal_analysis(payload)
    return payload


__all__ = ["explain_decision_tree", "CAUSAL_PATH"]
