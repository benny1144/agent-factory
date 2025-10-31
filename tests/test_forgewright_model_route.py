from __future__ import annotations

from agents.model_router import ModelRouter


def test_forgewright_route() -> None:
    router = ModelRouter(agent_name="Forgewright")
    meta = {"risk": "low", "tokens": 1200, "task_id": "fw-test-001"}
    res = router.route(meta, "Generate a function that reverses a string.")
    assert "output" in res and "model" in res
