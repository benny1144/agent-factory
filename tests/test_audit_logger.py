from __future__ import annotations

import io
import json
import sys
from pathlib import Path

# Ensure src is on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from agent_factory.services.audit.audit_logger import log_event, log_agent_run, log_tool_creation, log_knowledge_ingest


def test_log_event_outputs_structured_json(monkeypatch, capsys):
    evt = log_event("unit_test", {"foo": "bar", "num": 1})
    assert evt["ok"] is True
    assert evt["data"]["event_type"] == "unit_test"
    assert "trace_id" in evt["meta"]

    out = capsys.readouterr().out
    assert out.startswith("[AUDIT] ")
    # Validate JSON part
    json_str = out[len("[AUDIT] "):].strip()
    payload = json.loads(json_str)
    assert payload["data"]["event_type"] == "unit_test"


def test_helper_shortcuts(capsys):
    log_agent_run("TestAgent", task_id="t1", status="started")
    log_tool_creation("my_tool", {"path": "tools/my_tool.py"})
    log_knowledge_ingest("file.txt", 3)
    out = capsys.readouterr().out
    assert out.count("[AUDIT]") >= 3
