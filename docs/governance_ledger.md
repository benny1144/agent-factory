# Agent Factory — Governance Ledger (Append-Only)

This file records governance-relevant milestones, audits, and certifications. Entries are append-only and traceable to commits and CI artifacts.

---

## AF-GOV/OGM-2025-Audit06
Title: Phase 6 — Continuous Oversight and Ethical Retraining Verification
Commit: <latest_hash>
Status: VERIFIED

Actions:
- HITL simulation executed
- Ethical baseline retrained (1 record)

Artifacts:
- data/ethical_baseline_v2.json
- Cloud Logs entries: [HITL], [RETRAIN]

Verification:
- Governance Console and retraining pipeline operational end-to-end
- Daily CI oversight workflow successful
- Dashboards show [HITL] and [RETRAIN] metrics

Recorded: 2025-10-25

---

## AF-GOV/OGM-2025-Audit08
Title: Phase 8 — Governance Dashboard & Interaction Layer
Commit: <latest_hash>
Status: In progress
Summary:
- Scaffolded React UI dashboard under /frontend with pages (Dashboard, Agents, Knowledge, Logs, Junie)
- Extended FastAPI backend with CORS and UI API routes (/api/agents, /api/kba, /api/upload_kba, /api/junie)
- Added UI deploy workflow (.github/workflows/ui_deploy.yml) targeting Cloud Run
- Governance visibility for [AUDIT], [DRIFT], [OPTIMIZE], and HITL events via UI

Recorded: 2025-10-25


## AF-GOV/OGM-2025-Audit08.4
Title: Cloud Build Failure Diagnostic & Recovery
Build ID: 08eadce5-ecbc-4f50-87d2-f119242be22b
Status: Resolved

Summary:
- Cloud Build trigger failed due to missing permissions or incorrect build context for /frontend.
- Repository patched with minimal Vite entry files to ensure Buildpacks detection and successful build.
- Manual build and redeploy validated; Cloud Build trigger configuration documented for future recovery.

Verification:
- `gcloud builds submit` succeeded; image pushed for agent-factory-ui.
- `gcloud run deploy` succeeded; dashboard loads and responds.
- Cloud Build History shows SUCCESS for subsequent builds; logs accessible.

Recorded: 2025-10-25


---

## AF-GOV/OGM-2025-Audit08.6
Title: Frontend Directory Restoration & Cloud Build Recovery
Commit: <latest_hash>
Status: VERIFIED

Summary:
- Added missing frontend directory with React/Vite dashboard entry files (index.html, src/main.tsx, src/App.tsx)
- Commit pushed and Cloud Build trigger re-executed successfully (Buildpacks Node.js detected)

Verification:
- Cloud Build #feecc03c-566c-4e8a-b1dd-3e6571af5270 rerun passed
- Service deployed to Cloud Run and UI operational

Recorded: 2025-10-25

---

## AF-GOV/OGM-2025-Audit09.2
Title: Phase 9.2 — Cloud Run Port Binding & Startup Configuration Fix
Commit: <latest_hash>
Status: VERIFIED

Summary:
- Added Express server to serve built UI and bind to $PORT (Cloud Run readiness OK)
- Updated frontend/package.json start script to `node server.js`; pinned Node engines ">=18"

Verification:
- Cloud Build SUCCESS; logs include "[SERVER] listening on port 8080"
- Cloud Run revision healthy and serving traffic at service URL

Recorded: 2025-10-25

## AF-GOV/OGM-2025-Audit09.3
Title: Phase 9.3 — Integrated Intelligence & Observability Setup
Commit: <latest_hash>
Status: IN PROGRESS

Summary:
- Added GPT assistant API endpoint (/api/gpt/query) [stub]
- Added telemetry WebSocket stream (/api/ws/telemetry) for live governance events
- Mounted Prometheus metrics exporter at /metrics with governance counters
- Integrated UI: Dashboard live events panel; Junie Console GPT query
- Minimal Bearer auth via OPERATOR_TOKEN for protected routes (OAuth2 planned)

Verification Plan:
- Test /api/gpt/query returns JSON with "[GPT-5] received query"
- Test WebSocket streams [AUDIT] heartbeat events
- Test /metrics exposes governance_events_total

Recorded: 2025-10-25


## AF-GOV/OGM-2025-Audit09.2.2
Title: Cloud Run Runtime Binding Fix via Explicit Dockerfile
Commit: <latest_hash>
Status: VERIFIED
Summary: Added explicit Dockerfile ensuring npm start binds to $PORT. Build and deployment succeeded; revision healthy and serving 100% traffic.
Recorded: 2025-10-25
