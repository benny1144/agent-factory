┌──────────────────────────────────────────────────────────────────────────────┐
│                         HUMAN FIREWALL & GOVERNANCE CONSOLE (UI)             │
│  • Approvals  • Risk Alerts  • Audit Dashboards  • Feedback Interface        │
│  • Slack / Teams Bots  • Web Governance Portal                               │
└───────────────▲──────────────────────────────────────────────────────────────┘
│  Human Oversight  (HITL / HOTL Escalation)
│
┌───────────────┴──────────────────────────────────────────────────────────────┐
│                      GENESIS ORCHESTRATOR  (AutoGen / MAF)                   │
│  • Master Planner / Task Decomposer                                          │
│  • Risk-Adaptive Oversight Engine                                            │
│  • Uses CrewAI for Creative Tasks                                            │
│  • Logs all actions → Compliance Kernel                                      │
│  • Reads / Writes to Procedural Memory                                       │
│  • Supervised Execution Bootstrap (Phase 2.2)                                │
└───────────────┬──────────────────────────────────────────────────────────────┘
│  Commands, Plans, Telemetry, Memory Calls
▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                       CORE ARCHITECTURE STACK  (Layer 0)                     │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │ 1️⃣ Compliance & Audit Kernel                                           │  │
│  │    • Immutable Logs  • OpenTelemetry  • Vault / Entra ID Auth          │  │
│  ├────────────────────────────────────────────────────────────────────────┤  │
│  │ 2️⃣ Cognitive Engine (Shared Memory)                                    │  │
│  │    • Short-Term (Redis)  • Long-Term (Vector RAG)                      │  │
│  │    • Procedural Memory / Skill Logs (seed from supervised runs)         │  │
│  ├────────────────────────────────────────────────────────────────────────┤  │
│  │ 3️⃣ Protocol Fabric (Communication Bus)                                 │  │
│  │    • A2A (Agent Discovery) • MCP (Tool Interop) • ANP (Federation)    │  │
│  ├────────────────────────────────────────────────────────────────────────┤  │
│  │ 4️⃣ Evaluation & Benchmarking Engine                                    │  │
│  │    • CI/CT Tests • Performance KPIs • Compliance Checks                │  │
│  ├────────────────────────────────────────────────────────────────────────┤  │
│  │ 5️⃣ Reinforcement & Learning Service                                   │  │
│  │    • Reward Signals from Eval Engine + Helios Feedback                 │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└───────────────┬──────────────────────────────────────────────────────────────┘
│  Metrics / Knowledge / Policy Baselines
▼
┌──────────────────────────────────────────────────────────────────────────────┐
│          OPTIMIZATION & ETHICS LAYER  (Phase 3 Agents + Monitors)            │
│  • Prometheus – R&D Agent (CrewAI)                                           │
│  • Helios – Resource Optimizer (CFO)                                         │
│  • Ethical Drift Monitor + Golden Dataset Baseline                           │
│  • Simulation Sandbox for Safe Testing                                       │
│  • Outputs → Governance Console & Reinforcement Service                      │
└───────────────┬──────────────────────────────────────────────────────────────┘
│  Federation / External Collaboration via Protocol Fabric
▼
┌──────────────────────────────────────────────────────────────────────────────┐
│        EXTERNAL AGENTS & PARTNER SYSTEMS (A2A / MCP / ANP Gateways)          │
│  • Third-Party Agents / APIs / Knowledge Sources                             │
│  • Verified Identities (DIDs)  • Federated Learning Exchange                 │
└──────────────────────────────────────────────────────────────────────────────┘
