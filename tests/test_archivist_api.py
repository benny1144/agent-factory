from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "src"))

from fastapi.testclient import TestClient  # type: ignore

# Import the Archivist app
from factory_agents.archivist_archy.curator_api import app, CURATED_DIR, AUDIT_WRITES  # type: ignore


def test_chat_internal():
    client = TestClient(app)
    r = client.post("/chat", json={"message": "Explain the knowledge base structure"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("intent") == "internal"
    # should include citations field in internal mode
    assert "citations" in data or "excerpt" in data


def test_chat_research_intent(monkeypatch):
    # Set integration key to enable research path (even if tool is stub)
    monkeypatch.setenv("INTEGRATION_SERPER_KEY", "test-key")
    client = TestClient(app)
    r = client.post("/chat", json={"message": "research: latest updates on Agent Factory"})
    assert r.status_code == 200
    data = r.json()
    assert data.get("intent") == "research"
    assert data.get("external") is True


def test_add_file_and_audit(tmp_path, monkeypatch):
    # Ensure curated dir exists
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    client = TestClient(app)
    # Write file
    r = client.post(
        "/add_file",
        json={
            "category": "curated",
            "filename": "unit_test_entry.md",
            "content": "# Unit Test\nThis is a test entry.\n",
            "actor": "pytest",
        },
    )
    assert r.status_code == 200
    data = r.json()
    p = Path(data["path"])  # written file
    assert p.exists()
    # Audit CSV should contain a line for this write
    assert AUDIT_WRITES.exists()
    contents = AUDIT_WRITES.read_text(encoding="utf-8")
    assert ",add," in contents or "add," in contents
    # Clean up file to avoid residue on developer machine (optional)
    # p.unlink(missing_ok=True)  # leave file for provenance


def test_versioned_update_review_gate(monkeypatch):
    client = TestClient(app)
    base = CURATED_DIR / "roadmap_entry.md"
    base.parent.mkdir(parents=True, exist_ok=True)
    base.write_text("Initial content\n", encoding="utf-8")

    # Without approval, should be pending (no version file written)
    r = client.post(
        "/update_doc",
        json={
            "target": str(base.relative_to(PROJECT_ROOT)),
            "content": "Revised content\n",
            "approve": False,
            "actor": "pytest",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "pending_review"

    # With approval, a _v01.md should appear
    # Approve replace + allow firewall to proceed non-interactively
    os.environ["HITL_APPROVE"] = "true"
    r2 = client.post(
        "/update_doc",
        json={
            "target": str(base.relative_to(PROJECT_ROOT)),
            "content": "Revised content\n",
            "approve": True,
            "actor": "pytest",
        },
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("ok") is True
    new_path = PROJECT_ROOT / d2.get("path")
    assert new_path.exists(), f"Expected versioned file at {new_path}"
