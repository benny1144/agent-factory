from __future__ import annotations
from typing import Any, Dict

# Normalized response schema:
# {"ok": true, "model": "openai/stub", "text": "...", "tokens": 0, "finish_reason": "stop"}

def generate(prompt: str, **opts: Any) -> Dict[str, Any]:
    # Deterministic stub — replace with real OpenAI call when enabled
    text = f"[OpenAI] Echo: {prompt[:2000]}"
    return {"ok": True, "model": "openai/stub", "text": text, "tokens": len(prompt.split()), "finish_reason": "stop"}
