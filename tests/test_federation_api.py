from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from agent_factory.console.app import app

client = TestClient(app)
CSV_PATH = Path("compliance/audit_log/federation_updates.csv")


def test_list_updates_initial():
    # Should not error and should return JSON with count and items
    r = client.get("/api/federation/updates")
    assert r.status_code == 200
    data = r.json()
    assert "count" in data and "items" in data


def test_approve_and_publish_update(tmp_path):
    # Approve an update
    topic = "Test Federation Topic"
    r = client.post("/api/federation/approve", json={"topic": topic, "notes": "seed"})
    assert r.status_code == 200
    payload = r.json()
    assert payload.get("ok") is True
    approved = payload.get("data", {})
    assert approved.get("status") == "approved"
    assert approved.get("topic") == topic

    # The CSV should exist and contain header
    assert CSV_PATH.exists()
    csv_text = CSV_PATH.read_text(encoding="utf-8")
    assert "status" in csv_text and "approved" in csv_text

    # GET filter by approved should include at least one entry
    r2 = client.get("/api/federation/updates", params={"status": "approved"})
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["count"] >= 1

    # Publish the same topic
    r3 = client.post("/api/federation/publish", json={"topic": topic, "notes": "go"})
    assert r3.status_code == 200
    published = r3.json().get("data", {})
    assert published.get("status") == "published"

    # GET filter by published should include at least one entry
    r4 = client.get("/api/federation/updates", params={"status": "published"})
    assert r4.status_code == 200
    data4 = r4.json()
    assert data4["count"] >= 1
