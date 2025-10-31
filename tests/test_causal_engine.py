from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / 'src'))

from evaluation.evaluation_engine import explain_decision_tree, CAUSAL_PATH  # type: ignore


def test_explain_decision_tree_writes_graph(tmp_path, monkeypatch):
    # Redirect evaluation path to temp dir by monkeypatching CAUSAL_PATH parent via cwd
    # Instead, we call explain and check file exists at default path (under repo), then cleanup not required in CI
    trace = [
        {"step": "research"},
        {"step": "charter"},
        {"step": "code"},
        {"step": "critique"},
    ]
    out = explain_decision_tree(trace)
    assert 'metrics' in out and out['metrics']['node_count'] >= 4
    p = Path(out['graph_path'])
    assert p.exists(), f"causal graph not written at {p}"
