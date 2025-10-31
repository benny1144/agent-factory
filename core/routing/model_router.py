from __future__ import annotations

import os
import json
import datetime
from pathlib import Path
from typing import Any, Dict, Tuple

# OpenAI SDK v1 style client
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

LOG_PATH = Path("logs/compliance/model_usage.jsonl")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


class ModelRouter:
    """Selects GPT-5/ChatGPT models based on task metadata, with Orion governance logging.

    route_to_model(metadata) -> (client, model)
      - client: OpenAI client instance (or None if SDK unavailable)
      - model: selected model string
    """

    MODEL_COSTS: Dict[str, float] = {
        "gpt-5-pro": 0.02,
        "gpt-5-mini": 0.004,
        "gpt-5-nano": 0.001,
        "gpt-oss-safeguard": 0.000,
    }

    def route_to_model(self, metadata: Dict[str, Any]) -> Tuple[Any, str]:
        risk = metadata.get("risk", "low")
        tokens = metadata.get("tokens", 1000)
        budget = metadata.get("budget", None)
        confidential = metadata.get("confidential", False)

        if confidential:
            model = "gpt-oss-safeguard"
        elif risk == "high":
            model = "gpt-5-pro"
        elif budget is not None and budget < self.MODEL_COSTS["gpt-5-mini"]:
            model = "gpt-5-nano"
        elif tokens and int(tokens) > 8000:
            model = "gpt-5-pro"
        else:
            model = "gpt-5-mini"

        self._log_routing(model, metadata)

        api_key = os.getenv("OPENAI_API_KEY", "")
        client = OpenAI(api_key=api_key) if (OpenAI and api_key) else None  # type: ignore
        return client, model

    # ---------------- Internal ---------------- #
    def _log_routing(self, model: str, metadata: Dict[str, Any]) -> None:
        entry = {
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "agent": metadata.get("agent", "unknown"),
            "task_id": metadata.get("task_id", "n/a"),
            "model": model,
            "budget": metadata.get("budget"),
            "risk": metadata.get("risk", "low"),
            "confidential": bool(metadata.get("confidential", False)),
        }
        try:
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:  # pragma: no cover
            pass
