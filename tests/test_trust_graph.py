from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / 'src'))

from federation.trust_graph import TrustGraph  # type: ignore


def test_trust_reconcile_reduces_weight_on_divergence():
    tg = TrustGraph()
    # Two nodes with opposite vectors to produce low cosine similarity
    tg.add_node("genesis_a", [1.0, 0.0, 0.0])
    tg.add_node("genesis_b", [-1.0, 0.0, 0.0])
    tg.add_attestation("genesis_a", "genesis_b", weight=0.9, signature="sig")

    out = tg.reconcile_drift(threshold=0.95)
    assert isinstance(out, dict)
    assert out["changes"], "Expected at least one trust change due to divergence"
    ch = out["changes"][0]
    assert ch["old"] > ch["new"], "Weight should be reduced when similarity falls below threshold"
