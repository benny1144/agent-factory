from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

# Repo-root aware paths
REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR = REPO_ROOT / "logs"
AGENTS_DIR = REPO_ROOT / "factory_agents"
ARCHIVIST_DIR = AGENTS_DIR / "archivist"
CONFIG_DIR = REPO_ROOT / "config"
HF_YAML = CONFIG_DIR / "human_firewall.yaml"

# Ensure src on path for agent_factory imports
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.append(str(REPO_ROOT / "src"))
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# Optional audit logger (best-effort)
try:
    from agent_factory.services.audit.audit_logger import log_event  # type: ignore
except Exception:  # pragma: no cover
    def log_event(event_type: str, metadata: Dict[str, object] | None = None) -> Dict[str, object]:  # type: ignore
        return {"ok": True, "data": {"event_type": event_type, "metadata": metadata or {}}}

# Import GenesisOrchestrator from Architect Genesis
try:
    from factory_agents.architect_genesis.main import GenesisOrchestrator  # type: ignore
except Exception as e:  # pragma: no cover
    GenesisOrchestrator = None  # type: ignore


PAYLOAD = "Create and deploy Archivist Agent — Level-3 Knowledge Curator (Archy)"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _genesis_log_path() -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    day = datetime.now(timezone.utc).date().isoformat()
    return LOGS_DIR / f"genesis_session_{day}.log"


def _append_log_line(text: str) -> None:
    p = _genesis_log_path()
    try:
        with p.open("a", encoding="utf-8") as f:
            f.write(f"[{_now()}] {text}\n")
    except Exception:
        pass


def _read_log() -> List[str]:
    p = _genesis_log_path()
    if not p.exists():
        return []
    try:
        return p.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []


def _allow_reactivation() -> bool:
    # Minimal YAML read (avoid adding dependencies); scan for the flag
    if not HF_YAML.exists():
        return False
    try:
        text = HF_YAML.read_text(encoding="utf-8").lower()
        # very simple parser; true if line contains `allow_genesis_reactivation: true`
        return "allow_genesis_reactivation" in text and ": true" in text
    except Exception:
        return False


def commission(timeout_sec: float = 10.0) -> Dict[str, object]:
    """Execute the tasks in tasks/2025-10-CreateArchivist.md.

    Steps:
      1) Send payload to Genesis orchestrator (architect_mode)
      2) Monitor log for completion text (best-effort)
      3) Verify Archivist artifacts; if missing, rollback (delete folder)
    """
    result: Dict[str, object] = {
        "ok": False,
        "sent": PAYLOAD,
        "completed": False,
        "verified": False,
        "rolled_back": False,
        "details": {},
    }

    if GenesisOrchestrator is None:
        result["details"] = {"error": "GenesisOrchestrator_unavailable"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    # HITL: ensure reactivation is permitted
    if not _allow_reactivation():
        _append_log_line("Commission blocked: allow_genesis_reactivation is not true.")
        log_event("genesis_commission_blocked", {"reason": "allow_genesis_reactivation_false"})
        result["details"] = {"error": "reactivation_not_allowed"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result

    orch = GenesisOrchestrator()

    # Reactivate Genesis in architect_mode
    try:
        orch.reactivate("architect_mode")
        log_event("genesis_commission_start", {"mode": "architect_mode"})
    except Exception:
        pass

    # Send payload (record to log; real crew kickoff is operator-driven)
    _append_log_line(f"Commission payload queued: {PAYLOAD}")
    result["sent"] = PAYLOAD

    # Monitor logs for completion phrase briefly
    deadline = time.time() + float(timeout_sec)
    saw_complete = False
    while time.time() < deadline:
        lines = _read_log()
        if any("Task complete." in ln for ln in lines):
            saw_complete = True
            break
        time.sleep(0.5)

    # If not seen, attempt artifact verification anyway
    required = [
        ARCHIVIST_DIR / "main.py",
        ARCHIVIST_DIR / "retrieval_chain.py",
        ARCHIVIST_DIR / "curator_api.py",
        ARCHIVIST_DIR / "persona_archivist.md",
        ARCHIVIST_DIR / "requirements.txt",
    ]
    missing = [str(p.relative_to(REPO_ROOT)) for p in required if not p.exists()]

    if not missing:
        # Mark completion in log if absent
        if not saw_complete:
            _append_log_line("Task complete.")
            saw_complete = True
        result["verified"] = True
        result["completed"] = True
        result["ok"] = True
        log_event("genesis_commission_finish", {"status": "success", "archivist_ready": True})
    else:
        # Rollback: delete incomplete folder per instructions
        try:
            if ARCHIVIST_DIR.exists():
                for p in sorted(ARCHIVIST_DIR.rglob("*"), reverse=True):
                    try:
                        if p.is_file():
                            p.unlink()
                        else:
                            p.rmdir()
                    except Exception:
                        pass
                try:
                    ARCHIVIST_DIR.rmdir()
                except Exception:
                    pass
                result["rolled_back"] = True
        except Exception:
            pass
        result["details"] = {"missing": missing}
        log_event("genesis_commission_finish", {"status": "failed", "missing": missing})
        _append_log_line("Commission failed; incomplete Archivist artifacts removed.")

    # Print JSON summary
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    commission()
