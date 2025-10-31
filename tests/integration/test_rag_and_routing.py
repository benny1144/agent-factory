from __future__ import annotations

import pytest

from core.tools.holo_forge_tool import HoloForgeSearchTool
from core.routing.model_router import ModelRouter


def test_rag_and_routing(monkeypatch):
    # Setup
    tool = HoloForgeSearchTool(host="localhost", api_key="dummy", collection="test")
    router = ModelRouter()

    # Mock search output
    def fake_search(*a, **kw):
        return {"results": [{"text": "context A"}], "latency_ms": 12}

    monkeypatch.setattr(tool, "run", fake_search)

    metadata = {"risk": "low", "tokens": 1200, "agent": "ArchyValidator", "task_id": "T001"}
    result = tool.run(None, metadata)
    assert "results" in result

    _client, model = router.route_to_model(metadata)
    assert model in ["gpt-5-mini", "gpt-5-pro", "gpt-5-nano", "gpt-oss-safeguard"]
