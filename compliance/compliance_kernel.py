from __future__ import annotations

"""Compliance Kernel Stub

Exposes minimal interfaces for audit logging and policy checks.
This is a generated template and should be extended per governance.
"""

from pathlib import Path
from typing import Dict, Any

from utils.paths import LOGS_DIR
from tools.logging_utils import JsonlLogger

_logger = JsonlLogger(log_file=LOGS_DIR / 'audit.jsonl')

def record_audit(event: str, data: Dict[str, Any] | None = None) -> None:
    _logger.log(True, {"component": "compliance_kernel", "event": event, "data": data or {}})

def check_policy(name: str, context: Dict[str, Any] | None = None) -> bool:
    # Always allow by default in template
    record_audit('policy_check', {"name": name, "allowed": True})
    return True
