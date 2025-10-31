from __future__ import annotations

import json
import pathlib

from factory_agents.orion_control.federation_interface import FederationInterface


def test_chatroom_interface_roundtrip(tmp_path: pathlib.Path) -> None:
    # Use repo root inferred from test file location
    repo = pathlib.Path(__file__).resolve().parents[3]
    iface = FederationInterface(repo)
    # Relay a message
    iface.relay_message("UnitTest", "hello world")
    log = repo / "logs" / "chat" / "watchtower_room.jsonl"
    assert log.exists(), "chat log should be created"
    # Verify last line parses as JSON
    lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "chat log should have at least one entry"
    obj = json.loads(lines[-1])
    assert obj.get("agent") == "UnitTest"
    assert obj.get("content") == "hello world"
