# 🜂 Business Archivist Deployment Guide

### Version: 1.0  
### Author: Agent Factory Governance Council  
### Last Updated: 2025-10-27

---

## 1. Overview

The **Business Archivist** is an enterprise-ready cognitive agent based on the Agent Factory’s Archivist framework.  
It provides secure, compliant knowledge management, research, and reasoning over private organizational data.

This guide explains how to **deploy**, **configure**, and **govern** your own Business Archivist instance using the `/deploy/business` API and AutoGen orchestration.

---

## 2. Core Architecture

Each deployed Archivist instance operates as a **tenant-isolated intelligence node**, connected to its company’s private knowledge base.

### Directory Structure
```
tenants/
 └── <tenant_id>/
      ├── knowledge_base/
      ├── audit_kernel/
      ├── business_config.json
      └── logs/
```

### Key Components
| Component | Function |
|------------|-----------|
| **FastAPI Server** | Handles chat, deployment, and research endpoints. |
| **AutoGen Orchestrator** | Manages agent coordination (Archivist ↔ Genesis ↔ Junie). |
| **Governance Kernel** | Enforces Firewall, audit logging, and risk control. |
| **Vector Memory** | Stores embedded documents for semantic recall. |
| **External Connectors** | Provides secure read-only research (Arxiv, Serper, Semantic Scholar). |

---

## 3. Deployment Instructions

### Step 1 — Launch Archivist Server
Run from PowerShell or terminal:
```bash
python factory_agents/archivist/fastapi_server.py
```
Confirm server is running on port `5065`.

### Step 2 — Deploy Business Instance
POST to the business deployment endpoint:
```bash
Invoke-RestMethod -Uri "http://localhost:5065/deploy/business" -Method POST -Body '{"tenant_id":"acme_corp","company_name":"Acme Corporation"}' -ContentType "application/json"
```
Response example:
```json
{
  "reply": "✅ Business Archivist deployed for Acme Corporation under tenant ID acme_corp.",
  "config": "tenants/acme_corp/business_config.json"
}
```

This automatically:
- Creates tenant directories
- Generates a customized configuration from the template
- Mounts `knowledge_base/` and `audit_kernel/`

---

## 4. Configuration

### Configuration File — `business_config.json`
```json
{
  "company_name": "Acme Corporation",
  "knowledge_base_path": "/tenants/acme_corp/knowledge_base",
  "compliance_mode": "strict",
  "data_privacy_level": "enterprise",
  "governance_hooks": ["firewall_precheck", "audit_log", "rollback_ready"]
}
```

### Customization
You may edit `knowledge_base_path` to link to internal data sources such as:
- SharePoint or Google Drive mounts
- Local document repositories
- GitHub or GitLab wikis
- Notion or Confluence exports

Each external mount must be registered in the **Firewall config** for read-only access.

---

## 5. AutoGen Orchestration

Archivist leverages **AutoGen** to coordinate tasks between herself, **Genesis** (the Architect), and **Junie** (the Executor).

### Communication Loop Example
```
Archivist → Genesis → Junie → Firewall → Archivist
```
1. Archivist detects a new opportunity or missing knowledge.
2. Sends a structured `[GENESIS REQUEST]` proposal.
3. Genesis generates a `[JUNIE TASK]` implementation plan.
4. Junie executes under human or Firewall supervision.
5. Results are fed back to Archivist and logged to the Compliance Kernel.

This system ensures **zero autonomous execution** beyond approved scopes.

---

## 6. Compliance & Governance

All Business Archivist instances must integrate with the **Human Firewall** and **Compliance Audit Kernel**.

### Logs Generated
| Log File | Purpose |
|-----------|----------|
| `/audit_kernel/ledger.jsonl` | Immutable record of all actions and changes. |
| `/logs/external_queries.log` | Records all Arxiv/Serper/Semantic queries. |
| `/logs/federated_audit.log` | Tracks anonymized insight sharing with Genesis. |

### Governance Rules
- All write actions must pass **firewall_precheck**.
- Every new versioned file includes a SHA-256 hash.
- Any high-risk event triggers human approval.
- Rollback commands are auto-generated and reversible.

---

## 7. Memory and Knowledge Integration

Each Business Archivist includes a **vector store** for semantic recall:
```
/tenants/<tenant_id>/knowledge_base/vector_store/
```

Data can be ingested via the `/ingest` or `/index` endpoints (coming soon), or manually added to the folder.

Periodic **Reflective Sync** ensures that curated documents and conversation summaries are automatically indexed.

---

## 8. External Intelligence Connectors

Business Archivist supports external data lookups through read-only connectors:
- **Arxiv** → Academic research papers
- **Serper** → General web knowledge and market data
- **Semantic Scholar** → Scholarly abstracts and citations

Governance enforcement ensures that external lookups:
- Never store raw data without hashing.
- Are always logged with timestamps and source attribution.

---

## 9. Scaling & Multi-Tenant Management

You can deploy multiple Archivist instances simultaneously:
```
POST /deploy/business
{"tenant_id": "clientA", "company_name": "Client A Ltd"}
POST /deploy/business
{"tenant_id": "clientB", "company_name": "Client B Inc"}
```

Each instance has:
- Isolated data directories
- Independent audit and compliance logs
- Separate API keys (managed via Vault)

---

## 10. Commercial Integration Strategy

Businesses can embed their Archivist instance into existing tools:
| System | Integration Method |
|---------|-------------------|
| **Microsoft Teams / Slack** | Connect via FastAPI webhook endpoint |
| **SharePoint / GDrive** | Mount through secure service connectors |
| **Internal APIs** | Use REST calls from internal dashboards |
| **CRM / ERP Systems** | Archive summaries and auto-generate documentation |

Planned future versions include **GUI deployment dashboards**, **per-tenant analytics**, and **compliance reports**.

---

## 11. Security and Privacy Overview

- Each tenant operates in **total isolation**.
- API keys stored via **GCP Secret Manager or Vault**.
- All embeddings, logs, and audit data are **non-reversible and hashed**.
- Role-based access controls (RBAC) define which users can view, query, or approve changes.

---

## 12. Future Expansion Roadmap

| Feature | Description | Status |
|----------|--------------|---------|
| AutoGen 2.0 Integration | True autonomous knowledge-worker simulation | Planned |
| Federated Insight Sharing | Anonymous global insight exchange | Implemented |
| Reflective Visualization Engine | Diagrammatic knowledge graphs | Future |
| Cloud Sync | GCP or AWS integration for enterprise deployments | Planned |

---

## 13. Support

For setup or integration support, contact:
```
support@agentfactory.ai
```
or open an issue in the Agent Factory GitHub repository.

---

**End of Document**  
*Business Archivist — The Reflective Intelligence for the Enterprise*