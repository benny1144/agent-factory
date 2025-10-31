from __future__ import annotations

import os
from factory_agents.archivist.reasoning_core import llm_generate


def test_llm_generate_local_offline(monkeypatch):
    # Ensure no network providers are considered enabled
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("ALLOW_NETWORK_LLM", "0")

    res = llm_generate("Hello, world.")
    assert isinstance(res, dict)
    assert res.get("ok") is True
    data = res.get("data") or {}
    assert "text" in data
    meta = res.get("meta") or {}
    assert meta.get("provider") in {"local", "openai", "gemini", "groq"}
