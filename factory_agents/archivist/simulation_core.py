# Autonomous Crew Simulation Sandbox (Phase 10)
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any

# Optional risk logger from reasoning core (Phase 11 integration)
try:
    from factory_agents.archivist import reasoning_core as _rc
except Exception:  # pragma: no cover - keep sandbox resilient
    _rc = None  # type: ignore

# Error redaction helper (Phase 38.5)
_DEF_LOG = (Path(__file__).resolve().parents[2] / "logs" / "simulations" / "errors.log")
_DEF_LOG.parent.mkdir(parents=True, exist_ok=True)

def _redact_err(e: Exception) -> str:
    return f"{type(e).__name__}: {str(e)[:200]} (trace redacted)"

def _log_error(msg: str) -> None:
    try:
        _DEF_LOG.write_text((_DEF_LOG.read_text(encoding="utf-8") if _DEF_LOG.exists() else "") + msg + "\n", encoding="utf-8")
    except Exception:
        pass


@dataclass
class Agent:
    name: str
    style: str

    def utter(self, topic: str, round_idx: int) -> str:
        # Deterministic, local-only stub (no network/LLM calls by default)
        if self.name == "Strategist":
            return f"Round {round_idx}: Strategic framing for '{topic}'. Key objectives, risks, and success criteria."
        if self.name == "Engineer":
            return f"Round {round_idx}: Engineering plan for '{topic}'. Steps, data paths, and safety constraints."
        if self.name == "Philosopher":
            return f"Round {round_idx}: Ethical reflection on '{topic}'. Trade-offs, alignment, and governance."
        return f"Round {round_idx}: Contribution from {self.name} on '{topic}'."


class AutonomousCrew:
    """Deterministic autonomous crew simulator (text-only sandbox)."""

    def __init__(self) -> None:
        self.agents = [
            Agent("Strategist", "plans"),
            Agent("Engineer", "builds"),
            Agent("Philosopher", "questions"),
        ]
        self.logs_dir = Path(__file__).resolve().parents[2] / "logs" / "simulations" / "autonomous"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def simulate_autonomous_crew(self, topic: str, rounds: int = 3) -> str:
        ts = datetime.now(timezone.utc).isoformat()
        transcript: List[Dict[str, Any]] = []
        try:
            # Risk log (Phase 11)
            if _rc is not None:
                try:
                    _rc.risk_assess("simulate", f"topic={topic}; rounds={rounds}")
                except Exception:
                    pass

            md_lines: List[str] = [
                f"🜂 **Autonomous Crew Simulation**",
                f"## Topic: {topic}",
                f"Timestamp: {ts}",
                "",
            ]
            for r in range(1, max(1, rounds) + 1):
                md_lines.append(f"### Round {r}")
                for agent in self.agents:
                    text = agent.utter(topic, r)
                    md_lines.append(f"- **{agent.name}**: {text}")
                    transcript.append({
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "round": r,
                        "agent": agent.name,
                        "content": text,
                    })
                md_lines.append("")

            # Simple synthesis
            md_lines.append("## Summary")
            md_lines.append(
                "The crew produced a strategy, an engineering plan, and an ethical review. "
                "Use this as a sandbox artifact; extend with LLM reasoning behind a governance flag if desired."
            )

            # Store transcript JSON
            out = {
                "topic": topic,
                "rounds": rounds,
                "timestamp": ts,
                "transcript": transcript,
            }
            fname = f"sim_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
            (self.logs_dir / fname).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

            # Return Markdown result
            return "\n".join(md_lines)
        except Exception as e:
            _log_error(_redact_err(e))
            return f"[SimulationError] {_redact_err(e)}"
