# Phase 9.3 — Integrated Intelligence & Observability

Date: 2025-10-25

This document describes the additions for Phase 9.3: GPT assistant integration (stub), live telemetry streaming, and Prometheus metrics exposure for the Governance Console.

## Components

- GPT Assistant Endpoint (stub)
  - Path: `src/agent_factory/api/gpt_endpoint.py`
  - Route: `POST /api/gpt/query`
  - Behavior: Accepts `{ "query": "..." }` or `{ "question": "..." }`, returns deterministic stub JSON without external calls.
  - Security: Protected by optional Bearer token (env `OPERATOR_TOKEN`).

- Telemetry WebSocket
  - Path: `src/agent_factory/api/telemetry_ws.py`
  - Route: `WS /api/ws/telemetry`
  - Behavior: Emits a welcome heartbeat, then `[AUDIT] governance heartbeat` every `WS_INTERVAL_SEC` (default 5s).
  - Security: Protected by optional Bearer token (env `OPERATOR_TOKEN`).

- Prometheus Metrics
  - Path: `src/agent_factory/utils/metrics.py`
  - Exporter Mount: `/metrics` (plain text exposition)
  - Metrics:
    - `governance_events_total` (Counter)
    - `api_request_latency_seconds` (Summary)

- Console Wiring
  - File: `src/agent_factory/console/app.py`
  - Adds routers and mounts Prometheus exporter.

- Frontend UI
  - `frontend/src/pages/Dashboard.tsx` opens a WebSocket to `/api/ws/telemetry` and displays the last 50 live messages.
  - `frontend/src/pages/JunieConsole.tsx` adds an input to query `/api/gpt/query` and displays the JSON response.

## Environment

- `.env.example` additions:
  - `OPERATOR_TOKEN=` (optional; when set, required as `Authorization: Bearer <token>` for GPT/WS)
  - `OAUTH_CLIENT_ID=` and `OAUTH_CLIENT_SECRET=` placeholders for a future Google OAuth integration.

## Verification

- Test 1: `POST /api/gpt/query` → `{ "response": "[GPT-5] received query: ..." }`
- Test 2: `WS /api/ws/telemetry` streams JSON messages every few seconds.
- Test 3: `GET /metrics` contains `governance_events_total` in Prometheus format.

## Notes

- GPT calls are stubbed to avoid external dependencies; real model calls can be enabled later.
- For production, prefer OAuth2 (Google Sign-In) and restrict CORS; OPERATOR_TOKEN is a minimal gate for dev.
