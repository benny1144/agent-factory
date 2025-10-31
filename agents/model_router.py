from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import requests
from dotenv import load_dotenv

# Load env once at import time (safe for local dev). In CI, env is set via runner.
load_dotenv()

# Repo-aware paths (fallback to relative if utils not available)
try:
    from utils.paths import PROJECT_ROOT
except Exception:  # pragma: no cover - defensive fallback
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

LOG_PATH = PROJECT_ROOT / "logs" / "compliance" / "model_usage.jsonl"
EVENT_BUS = PROJECT_ROOT / "governance" / "event_bus.jsonl"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
EVENT_BUS.parent.mkdir(parents=True, exist_ok=True)


class ModelRouter:
    """Centralized model router for Agent Factory (v1.1).

    Features:
    - Deterministic model selection from task metadata (risk, tokens, budget, confidential, purpose).
    - Supports OpenAI (chat.completions) and local OSS endpoint (Ollama-compatible JSON API).
    - Emits governance-compliant usage logs to logs/compliance/model_usage.jsonl.
    - Mirrors summary events to governance/event_bus.jsonl for Watchtower dashboards.
    - Secure key management via environment variables loaded through python-dotenv.
    """

    MODEL_COSTS: Dict[str, float] = {
        # Standardized ChatGPT suite
        "gpt-4o": 0.015,
        "gpt-4o-mini": 0.006,
        "gpt-4-turbo": 0.012,
        # Legacy placeholders (kept for backward compatibility)
        "gpt-5-pro": 0.02,
        "gpt-5": 0.01,
        "gpt-5-mini": 0.004,
        "gpt-5-nano": 0.001,
        # Local
        "gpt-oss": 0.0,
        "gpt-oss-safeguard": 0.0,
    }

    MODEL_KEY_MAP: Dict[str, str | None] = {
        # OpenAI scopes (fallback to OPENAI_API_KEY). No secrets are written to disk.
        "gpt-4o": os.getenv("OPENAI_KEY_MANAGER") or os.getenv("OPENAI_API_KEY"),
        "gpt-4o-mini": os.getenv("OPENAI_KEY_SAFE") or os.getenv("OPENAI_API_KEY"),
        "gpt-4-turbo": os.getenv("OPENAI_KEY_WORKER") or os.getenv("OPENAI_API_KEY"),
        # Legacy
        "gpt-5-pro": os.getenv("OPENAI_KEY_MANAGER") or os.getenv("OPENAI_API_KEY"),
        "gpt-5": os.getenv("OPENAI_KEY_WORKER") or os.getenv("OPENAI_API_KEY"),
        "gpt-5-mini": os.getenv("OPENAI_KEY_SAFE") or os.getenv("OPENAI_API_KEY"),
        "gpt-5-nano": os.getenv("OPENAI_KEY_SAFE") or os.getenv("OPENAI_API_KEY"),
        # Local
        "gpt-oss": "local",
        "gpt-oss-safeguard": "local",
    }

    LOCAL_ENDPOINT: str = os.getenv("GPT_OSS_ENDPOINT", "http://localhost:11434/api/generate")

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name

    # ---------------- Selection Logic ---------------- #
    def select(self, metadata: Dict[str, Any]) -> str:
        """Select appropriate model based on metadata.

        Args:
            metadata: Dict with optional keys: risk, tokens, confidential, budget, purpose, force_model.
        """
        # Allow explicit override
        force_model = metadata.get("force_model")
        if isinstance(force_model, str) and force_model:
            return force_model

        # Purpose-aware mapping (Phase 38.5 standardization)
        purpose = str(metadata.get("purpose", "")).lower()
        if purpose in {"reflective", "reflection", "summary_reflective"}:
            return os.getenv("OPENAI_MODEL_REFLECTIVE", "gpt-4o-mini")
        if purpose in {"ethics", "policy", "policy_diff"}:
            return os.getenv("OPENAI_MODEL_ETHICS", "gpt-4-turbo")
        if purpose in {"summary", "narrative", "watchtower_narrative"}:
            return os.getenv("OPENAI_MODEL_SUMMARY", "gpt-4o")
        if purpose in {"health", "self-check", "healthcheck"}:
            return os.getenv("OPENAI_MODEL_REFLECTIVE", "gpt-4o-mini")

        # Prefer GPT-5 mini stack for specific agents per Phase 38.6–38.7
        agent = (self.agent_name or "").strip()
        if agent in {"Forgewright", "Librarius"}:
            if bool(metadata.get("confidential", False)):
                return "gpt-oss-safeguard"
            return "gpt-5-mini"

        # Heuristics
        risk = str(metadata.get("risk", "low")).lower()
        tokens = int(metadata.get("tokens", 1000) or 1000)
        confidential = bool(metadata.get("confidential", False))
        budget = metadata.get("budget")
        budget = float("inf") if budget is None else float(budget)

        if confidential:
            return "gpt-oss-safeguard"
        if risk == "high":
            return "gpt-4-turbo"
        if tokens > 8000:
            return "gpt-4o"
        # Use mini when very tight budget threshold
        if budget < self.MODEL_COSTS.get("gpt-4o-mini", 0.006):
            return "gpt-4o-mini"
        # Default lightweight
        return "gpt-4o-mini"

    # ---------------- Routing Core ---------------- #
    def route(self, metadata: Dict[str, Any], prompt: str) -> Dict[str, Any]:
        """Route prompt to selected model and emit logs/events.

        Returns a dict: {"model": <name>, "output": <string|error>}.
        """
        model = self.select(metadata)
        key_scope = self.MODEL_KEY_MAP.get(model, "local")
        output: str

        try:
            if str(model).startswith("gpt-oss"):
                output = self._call_local_model(prompt)
            else:
                output = self._call_openai(model, key_scope or "", prompt)
        except Exception as e:  # pragma: no cover - defensive
            output = f"[Router error]: {e}"
            self._log_event("router_error", {"error": str(e), "model": model})

        # Governance logs
        self._log_usage(model, key_scope, metadata)
        self._emit_event(model, metadata)
        return {"model": model, "output": output}

    # ---------------- API Calls ---------------- #
    def _call_openai(self, model: str, key: str, prompt: str) -> str:
        """Call OpenAI API. Uses SDK v1 style if available; otherwise fallback to HTTP."""
        if not key:
            return "[Error] OPENAI_API_KEY not set"
        try:
            import openai  # type: ignore
        except Exception:
            # Minimal HTTP fallback if SDK not present
            try:
                url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
                headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                }
                resp = requests.post(url, headers=headers, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                # Try both dict access styles to support SDK-like responses
                msg = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                return str(msg)
            except Exception as e:  # pragma: no cover - network path may be blocked in CI
                self._log_event("model_fallback", {"error": str(e), "model": model})
                return f"[Error calling {model}]: {e}"

        # SDK path
        try:
            openai.api_key = key  # type: ignore[attr-defined]
            completion = openai.chat.completions.create(  # type: ignore[attr-defined]
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            # Newer SDK returns objects; support both mapping and attr styles
            try:
                # object-like
                return completion.choices[0].message["content"]  # type: ignore[index]
            except Exception:
                # mapping-like
                first = completion.get("choices", [{}])[0]
                msg = first.get("message", {}).get("content", "")
                return str(msg)
        except Exception as e:
            self._log_event("model_fallback", {"error": str(e), "model": model})
            return f"[Error calling {model}]: {e}"

    def _call_local_model(self, prompt: str) -> str:
        """Send prompt to local OSS model endpoint (e.g., Ollama generate)."""
        try:
            res = requests.post(self.LOCAL_ENDPOINT, json={"prompt": prompt}, timeout=30)
            res.raise_for_status()
            body = res.json()
            return str(body.get("response") or body.get("text") or "")
        except Exception as e:
            self._log_event("model_fallback", {"error": str(e), "model": "gpt-oss"})
            return f"[Local model error]: {e}"

    # ---------------- Governance Logging ---------------- #
    def _log_usage(self, model: str, key_scope: str | None, metadata: Dict[str, Any]) -> None:
        entry = {
            "trace_id": uuid.uuid4().hex,
            "timestamp": datetime.utcnow().isoformat(),
            "agent": self.agent_name,
            "model": model,
            "key_scope": ("local" if key_scope == "local" else ("scoped_key" if key_scope else "none")),
            "phase": metadata.get("phase", "untracked"),
            "task_id": metadata.get("task_id", "unknown"),
            "risk": metadata.get("risk", "low"),
            "confidential": bool(metadata.get("confidential", False)),
            "budget": metadata.get("budget"),
            "requires_hitl": bool(metadata.get("human_firewall", False)),
        }
        try:
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _emit_event(self, model: str, metadata: Dict[str, Any]) -> None:
        event = {
            "type": "model_usage",
            "agent": self.agent_name,
            "model": model,
            "ts": datetime.utcnow().isoformat(),
            "trace_id": metadata.get("task_id", uuid.uuid4().hex),
            "status": "ok",
        }
        try:
            with EVENT_BUS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _log_event(self, event_type: str, details: Dict[str, Any]) -> None:
        event = {
            "type": event_type,
            "agent": self.agent_name,
            "details": details,
            "ts": datetime.utcnow().isoformat(),
        }
        try:
            with EVENT_BUS.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception:
            pass


if __name__ == "__main__":
    # Local smoke test without network: prefers OSS endpoint and logs to files.
    router = ModelRouter(agent_name="TestAgent")
    result = router.route({"risk": "low", "tokens": 1200, "phase": "sandbox-test"}, "Hello world!")
    print(json.dumps(result, indent=2))
