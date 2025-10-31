from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure repo-root import for utils.*
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from utils.firewall_protocol import risk_score, evaluate_risk_before_action, EscalationLevel  # type: ignore


def test_risk_score_low():
    res = risk_score(confidence=0.95, criticality="low", sensitivity="public")
    assert 0.0 <= res["score"] <= 1.0
    assert res["tier"] in (EscalationLevel.HOOTL, EscalationLevel.HOTL)
    # With very high confidence and low/ public, expect HOOTL
    assert res["tier"] == EscalationLevel.HOOTL


def test_risk_score_medium():
    res = risk_score(confidence=0.6, criticality="medium", sensitivity="internal")
    # Expected blended score ~0.46 -> HOTL
    assert res["tier"] == EscalationLevel.HOTL


def test_risk_score_high():
    res = risk_score(confidence=0.2, criticality="high", sensitivity="restricted")
    assert res["tier"] == EscalationLevel.HITL


def test_evaluate_risk_before_action_persona_floor(monkeypatch):
    # Persona default is HOTL per repo personas/risk_matrix.json for Architect
    monkeypatch.setenv("AGENT_PERSONA", "Architect")
    # Force a low score scenario; persona floor can keep it at least HOTL
    out = evaluate_risk_before_action({
        "goal": "demo", "action": "x", "actor": "y",
        "llm_confidence": 0.99,
        "criticality": "low",
        "sensitivity": "public",
    })
    assert out["tier"] in (EscalationLevel.HOOTL, EscalationLevel.HOTL)
