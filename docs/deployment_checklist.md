# Phase 5 Deployment — Cloud Run Activation & Governance Dashboard Setup

This checklist guides deployment of the Governance Console (FastAPI) to Google Cloud Run and configuration of Cloud Logging + Monitoring dashboards.

Prerequisites
- Repo: benny1144/agent-factory @ v1.0.1
- GCP project with Cloud Run and Cloud Logging APIs enabled
- gcloud CLI authenticated and configured (gcloud auth login; gcloud config set project <PROJECT_ID>)
- Python build uses requirements.txt (includes fastapi, uvicorn)

Key service
- FastAPI app: src.agent_factory.console.app:app
- Root health endpoint: GET / → returns text "Agent Factory Console Active"
- Additional endpoints:
  - GET /healthz → returns text "Agent Factory Console Active"
  - GET /drift → latest ethical drift telemetry (JSON)
  - GET /optimization → optimization events (JSON)
  - GET /api/audit → local audit file listing (JSON)

1) Deploy to Cloud Run

export REGION=us-central1
export SERVICE=agent-factory-console

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "PYTHONPATH=src"

Expected output: a public URL like https://agent-factory-console-<hash>-uc.a.run.app/

2) Smoke test endpoints

# Replace $URL with the service URL from the deploy output
URL=https://agent-factory-console-<hash>-uc.a.run.app

curl -sS $URL/
# => Agent Factory Console Active

curl -sS $URL/healthz
# => Agent Factory Console Active

curl -sS $URL/drift | jq .
curl -sS $URL/optimization | jq .
curl -sS $URL/api/audit | jq .

3) Configure Cloud Logging sink (optional, recommended)

# Create a bucket sink (replace with your bucket)
BUCKET=gs://<YOUR_BUCKET>

gcloud logging sinks create agent-factory-governance \
  "$BUCKET" \
  --log-filter="resource.type=cloud_run_revision"

Validate that logs containing [AUDIT], [HITL], [DRIFT], [OPTIMIZE] flow into the bucket.

4) Simulate telemetry events

# HITL and retrain events
python scripts/retrain_ethical_baseline.py
python -m src.agent_factory.console.hitl_logger

# Ethical drift (optional)
python -m src.agent_factory.monitoring.ethical_drift

Re-check Cloud Logs for new entries with current timestamps.

5) Build Monitoring dashboard (GCP Console → Monitoring → Dashboards)
- Create dashboard: "Agent Factory Governance"
- Add charts:
  - Mean Ethical Drift (per day) from logs/artifacts
  - Optimization Frequency (count of optimization_adjustment)
  - HITL Events (count of [HITL])
  - Audit Integrity ([AUDIT] counts over time)
- Alerts:
  - Drift > 0.35
  - No [AUDIT] entries for > 24 hours

6) Governance ledger entry
Record deployment in the internal ledger:
- Key: AF-DEPLOY/OGM-2025-Prod01
- Tag: v1.0.1
- Commit: <latest_hash>
- Environment: GCP Cloud Run (us-central1)
- Audit Bucket: gs://<your-audit-bucket>
- Validation: Console endpoints responsive + Cloud Logs receiving

Rollback

gcloud run services delete agent-factory-console --region us-central1
# To restore, redeploy last known validated tag v1.0.1

Notes
- The repo includes a Procfile for uvicorn startup on Cloud Run:
  web: uvicorn src.agent_factory.console.app:app --host 0.0.0.0 --port $PORT
- Requirements include FastAPI and Uvicorn.
- PYTHONPATH=src is set during deploy to resolve module imports.
