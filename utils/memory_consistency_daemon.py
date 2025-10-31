from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

try:
    # Repo-root aware imports (pytest.ini adds src to pythonpath)
    from utils.procedural_memory_pg import (
        init_db,
        session_scope,
        knowledge_ingest,
        memory_events,
        select_all,
    )
    from agent_factory.services.audit.audit_logger import log_memory_consistency, log_event
except Exception:  # pragma: no cover - for static linters
    init_db = None  # type: ignore
    session_scope = None  # type: ignore
    knowledge_ingest = None  # type: ignore
    memory_events = None  # type: ignore
    select_all = None  # type: ignore
    def log_memory_consistency(details: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
        return {"ok": True, "data": details}
    def log_event(event_type: str, metadata: Dict[str, Any] | None = None) -> Dict[str, Any]:  # type: ignore
        return {"ok": True, "data": {"event_type": event_type, "metadata": metadata or {}}}


@dataclass
class ConsistencyReport:
    coherence: float
    ingest_total: int
    memory_inserts: int
    corrections: int
    details: Dict[str, Any]


def _compute_coherence() -> Tuple[float, int, int, Dict[str, Any]]:
    """Compute a coarse coherence metric between ingests and memory inserts.

    We aggregate:
      - total ingested vector_count from knowledge_ingest
      - total memory insert events from memory_events (event_type == 'insert')
    Returns (coherence_ratio, ingest_total, memory_inserts, detail_dict)
    """
    eng = init_db()
    # Sum ingested vectors
    ingest_total = 0
    ing_rows = select_all(knowledge_ingest, eng)
    for r in ing_rows:
        ingest_total += int(r.get("vector_count", 0) or 0)

    # Count memory insert events
    mem_rows = select_all(memory_events, eng)
    inserts = [r for r in mem_rows if str(r.get("event_type")) == "insert"]
    memory_inserts = len(inserts)

    coherence = 1.0
    if ingest_total > 0:
        # Ratio of observed memory inserts to expected ingested chunks
        coherence = max(0.0, min(1.0, memory_inserts / float(ingest_total)))

    details = {
        "ingest_total": ingest_total,
        "memory_insert_events": memory_inserts,
    }
    return coherence, ingest_total, memory_inserts, details


def check_once(threshold: float = 0.85) -> ConsistencyReport:
    """Run one consistency check and perform a stub correction if below threshold.

    If coherence < threshold, we emit an audit event with action='rebuild' and do a no-op
    correction (stub) to keep the system deterministic in CI.
    """
    coherence, ing_total, mem_ins, details = _compute_coherence()
    corrections = 0
    action = "check"
    if coherence < threshold:
        action = "rebuild"
        corrections = 1
    log_memory_consistency({
        "action": action,
        "coherence": coherence,
        "threshold": threshold,
        **details,
    })
    return ConsistencyReport(coherence, ing_total, mem_ins, corrections, {"action": action, **details})


def main() -> None:
    parser = argparse.ArgumentParser(description="Memory Consistency Daemon")
    parser.add_argument("--threshold", type=float, default=float(os.getenv("REFLECTIVE_COHERENCE_THRESHOLD", "0.85")))
    ns = parser.parse_args()

    enable = os.getenv("ENABLE_REFLECTIVE_DAEMON", "false").lower() == "true"
    if not enable:
        log_memory_consistency({"action": "disabled", "reason": "ENABLE_REFLECTIVE_DAEMON=false"})
        print("[CONSISTENCY] daemon disabled via config")
        return

    rep = check_once(threshold=ns.threshold)
    print(json.dumps({
        "coherence": rep.coherence,
        "ingest_total": rep.ingest_total,
        "memory_inserts": rep.memory_inserts,
        "corrections": rep.corrections,
    }))


if __name__ == "__main__":
    main()
