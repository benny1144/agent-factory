# Agent Factory v7.5 — Watchtower Expansion

Bridge from Federated Growth Autonomy (v7) to Meta-Agent Orchestration (v7.5)

- Introduces Orion (meta-orchestrator)
- Deploys Watchtower (dashboard interface)
- Replaces Junie with Artisan (executor)
- Begins live federation synchronization

## Overview
Version 7.5 transitions the control plane from a single-bridge paradigm to a meta-orchestrated model:

- Orion: Headless meta-orchestrator that watches for tasks and coordinates execution.
- Watchtower: Human-facing interface that streams Orion logs and forwards operator commands.
- Artisan: Deterministic executor responsible for running commands/materializing artifacts.

## Activation
- Federation manifest v2: `federation/context_manifest_v2.json` set to `version: v7.5`.
- Activation date: 2025-11-01T00:00:00Z

## Migration Notes
- Junie Bridge remains available for rollback. To revert, restore the v7 snapshot from `archives/factory_v7_final/` and re-activate Junie executors.
- Human Firewall approvals should be surfaced in Watchtower UI as dedicated events in the log stream.

## Governance Handoff → Orion Autonomy
- Handoff record: `governance/audits/federation_handoff_v7_5.json` with `{"ts":"<UTC>","phase":38,"handoff":"complete","controller":"Orion"}`.
- Federation Loop: Orion emits heartbeats every 30s (and pings Genesis each cycle). Entries appear in `logs/orion_activity.jsonl`.
- Governance Event Bus: `governance/event_bus.jsonl` aggregates standardized events from all agents (Genesis build_complete, Artisan executions, Archy alerts, Orion heartbeats).
- Watchtower: "Federation Loop" dashboard streams the Event Bus (`/gov/stream`) and shows status lights (🟢 seen <2m, 🟡 <5m, 🔴 stale) and per-agent metrics.
