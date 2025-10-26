from __future__ import annotations

import os
import json
import time
from pathlib import Path

import sys
from pathlib import Path

# Ensure repo-root and src are on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from fastapi.testclient import TestClient

# Import app
from agent_factory.console.app import app


def test_gpt_query_endpoint():
    client = TestClient(app)
    # allow without token by default; set OPERATOR_TOKEN to simulate auth
    if os.getenv("OPERATOR_TOKEN"):
        headers = {"Authorization": f"Bearer {os.getenv('OPERATOR_TOKEN')}"}
    else:
        headers = {}
    r = client.post("/api/gpt/query", json={"query": "hello"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "response" in data and "[GPT-5] received query: hello" in data["response"]


def test_metrics_endpoint_exposes_prometheus():
    client = TestClient(app)
    r = client.get("/metrics")
    # Prometheus exposition format is text/plain
    assert r.status_code == 200
    # Expect our governance counter name to appear
    assert "governance_events_total" in r.text


def test_ws_telemetry_streams_messages():
    # Speed up stream for tests
    os.environ["WS_INTERVAL_SEC"] = "0.01"
    client = TestClient(app)
    headers = {}
    if os.getenv("OPERATOR_TOKEN"):
        headers["Authorization"] = f"Bearer {os.getenv('OPERATOR_TOKEN')}"
    with client.websocket_connect("/api/ws/telemetry", headers=headers) as ws:
        # Receive immediate welcome event
        msg = ws.receive_text()
        data = json.loads(msg)
        assert data.get("type") == "audit"
        # Receive another heartbeat quickly
        msg2 = ws.receive_text()
        data2 = json.loads(msg2)
        assert data2.get("type") == "audit"
