from __future__ import annotations

import json
from services.autogen.bridge import AutoGenBridge


def test_autogen_bridge_run_basic():
    bridge = AutoGenBridge()
    res = bridge.run("sample task")
    assert isinstance(res, dict)
    assert res.get("ok") is True
    data = res.get("data") or {}
    assert "run_id" in data and "summary" in data
    # summary should be deterministic string
    assert isinstance(data["summary"], str) and len(data["summary"]) > 0
