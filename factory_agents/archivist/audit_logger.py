# /factory_agents/archivist/audit_logger.py
# Delegate to the root implementation so both imports behave identically.
from audit_logger import (
    log_agent_run,
    log_tool_creation,
    log_knowledge_ingest,
)
__all__ = ["log_agent_run", "log_tool_creation", "log_knowledge_ingest"]
