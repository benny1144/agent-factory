# Project Governance and Security Mandate

## 1. Official Adoption of the Human Firewall Protocol

This document formally codifies the adoption of the principles, procedures, and standards outlined in the **"AE - AI Agent Human Firewall Protocol"** as the mandatory and non-negotiable governance framework for this entire project.

## 2. Scope of Compliance

Compliance with this protocol is required for every asset and component within this repository, including but not limited to:

* **All Agent Personas:** Personas must be designed with explicit operational boundaries and safety constraints.
* **All Tools:** Every tool must be developed in strict adherence to the "Specification for Architect-Grade Agent Tools," which is the direct implementation of the Firewall Protocol.
* **All Agentic Workflows:** The design and deployment of agent crews must include provisions for human oversight, logging, and intervention as defined by the protocol.

## 3. The Principle of "Secure by Design"

This project operates on a **"secure by design"** principle. Security, reliability, and predictability are not afterthoughts; they are the primary requirements for any code to be accepted into this project. Any contribution, whether a new tool or an agent modification, will be evaluated against the standards of the Human Firewall Protocol before it is approved.

## Reflective Sync Automation

Every executed [JUNIE TASK] must automatically update governance records, procedural memory, and RAG embeddings via `tools/reflective_sync.py`.
No code change is final until a sync confirmation hash is logged in `compliance/audit_log/reflective_sync.csv`.

This document serves as the single source of truth for the project's commitment to building a secure, reliable, and trustworthy agentic workforce.