# 🧭 Agent Factory — Knowledge Base Structure

**Version:** 1.0  
**Status:** Active (Phase 3.2 Federation)  
**Purpose:**  
Defines the canonical directory map and metadata schema for the **Agent Factory Knowledge Base Architecture (KBA)**.  
It ensures that all research, compliance, and implementation materials are properly classified, auditable, and retrievable through the Cognitive Engine and Governance Console.

---

## 📂 1. Core Domains

| Folder | Description | Example Documents |
|---------|--------------|------------------|
| `/core/governance/` | Security, audit, and oversight frameworks. | `AI_Agent_Human_Firewall_Protocol.pdf`, `Agent_Factory_Roadmap_v3.2.pdf` |
| `/core/memory/` | Cognitive Engine and Procedural Memory design. | `Agent_Factory_Phase_1.pdf`, `Agent_Tooling_Research.pdf` |
| `/core/communication/` | Protocol Fabric (A2A / MCP / ANP). | `AI_Agent_Communication_Protocols.pdf` |
| `/core/orchestration/` | Multi-agent orchestration frameworks. | `CrewAI_Handbook.pdf`, `AutoGen_Framework_Research.pdf` |
| `/core/architecture/` | Design blueprints and applied case studies. | `Agentic_Blueprints_&_Case_Studies.pdf` |

---

## 🧱 2. Expansion Domains

| Folder | Purpose | Example Inputs |
|---------|----------|----------------|
| `/expansion/governance/` | Ethical and compliance standards (EU AI Act, NIST RMF). | `EU_AI_Act_Compliance.pdf` |
| `/expansion/engineering/` | Implementation, CI/CD validation, provenance. | `Phase2_Validation_Spec.md` |
| `/expansion/cognitive/` | Memory and reinforcement learning research. | `Prometheus_Memory_Experiments.md` |
| `/expansion/federation/` | Federated AI and decentralized protocols. | `Agent_Network_Protocol.pdf` |
| `/expansion/case_studies/` | Applied CrewAI/AutoGen case studies. | `CrewAI_Customer_Support_CaseStudy.pdf` |

---

## 🧬 3. Data & Research Assets

| Folder | Content | Example Files |
|---------|----------|---------------|
| `/datasets/` | Ethical Golden Dataset, provenance, benchmarks. | `ethical_baseline_v1.jsonl` |
| `/registry/` | Central index for all documents. | `metadata_index.json`, `registry_schema.yaml` |
| `/blueprints/` | System diagrams and workflow maps. | `Genesis_Federation_Map.vsdx` |

---

## ⚙️ 4. Validation & Audit Layer

| Component | Description |
|------------|-------------|
| `/validation/` | Scripts for verifying provenance and compliance. |
| `/validation/tests/` | Unit tests for registry accuracy. |
| `/validation/logs/` | [AUDIT] output from automated checks. |

---

## 🧠 5. Registry Schema (for `/registry/metadata_index.json`)

```json
{
  "id": "uuid",
  "title": "string",
  "category": "core|expansion|dataset|validation|blueprint",
  "domain": "governance|memory|communication|orchestration|architecture|ethics|engineering|cognitive|federation|case_study",
  "file_path": "string",
  "version": "1.0.0",
  "provenance": "sha256-hash",
  "tags": ["AI", "agentic", "governance"],
  "summary": "string",
  "last_updated": "YYYY-MM-DD"
}
```
