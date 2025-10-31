# Artisan Executor (Canonical) — Phase 38.8

This module consolidates all Artisan executor logic into the Federation layout.

Directory
- main.py — Entrypoint for the executor service (supports `--test`)
- core/
  - executor_core.py — Task dispatcher with HITL approval and governance logging
  - policy.py — Allowlist policy (v1.1)
  - __init__.py
- tests/
  - test_policy.py — Unit tests for allowlist
- persona_artisan.yaml — Agent persona metadata
- requirements.txt — Local dependencies
- README.md — This file

Runtime & Logs
- Canonical runtime log: `logs/artisan/runtime.log`
- Legacy JSONL (preserved for dashboards): `logs/artisan_activity.jsonl`
- Governance Event Bus: `governance/event_bus.jsonl`

How to run
- Self-test: `python -S factory_agents\artisan_executor\main.py --test`
  - Creates/updates `logs/artisan/runtime.log`
- Service: `python -S factory_agents\artisan_executor\main.py --poll 10`

Notes
- The legacy `artisan_engine/` remains for backward compatibility; new builds should import from `factory_agents.artisan_executor.*`.
- All model interactions are routed via `agents.ModelRouter` for compliance logging; no secrets are logged.
