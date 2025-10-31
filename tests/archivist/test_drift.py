from __future__ import annotations
import sys
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factory_agents.archivist.reasoning_core import compute_persona_drift  # type: ignore


def test_compute_persona_drift_basic():
    res = compute_persona_drift("This is a short test content about archivist behavior and governance.")
    assert isinstance(res, dict)
    assert "score" in res and "level" in res
    # score in [0,1] for jaccard, or cosine in [-1,1] for embeddings/local; clamp check
    assert -1.0 <= float(res["score"]) <= 1.0
