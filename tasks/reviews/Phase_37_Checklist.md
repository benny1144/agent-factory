# Phase 37 – Artisan Replacement & Genesis Optimization (Checklist)

Date: 2025-10-30

This checklist verifies the requirements for Phase 37 (Artisan v1.1 Safe Executor, Genesis telemetry/optimization, Orion↔Genesis link, Watchtower approval gate, and Archy sentinel).

## What changed (paths)
- Artisan policy allowlist: artisan_engine/policy.py
- Artisan executor (enforces policy + HITL gate): artisan_engine/executor.py
- Watchtower API (approvals + merged logs SSE): frontend/watchtower/src/api.ts
- Genesis CLI ping: factory_agents/architect_genesis/api.py (supports `--ping`)
- Genesis helpers + CLI flags: factory_agents/architect_genesis/main.py (`--register_orion`, `--optimize`)
- Genesis memory directory/files: factory_agents/architect_genesis/memory/{short_term.jsonl,procedural.jsonl,long_term.jsonl}
- Orion heartbeat → Genesis ping: core/orion_bootstrap.py
- Federation manifest status: federation/context_manifest_v2.json {"status":"active"}
- Archy sentinel (drift monitor): factory_agents/archy.py
- Policy unit tests: artisan_engine/tests/test_policy.py

## How to verify
1) Policy test
- Command: `pytest -q artisan_engine/tests/test_policy.py`
- Expect: tests pass; disallowed commands evaluate False.

2) Genesis ping
- Command: `python -S factory_agents/architect_genesis/api.py --ping`
- Expect: prints `pong` and appends an event to logs/genesis_activity.jsonl

3) Genesis registration
- Command: `python -S factory_agents/architect_genesis/main.py --register_orion`
- Expect: logs/register_orion event in logs/genesis_activity.jsonl; memory/*.jsonl files exist.

4) Genesis optimize
- Command: `python -S factory_agents/architect_genesis/main.py --optimize`
- Expect: governance/audits/genesis_phase37_optimize.json created; event appended to logs/genesis_activity.jsonl

5) Orion heartbeat → Genesis ping
- Command: `python -S core/orion_bootstrap.py --dry-run` (single iteration) or temporary run for ~15s without `--dry-run`.
- Expect: logs/orion_activity.jsonl includes `genesis_ping` events.

6) Watchtower approval gate
- Start Watchtower dev: `cd frontend/watchtower && npm install && npm run dev`.
- Create a task requiring approval: write a JSON file under `tasks/from_orion/` with `{ "command": "powershell Remove-Item *" }` (do NOT run; this should be blocked).
- Run Artisan executor: `python -S artisan_engine/executor.py`.
- Expect: logs/artisan_activity.jsonl shows `task_blocked` and a `.awaiting` file under `tasks/pending_human/`.
- Approve from Watchtower: `POST http://localhost:8001/orion/approve { "id": "<task_file_stem>" }`.
- Expect: Artisan will execute (only for approved), logging `task_success` with `approved_override: true`.

7) Archy sentinel
- Command: `python -S factory_agents/archy.py --once --threshold 0.05`
- To simulate, add an entry to logs/genesis_activity.jsonl with `{"ethical_drift": 0.06}`.
- Expect: alerts/ethical_drift.jsonl receives an alert record.

## Notes
- The executor allowlist currently permits only: pytest, python, git, echo. All other commands require explicit approval.
- Federation manifest updated to status: active (v7.5).
- No network keys or secrets added. Existing `.env` should be removed from VCS and rotated per governance.
