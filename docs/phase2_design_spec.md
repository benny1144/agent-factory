### Phase 2 Design Spec — Cognitive Engine Federation & Curator 2.0

Date: 2025-10-24

Overview
- Introduces a federated Memory Engine abstraction with pluggable backends (FAISS, Qdrant, Redis).
- Expands Knowledge Curator to multi-format ingestion with provenance tracking.
- Extends Procedural Memory with memory_events table to capture memory operations.
- Enhances Human Firewall with risk-tier decorator require_risk().

1) Memory Engine Federation
- Module: src/agent_factory/services/memory/engine.py
- Class: MemoryEngine
  - Reads backend from env MEMORY_BACKEND (faiss|qdrant|redis), default faiss.
  - Methods:
    - add_documents(docs, metadata: dict|None) -> {"ids": [...], "count": int}
    - search(query: str, top_k: int=5) -> list[dict]
    - delete(filter: dict) -> {"deleted": int} (tagged @require_risk("HIGH"))
  - Emits audit events via [AUDIT] memory_insert, memory_search, memory_delete.
  - Persists events to DB via utils.procedural_memory_pg.insert_memory_event().

- Adapters (stubs; no external connections yet):
  - src/agent_factory/services/memory/faiss_adapter.py
  - src/agent_factory/services/memory/qdrant_adapter.py
  - src/agent_factory/services/memory/redis_adapter.py
  - Each exposes: connect(), add_documents(), query(), delete() with deterministic mock returns.

2) Knowledge Curator 2.0
- Module: agents/knowledge_curator/curate.py (updated)
- Features:
  - Auto-detects and ingests .txt, .md, .pdf, .csv
  - Uses light loaders with graceful fallbacks (PyPDFLoader → PyPDF2 → placeholder)
  - Simple chunking: lines grouped (text), rows batched (csv), per-page chunks (pdf)
  - Writes provenance file per source at knowledge_base/provenance/{file_id}.json
    Example:
    {
      "source": "...",
      "chunks": 42,
      "curator": "auto",
      "timestamp": "..."
    }
  - Logs knowledge_ingest via audit_logger and inserts DB record (knowledge_ingest)
  - Inserts chunks into MemoryEngine.add_documents() which emits memory_insert audit + DB memory_events

3) Procedural Memory v2 Schema
- File: utils/procedural_memory_pg.py
- New table: memory_events
  - id INTEGER PK AUTOINCREMENT
  - backend TEXT NOT NULL
  - event_type TEXT NOT NULL
  - ts TIMESTAMP WITH TIME ZONE NOT NULL
  - details_json JSON
- API: insert_memory_event(backend, event_type, details_json)
- Migration script (SQLite-safe): scripts/db/migrate_phase2.sql

4) Governance Enhancements
- File: utils/firewall_protocol.py
- New decorator: require_risk(level: str = "LOW")
  - HIGH: enforce HITL approval always
  - LOW: defer to configured escalation (HITL/HOTL/HOOTL) via require_hitl
- Applied to MemoryEngine.delete() as @require_risk("HIGH")

5) Environment & Paths
- .env.example additions:
  MEMORY_BACKEND=faiss
  QDRANT_URL=http://localhost:6333
  REDIS_URL=redis://localhost:6379
- utils/paths.py additions:
  - PROVENANCE_DIR = knowledge_base/provenance

6) Tests (Phase 2 initial coverage)
- tests/test_memory_engine.py
  - Validates env-driven adapter selection
  - Checks add_documents() mock path and [AUDIT] memory_insert emission
  - Ensures HIGH risk delete path can be approved via HITL_APPROVE=true

7) Validation Steps
- Run unit tests:
  pytest -q
- Smoke the curator:
  python agents/knowledge_curator/curate.py knowledge_base/source_documents/sample.txt

Expected Results
- [AUDIT] memory_insert and [AUDIT] knowledge_ingest logs in console
- New provenance JSON under knowledge_base/provenance/
- memory_events table populated with insert/search/delete events

Security & Governance Notes
- No network calls are made by adapter stubs.
- HIGH risk operations prompt approval unless HITL_APPROVE=true set explicitly.
- No secrets are logged; ensure .env contains required keys only in local dev.

Rollback
- git checkout main && git reset --hard origin/main
- DROP TABLE IF EXISTS memory_events; (if DB rollback required)
- Remove src/agent_factory/services/memory/ and docs/phase2_design_spec.md if necessary.
