from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# Optional GCP/OTEL integrations (graceful if not installed)
try:  # Google Cloud Logging
    from google.cloud import logging as gcp_logging  # type: ignore
except Exception:  # pragma: no cover - optional
    gcp_logging = None  # type: ignore

try:  # OpenTelemetry logs
    from opentelemetry import trace  # type: ignore
    from opentelemetry.trace import get_tracer  # type: ignore
except Exception:  # pragma: no cover - optional
    trace = None  # type: ignore
    get_tracer = None  # type: ignore


_AUDIT_LOGGER_NAME = "agent_factory.audit"
_logger: Optional[logging.Logger] = None


def _ensure_logger() -> logging.Logger:
    global _logger
    if _logger:
        return _logger

    logger = logging.getLogger(_AUDIT_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # don't duplicate in root

    if not logger.handlers:
        stream = logging.StreamHandler(stream=sys.stdout)
        stream.setLevel(logging.INFO)
        # Keep formatter simple; we output pre-formatted JSON string
        formatter = logging.Formatter("%(message)s")
        stream.setFormatter(formatter)
        logger.addHandler(stream)

        # Attach Google Cloud Logging handler if available and configured
        if gcp_logging and os.getenv("GCP_PROJECT_ID"):
            try:
                gcp_client = gcp_logging.Client(project=os.getenv("GCP_PROJECT_ID"))
                gcp_client.setup_logging(log_level=logging.INFO)
            except Exception:
                # Best-effort; we keep stdout logs regardless
                pass

    _logger = logger
    return logger


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _make_event(event_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    trace_id = str(uuid.uuid4())
    project_id = os.getenv("GCP_PROJECT_ID")
    ts = _now_iso()
    payload: Dict[str, Any] = {
        "ok": True,
        "data": {
            "event_type": event_type,
            "metadata": metadata or {},
        },
        "error": None,
        "meta": {
            "source": "audit_logger",
            "trace_id": trace_id,
            "project_id": project_id,
            "ts": ts,
            "duration_ms": None,
        },
    }
    return payload


def log_event(event_type: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Log a structured audit event.

    Args:
        event_type: Short type string (e.g., "agent_run", "tool_creation").
        metadata: Arbitrary extra data, JSON-serializable.

    Returns:
        The structured event dict that was logged.
    """
    logger = _ensure_logger()
    event = _make_event(event_type, metadata or {})

    # If OTEL is available, create a span context with the trace id.
    if get_tracer and trace:
        try:  # pragma: no cover - optional integration
            tracer = get_tracer(__name__)
            with tracer.start_as_current_span(event_type) as span:
                span.set_attribute("audit.trace_id", event["meta"]["trace_id"])
                span.set_attribute("audit.event_type", event_type)
                for k, v in (metadata or {}).items():
                    # Only set simple types to avoid exporter issues
                    if isinstance(v, (str, int, float, bool)) or v is None:
                        span.set_attribute(f"audit.meta.{k}", v)
        except Exception:
            pass

    try:
        json_str = json.dumps(event, ensure_ascii=False)
    except Exception as e:
        # Fallback to minimal message
        json_str = json.dumps({
            "ok": False,
            "error": f"serialization_error: {e}",
            "data": {"event_type": event_type}
        }, ensure_ascii=False)

    logger.info(f"[AUDIT] {json_str}")

    # Mirror to JSONL file with rotation via tools.log_utils (best-effort)
    try:
        from pathlib import Path
        from datetime import datetime as _dt, timezone as _tz
        logs_dir = Path(os.getenv("LOGS_DIR") or (Path(__file__).resolve().parents[4] / "logs"))
        logs_dir.mkdir(parents=True, exist_ok=True)
        day = _dt.now(_tz.utc).date().isoformat()
        jsonl_path = logs_dir / f"audit_{day}.jsonl"
        try:
            from tools.log_utils import append_jsonl  # type: ignore
            append_jsonl(jsonl_path, event)
        except Exception:
            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(json_str + "\n")
        # Update simple index under compliance/audit_log
        idx_dir = Path(__file__).resolve().parents[4] / "compliance" / "audit_log"
        idx_dir.mkdir(parents=True, exist_ok=True)
        idx = idx_dir / "log_index.txt"
        line = f"{day},{jsonl_path.as_posix()}\n"
        try:
            if not idx.exists() or line not in idx.read_text(encoding="utf-8"):
                with open(idx, "a", encoding="utf-8") as f:
                    f.write(line)
        except Exception:
            pass
    except Exception:
        pass

    return event


def log_tool_creation(tool_name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    meta = {"tool_name": tool_name}
    if metadata:
        meta.update(metadata)
    return log_event("tool_creation", meta)


def log_knowledge_ingest(file_name: str, chunk_count: int) -> Dict[str, Any]:
    meta = {"file_name": file_name, "chunk_count": int(chunk_count)}
    return log_event("knowledge_ingest", meta)


def log_agent_run(agent_name: str, task_id: Optional[str], status: str) -> Dict[str, Any]:
    meta = {"agent_name": agent_name, "task_id": task_id, "status": status}
    return log_event("agent_run", meta)


def log_memory_consistency(details: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to log memory consistency daemon events.

    Args:
        details: Payload with fields like {"action": "rebuild|check", "coherence": float, ...}
    """
    return log_event("memory_consistency", details or {})


def log_causal_analysis(details: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to log causal analysis results from the evaluation engine."""
    return log_event("causal_analysis", details or {})


__all__ = [
    "log_event",
    "log_tool_creation",
    "log_knowledge_ingest",
    "log_agent_run",
    "log_memory_consistency",
    "log_causal_analysis",
]