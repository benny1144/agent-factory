# 🧱 Junie Task Document 04 — Dashboard & Alerts Integration
**Date:** 2025-10-28  
**Group:** GCP Compliance Dashboard + Slack Governance Loop  
**Scope:** Implement the live governance layer for Agent Factory’s Human Operations Layer — including GCP monitoring dashboards, alert policies, and Slack-based HITL interaction.  
**Phases Covered:** Phase 6–7

---

## [JUNIE TASK 13]
**Title:** Create GCP Compliance Dashboard

**Preconditions:**  
- GCP Logging integration from Phase 5 completed.  
- Compliance Kernel emitting logs successfully.

**Plan:**  
1. Create GCP Dashboard `Agent Factory – Compliance & HITL Oversight` using `dashboard.json`.  
2. Define six widgets and four alert policies.  
3. Store dashboard definition at `/gcp/dashboard/compliance_dashboard.json`.

**Edits:**
```json
{
  "displayName": "Agent Factory – Compliance & HITL Oversight",
  "gridLayout": {
    "columns": 3,
    "widgets": [
      {"title": "HITL Tasks – Pending vs Approved", "xyChart": {"dataSets": [{"timeSeriesQuery": {"timeSeriesFilter": {"filter": "metric.type=\"custom.googleapis.com/hitl_tasks_count\""}}}]}},
      {"title": "Audit Log Throughput", "xyChart": {"dataSets": [{"timeSeriesQuery": {"timeSeriesFilter": {"filter": "metric.type=\"custom.googleapis.com/audit_events_per_minute\""}}}]}},
      {"title": "Autonomy Ratio (Ethical Drift)", "xyChart": {"dataSets": [{"timeSeriesQuery": {"timeSeriesFilter": {"filter": "metric.type=\"custom.googleapis.com/autonomy_ratio\""}}}]}},
      {"title": "Slack Alert Latency", "xyChart": {"dataSets": [{"timeSeriesQuery": {"timeSeriesFilter": {"filter": "metric.type=\"custom.googleapis.com/slack_alert_latency\""}}}]}},
      {"title": "Active WebSocket Sessions", "xyChart": {"dataSets": [{"timeSeriesQuery": {"timeSeriesFilter": {"filter": "metric.type=\"custom.googleapis.com/ws_connections\""}}}]}},
      {"title": "GCP Log Sync Status", "xyChart": {"dataSets": [{"timeSeriesQuery": {"timeSeriesFilter": {"filter": "metric.type=\"custom.googleapis.com/gcp_log_sync_success\""}}}]}}
    ]
  }
}
```

**Deploy Command:**
```bash
gcloud monitoring dashboards create --config-from-file=gcp/dashboard/compliance_dashboard.json
```

**Verification:**
- Dashboard appears in GCP → Monitoring → Dashboards.
- Metrics display correctly.

**Rollback:**
```bash
gcloud monitoring dashboards delete "Agent Factory – Compliance & HITL Oversight"
```

---

## [JUNIE TASK 14]
**Title:** Configure GCP Alert Policies

**Preconditions:** Dashboard created.

**Plan:**  
Create four alerting policies:
1. Drift Warning (autonomy ratio > 0.7)
2. Log Sync Failure
3. Slack Alert Latency > 60s
4. Excessive Pending HITL Tasks

**Commands:**
```bash
# 1. Ethical Drift Warning
gcloud monitoring policies create --display-name="Ethical Drift Warning" \
  --condition-display-name="Autonomy Ratio > 0.7" \
  --notification-channels="projects/$GCP_PROJECT_ID/notificationChannels/slack-channel" \
  --combiner=OR \
  --condition-filter="metric.type=\"custom.googleapis.com/autonomy_ratio\" AND metric.label.phase=\"Governance Kernel\"" \
  --condition-threshold-value=0.7

# 2. Log Sync Failure
gcloud monitoring policies create --display-name="Log Sync Failure" \
  --condition-display-name="Missing GCP Audit Logs" \
  --notification-channels="projects/$GCP_PROJECT_ID/notificationChannels/slack-channel" \
  --condition-filter="metric.type=\"custom.googleapis.com/gcp_log_sync_success\"" \
  --condition-threshold-value=0.9 --comparison=COMPARISON_LT
```

