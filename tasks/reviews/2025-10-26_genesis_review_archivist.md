# Genesis Review Request — Deploy Archivist Agent (Read/Write Curator)

Submitted: 2025-10-26 16:10 (local)
Submitted by: Junie (JetBrains AI Implementor)
Status: SUBMITTED

Task Title
- Deploy Archivist Agent — Read/Write Curator Implementation

Purpose
- Request Genesis (Architect) review and approval of the newly implemented Archivist agent and its governance-constrained read/write capabilities.

Scope of Review
- Agents/archivist package:
  - agents/archivist/persona_archivist.md
  - agents/archivist/retrieval_chain.py
  - agents/archivist/curator_api.py (FastAPI endpoints: /chat, /add_file, /update_doc)
  - agents/archivist/main.py (uvicorn entry)
  - agents/archivist/requirements.txt
- Governance integrations:
  - compliance/audit_log/archivist_writes.csv (append-only)
  - governance/agents_registry.yaml (Archivist registered: Curator/L3)
  - .env.example flags (ALLOW_WRITE_CURATED, ALLOW_VERSIONED_REPLACE, REVIEW_REQUIRED_FOR_REPLACE)
- Whitelist write targets:
  - knowledge_base/curated/
  - knowledge_base/conversations/

Acceptance Criteria (for Review)
- All writes restricted to whitelisted folders (enforced by path resolution).
- Versioned updates require review/approval; high-risk path gated via @require_risk("HIGH").
- Every write is audited to CSV with SHA-256 of the new content and emits [AUDIT] archivist_write.
- External search only on explicit "research" intent and only with SERPER key; responses labeled external.
- Reflective Sync triggers reindex manifest after approved writes.
- Unit tests for Archivist API pass locally and in CI.

Risk & Mitigations
- Risk: Unauthorized write outside whitelist → Mitigation: path canonicalization + block + [AUDIT] archivist_write_blocked.
- Risk: Silent overwrite → Mitigation: versioned replacement (_vNN.md) with review gate; audit trail with SHA-256.
- Risk: Data exfiltration via search → Mitigation: external search only on "research" intent + key gate + labeling.

HITL/HOTL Plan
- High-risk updates (replace) → enforce HITL via @require_risk("HIGH").
- Default persona escalation via Firewall Protocol for routine operations.

Artifacts
- Audit CSV: compliance/audit_log/archivist_writes.csv
- Memory manifest: knowledge_base/vector_store/faiss_index/manifest.json
- Tests: tests/test_archivist_api.py

Requested Actions (Genesis)
- Validate persona, retrieval chain, and curator API behavior.
- Confirm governance hooks align with Human Firewall and project guidelines.
- Approve deployment to shared environments.

Links
- Governance Ledger: docs/governance_ledger.md
- Governance Policy: GOVERNANCE.md

Machine-Readable Review Envelope
```json
{
  "ts": "2025-10-26T16:10:00",
  "type": "genesis_review_request",
  "task": "Deploy Archivist Agent — Read/Write Curator Implementation",
  "submitter": "Junie",
  "status": "SUBMITTED",
  "artifacts": {
    "review_doc": "tasks/reviews/2025-10-26_genesis_review_archivist.md",
    "audit_csv": "compliance/audit_log/archivist_writes.csv",
    "tests": ["tests/test_archivist_api.py"]
  },
  "governance_flags": {
    "ALLOW_WRITE_CURATED": true,
    "ALLOW_VERSIONED_REPLACE": true,
    "REVIEW_REQUIRED_FOR_REPLACE": true
  }
}
```

Approval Checklist
- [ ] Persona roles and boundaries validated
- [ ] Retrieval chain deterministic behavior confirmed
- [ ] Write whitelist enforcement verified
- [ ] Versioned update path (HITL) verified
- [ ] Audit CSV entries and hashes verified
- [ ] Reflective reindex manifest updated
- [ ] Tests green in CI
