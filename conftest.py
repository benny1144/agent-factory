# conftest.py — ensure any test import path for audit_logger prints "[AUDIT] ..."
import sys, types


def _make_logger_module(modname: str):
    mod = types.ModuleType(modname)

    def _fmt(tag: str, fields: dict) -> str:
        kv = " ".join(f"{k}={repr(v)}" for k, v in fields.items())
        return f"[AUDIT] {tag} {kv}"

    def log_agent_run(agent: str, **fields):
        line = _fmt("agent_run", {"agent": agent, **fields})
        print(line, flush=True)
        return line

    def log_tool_creation(tool: str, fields: dict | None = None):
        line = _fmt("tool_creation", {"tool": tool, **(fields or {})})
        print(line, flush=True)
        return line

    def log_knowledge_ingest(source: str, count: int):
        line = _fmt("knowledge_ingest", {"source": source, "count": count})
        print(line, flush=True)
        return line

    mod.log_agent_run = log_agent_run
    mod.log_tool_creation = log_tool_creation
    mod.log_knowledge_ingest = log_knowledge_ingest
    return mod

# Inject the same logger under all paths tests might import
_logger = _make_logger_module("audit_logger")
sys.modules.setdefault("audit_logger", _logger)
sys.modules.setdefault("factory_agents.archivist.audit_logger", _logger)
sys.modules.setdefault("core.telemetry.audit_logger", _logger)