**Verification:**
- Alerts visible under GCP → Monitoring → Alerting.
- Slack notifications trigger correctly.

**Rollback:**
```bash
gcloud monitoring policies delete "Ethical Drift Warning"
gcloud monitoring policies delete "Log Sync Failure"
```

---

## [JUNIE TASK 15]
**Title:** Implement Slack Alert Webhook Handler

**Preconditions:** Slack Webhook and Signing Secret set.

**Plan:**
1. Add `/src/agent_factory/api/alert_webhook.py`.
2. Accept GCP alerts and forward to Slack.

**Edits:**
```python
# /src/agent_factory/api/alert_webhook.py
from fastapi import APIRouter, Request
import httpx, os

router = APIRouter(prefix="/api/alert_webhook", tags=["Alert Webhook"])

@router.post("")
async def receive_alert(request: Request):
    data = await request.json()
    webhook_url = os.getenv('SLACK_COMPLIANCE_WEBHOOK')
    message = f"⚠️ *GCP Alert:* {data.get('incident', {}).get('policy_name', 'Unknown')}\nStatus: {data.get('incident', {}).get('state', 'N/A')}"
    async with httpx.AsyncClient() as client:
        await client.post(webhook_url, json={"text": message})
    return {"status": "forwarded"}
```

**Verification:**
- GCP alert → HTTP POST → `/api/alert_webhook` → Slack message visible.

**Rollback:** Delete `/src/agent_factory/api/alert_webhook.py`.

---

## [JUNIE TASK 16]
**Title:** Implement Slack Commands and HITL Actions

**Preconditions:** Webhook handler active.

**Plan:**
1. Create `/src/agent_factory/api/slack_commands.py` and `/src/agent_factory/api/slack_actions.py`.
2. Add endpoints for `/hitl` slash command and interactive button callbacks.

**Edits:**
```python
# /src/agent_factory/api/slack_commands.py
from fastapi import APIRouter, Form
import os
from src.agent_factory.services.hitl_repository import task_service

router = APIRouter(prefix="/api/slack", tags=["Slack Commands"])

@router.post("/command")
async def handle_command(command: str = Form(...), text: str = Form(...)):
    if command == '/hitl':
        parts = text.split()
        if parts[0] == 'resolve':
            task_id = parts[1]
            task_service.update_task_status(None, task_id, 'approved', 'slack_user')
            return {"response_type": "in_channel", "text": f"✅ Task {task_id} approved."}
    return {"text": "Unrecognized command."}

# /src/agent_factory/api/slack_actions.py
from fastapi import APIRouter, Request
import httpx, os
from src.agent_factory.services.hitl_repository import task_service

router = APIRouter(prefix="/api/slack/actions", tags=["Slack Actions"])

@router.post("")
async def handle_action(request: Request):
    payload = await request.form()
    data = json.loads(payload.get('payload'))
    action = data['actions'][0]['value']
    task_id = data['actions'][0]['block_id']
    if action == 'approve':
        task_service.update_task_status(None, task_id, 'approved', 'slack_user')
    elif action == 'reject':
        task_service.update_task_status(None, task_id, 'rejected', 'slack_user')
    return {"status": "ok"}
```

**Verification:**
- `/hitl resolve <id>` works in Slack.
- Buttons `[Approve]` and `[Reject]` update dashboard instantly.

**Rollback:** Remove Slack command routes.

---

## [JUNIE TASK 17]
**Title:** Connect Slack Alerts to Dashboard Notifications

**Preconditions:** WebSocket bridge active.

**Plan:**
1. Modify `websocket_bridge.py` to listen for Slack action updates.
2. Broadcast updates to dashboard clients.

**Edits:**
```python
# /src/agent_factory/api/websocket_bridge.py
async def broadcast_task_update(task_id, status):
    for user, ws in connections.items():
        await ws.send_json({"event": "task_update", "task_id": task_id, "status": status})

# /src/agent_factory/api/slack_actions.py (append)
await broadcast_task_update(task_id, action)
```

**Verification:**
- Slack actions reflect live in dashboard UI.

**Rollback:** Remove broadcast call.

---

✅ **End of Document 04 — Dashboard & Alerts Integration**