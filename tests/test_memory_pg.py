from __future__ import annotations

import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from utils.procedural_memory_pg import (
    init_db,
    trace_run,
    register_tool,
    insert_ingest,
    select_all,
    agent_runs,
    tool_registry,
    knowledge_ingest,
)


def test_db_roundtrip(tmp_path, monkeypatch):
    # Use sqlite temp file
    db_file = tmp_path / "test.sqlite"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file.as_posix()}")

    engine = init_db()

    # trace_run context
    with trace_run("TestAgent", task="unit") as trace:
        trace["status"] = "ok"

    # tool registration
    tool_id = register_tool("unit_tool", path=PROJECT_ROOT / "tools" / "unit_tool.py", schema={"name": "unit_tool"})
    assert tool_id > 0

    # knowledge ingest
    ing_id = insert_ingest(source_path=PROJECT_ROOT / "README.md", vector_count=42, curator="tester")
    assert ing_id > 0

    # selects
    runs = select_all(agent_runs)
    assert len(runs) == 1
    assert runs[0]["status"] == "ok"

    tools = select_all(tool_registry)
    assert tools and tools[0]["tool_name"] == "unit_tool"

    ing = select_all(knowledge_ingest)
    assert ing and ing[0]["vector_count"] == 42
