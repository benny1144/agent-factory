Agent Factory
A private, secure, and scalable ecosystem for designing, deploying, and managing autonomous AI agents. This project follows the "Agent Factory Roadmap" to build a sovereign, self-optimizing agentic workforce.
Project Status
Phase 1: Foundational Layer — COMPLETE
 - [X] Environment & Governance Setup
 - [X] Compliance & Audit Kernel (JSON logs with OTEL/GCP integration)
 - [X] Procedural Memory (DB tables + context manager; SQLite fallback)
 - [X] Human Firewall Protocol (HITL/HOTL/HOOTL)
 - [X] Build Agent 1: Toolmaker's Co-Pilot (auto-save + registry)
 - [X] Build Agent 2: Knowledge Curator (ingest logging)
 - [X] Architect Genesis integration (audit + trace + HITL prompt)

Phase 2: Cognitive Engine Federation — IN PROGRESS

Core Principle: Security by Design
This project formally adopts the AI Agent Human Firewall Protocol as the mandatory framework for all agent and tool development. All components must adhere to these security, reliability, and governance standards.
See GOVERNANCE.md for details.

Validation
- Run tests: `pytest -q`
- Manual runs:
  - Architect Genesis: `python agents/architect_genesis/main.py`
  - Toolmaker Copilot: `python agents/toolmaker_copilot/main.py`
  - Knowledge Curator: `python agents/knowledge_curator/curate.py`

Repository Structure
This repository is organized to treat all agent components as version-controlled, production-grade assets.
 * /agents: Contains the core logic and configurations for all agent "crews" (e.g., using CrewAI).
 * /knowledge_base: Stores curated knowledge, processed documents, and vector store configurations that form the "brain" for our agents.
 * /personas: A version-controlled library of high-fidelity agent persona definitions. These are the "operating systems" for our agents.
 * /tools: The library of certified, production-grade tools that agents can use. Every tool in this directory must pass the "Specification for Architect-Grade Agent Tools."
License
This is a private, proprietary project. All rights are reserved. Do not add or assume any open-source license.


---

Auto-start (Option A — Windows Task Scheduler)

You can auto-start the Junie Bridge and Cloudflared tunnel at Windows sign-in using the scripts included in this repo.

Prerequisites
- Windows 10/11
- PowerShell (Run as Administrator for setup/removal)
- Node.js on PATH

One-time setup (creates or updates tasks)
1) Open PowerShell as Administrator
2) Navigate to the repo root: cd C:\Users\benny\IdeaProjects\agent-factory
3) Run: ./scripts/setup-autostart.ps1
   - Optional: ./scripts/setup-autostart.ps1 --run-now to start immediately

What this does
- Registers two Scheduled Tasks at logon with highest privileges:
  - "Junie Bridge" → runs start-bridge-task.ps1
  - "Junie Tunnel" → runs start-tunnel.ps1
- Highest privileges are required because the bridge binds to HTTPS on port 443.

Manage tasks
- Start now (manual trigger): ./scripts/run-autostart-now.ps1
- Remove tasks: ./scripts/remove-autostart.ps1

Notes
- Health check: http://localhost:8765/health (HTTP is always started). If USE_HTTPS=true, HTTPS listens on HTTPS_PORT (defaults to PORT or 443).
- If port 443 is in use, the bridge will log EADDRINUSE and continue without HTTPS unless you set HTTPS_FALLBACK_PORT (e.g., 8443). Example in junie-bridge/.env:
  - USE_HTTPS=true
  - PORT=443
  - HTTPS_PORT=443
  - HTTPS_FALLBACK_PORT=8443
- Tunnel target (default): https://localhost:443 with --no-tls-verify (see start-tunnel.ps1). If using fallback, target https://localhost:8443 instead.
- If you prefer a non-privileged port (no admin): set USE_HTTPS=false and PORT=8765 in junie-bridge/.env, then point the tunnel to http://localhost:8765.


## Local environment setup (fixes IDE missing-package warnings)

If your IDE shows warnings like "Package pytest/sqlalchemy/fastapi/prometheus-client is not installed," create a project virtual environment and install the repo requirements:

- One-click (cross-platform):
  - python scripts/setup_venv.py
  - Then in IntelliJ/PyCharm: File → Settings → Project → Python Interpreter → Add → Existing environment → select .venv/python

- Manual:
  - python -m venv .venv
  - .venv\\Scripts\\activate   # Windows PowerShell
    or
  - source .venv/bin/activate     # macOS/Linux
  - pip install -r requirements.txt

Reopen requirements.txt — the warnings should disappear.
