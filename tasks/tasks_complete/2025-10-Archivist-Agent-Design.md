# JUNIE TASK — Deploy Archivist Agent — Read/Write Curator Implementation

Date: 2025-10-26

Preconditions
- Repo: benny1144/agent-factory
- Branch: feature/archivist-agent
- Dependencies: Active Cognitive Engine (Qdrant/FAISS); Governance Kernel + Firewall enabled; Serper key in Vault (INTEGRATION_SERPER_KEY, read-only); Reflective Sync automation active.

Plan (Genesis → Junie)
- Design Phase — Genesis Crew
  - Architect sub-agent interprets spec
  - Toolsmith drafts structure and service scripts
  - Persona Engineer creates persona_archivist.md
  - Coder generates API / retrieval / logging code
  - Auditor injects compliance & rollback clauses
- Implementation Phase — Junie
  - Create /agents/archivist/: main.py, retrieval_chain.py, curator_api.py, persona_archivist.md, requirements.txt
  - Add whitelisted write folders: /knowledge_base/curated/, /knowledge_base/conversations/
  - Register Archivist in /governance/agents_registry.yaml

Core Features (implemented)
- Chat API (FastAPI)
  - POST /chat → routes messages through RAG + Serper (on “research” intent) + deterministic summaries.
  - Memory Logger: append-only JSONL at /logs/archivist_memory.jsonl
- Curator API
  - POST /add_file → schema-checked writes to whitelisted dirs; audit CSV + SHA-256
  - POST /update_doc → versioned replacement (_vNN.md); @require_risk("HIGH"); review gate
- Governance Hooks
  - Log every write to /compliance/audit_log/archivist_writes.csv
  - [AUDIT] events for chat and writes
  - After approved writes, trigger charter_tools.rebuild_vector_index() (Reflective Sync)

Permissions (env)
- ALLOW_WRITE_CURATED=true
- ALLOW_VERSIONED_REPLACE=true
- REVIEW_REQUIRED_FOR_REPLACE=true
- WRITE_WHITELIST: /knowledge_base/curated/, /knowledge_base/conversations/
- READ_SCOPE: project_root/*

Tests
- Chat Retrieval Test – Internal query retrieves deterministic citations/excerpt
- Serper Integration Test – “research” keyword → external=true (gated by INTEGRATION_SERPER_KEY)
- File Write Test – add_file creates markdown and audit row
- Versioned Update Test – update_doc creates _v01.md after approval and pending when not approved
- Governance Review Test – enforced by REVIEW_REQUIRED_FOR_REPLACE

Verification
- Archivist responds over /chat
- Writes only occur in whitelisted folders
- Audit CSV lines with hashes present
- Vector index manifest updated after approved writes
- Firewall gating blocks unauthorized replacements

Rollback
- git checkout phase2-stable
- Delete /agents/archivist/
- Remove Archivist entry from governance/agents_registry.yaml
- Restore prior vector index snapshot
- Audit log records rollback completion

Activation
Issue in Genesis console:
“Genesis, execute Deploy Archivist Agent — Read/Write Curator Implementation.”

Then approve under Firewall; Junie merges feature/archivist-agent. Run service locally:

```
python -m uvicorn agents.archivist.curator_api:app --reload --port 5000
# or
python agents/archivist/main.py --port 5000
```

Chat endpoint: http://localhost:5000/chat
