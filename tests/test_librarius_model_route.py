from __future__ import annotations

from agents.model_router import ModelRouter


def test_librarius_route() -> None:
    router = ModelRouter(agent_name="Librarius")
    meta = {"risk": "low", "tokens": 2000, "task_id": "lib-test-001"}
    res = router.route(meta, "Summarize the purpose of the HoloForge lattice.")
    assert "output" in res and "model" in res
