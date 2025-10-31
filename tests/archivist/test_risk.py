from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from factory_agents.archivist.reasoning_core import risk_assess  # type: ignore
from factory_agents.archivist.fastapi_server import app  # type: ignore
from fastapi.testclient import TestClient  # type: ignore


def test_risk_assess_log_append():
    # Write a unique event and assert it is appended to the log
    event = "unit_test_event_risk_assess"
    details = "testing risk logging pipeline"
    rec = risk_assess(event, details)
    assert rec["event"] == event
    log_path = ROOT / "logs" / "risk_assessments.json"
    assert log_path.exists()
    # Read last few lines looking for our event
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert any(json.loads(l).get("event") == event for l in lines[-10:])


def test_governance_review_endpoint():
    client = TestClient(app)
    payload = {"event": "unit_test_review", "level": "High", "details": "manually triggered"}
    r = client.post("/governance/review", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True
    # Verify governance log was written
    log_path = ROOT / "governance" / "firewall_audit.log"
    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "unit_test_review" in text
