# repo-root: audit_logger.py
from typing import Any, Dict


def _fmt(tag: str, fields: Dict[str, Any]) -> str:
    kv = " ".join(f"{k}={repr(v)}" for k, v in fields.items())
    return f"[AUDIT] {tag} {kv}"


def log_agent_run(agent: str, **fields):
    line = _fmt("agent_run", {"agent": agent, **fields})
    print(line, flush=True)
    return line


def log_tool_creation(tool: str, fields: Dict[str, Any] | None = None):
    line = _fmt("tool_creation", {"tool": tool, **(fields or {})})
    print(line, flush=True)
    return line


def log_knowledge_ingest(source: str, count: int):
    line = _fmt("knowledge_ingest", {"source": source, "count": count})
    print(line, flush=True)
    return line
