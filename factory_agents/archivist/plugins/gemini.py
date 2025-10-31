from __future__ import annotations
from typing import Any, Dict

def generate(prompt: str, **opts: Any) -> Dict[str, Any]:
    # Deterministic stub — replace with real Gemini call when enabled
    text = f"[Gemini] Echo: {prompt[:2000]}"
    return {"ok": True, "model": "gemini/stub", "text": text, "tokens": len(prompt.split()), "finish_reason": "stop"}
