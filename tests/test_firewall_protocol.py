from __future__ import annotations

import builtins
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from utils.firewall_protocol import require_hitl, EscalationLevel


def test_require_hitl_hotl(monkeypatch):
    calls = {"ran": False}

    @require_hitl
    def risky():
        calls["ran"] = True
        return 42

    monkeypatch.setenv("ESCALATION_LEVEL", EscalationLevel.HOTL)
    monkeypatch.setenv("HITL_APPROVE", "true")

    assert risky() == 42
    assert calls["ran"] is True


def test_require_hitl_hitl_blocks_without_approval(monkeypatch):
    calls = {"ran": False}

    @require_hitl
    def risky():
        calls["ran"] = True
        return 7

    monkeypatch.setenv("ESCALATION_LEVEL", EscalationLevel.HITL)
    monkeypatch.setenv("HITL_APPROVE", "false")

    def fake_input(prompt: str) -> str:
        return "deny"

    monkeypatch.setattr(builtins, "input", fake_input)

    try:
        risky()
        assert False, "Expected PermissionError"
    except PermissionError:
        pass
    assert calls["ran"] is False
