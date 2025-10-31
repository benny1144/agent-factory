# 🧱 Junie Task Document 05 — Governance Maturity Extensions
**Date:** 2025-10-28  
**Group:** Governance Maturity Extensions  
**Scope:** Extend the Human Operations Layer with advanced governance features — including role-based permissions, event replay, ethical drift monitoring, integrity verification, and procedural memory sync.  
**Phases Covered:** Phase 8

---

## [JUNIE TASK 18]
**Title:** Implement Role-Scoped Permissions

**Preconditions:** Authentication functional.

**Plan:**
1. Add `config/roles.yaml` with role definitions.
2. Create `/src/agent_factory/utils/roles.py` for access validation.
3. Apply `@requires_role` decorator to sensitive endpoints.

**Edits:**
```yaml
# /config/roles.yaml
roles:
  compliance_lead:
    permissions:
      - approve_tasks
      - view_audit
      - manage_alerts
  reviewer:
    permissions:
      - approve_tasks
      - view_audit
  observer:
    permissions:
      - view_audit
```

```python
# /src/agent_factory/utils/roles.py
import yaml, os
from functools import wraps

with open(os.getenv('ROLE_CONFIG_PATH', 'config/roles.yaml')) as f:
    ROLES = yaml.safe_load(f)['roles']

def requires_role(required_perm):
    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            user_role = kwargs.get('user', {}).get('role', 'observer')
            if required_perm not in ROLES.get(user_role, {}).get('permissions', []):
                raise Exception('403: Forbidden – insufficient permissions')
            return await fn(*args, **kwargs)
        return wrapper
    return decorator
```

**Verification:**
- Users restricted by permissions.
- Unauthorized actions raise `403`.

**Rollback:** Delete `roles.py` and `roles.yaml`.

---

## [JUNIE TASK 19]
**Title:** Implement Event Replay Timeline API

**Preconditions:** Governance Middleware logging events.

**Plan:**
1. Create `/src/agent_factory/api/audit_timeline.py`.
2. Return all events for a given task, ordered chronologically.

**Edits:**
```python
# /src/agent_factory/api/audit_timeline.py
from fastapi import APIRouter, Depends
from src.agent_factory.database import get_session
from src.agent_factory.models.hitl_schema import AuditLog

router = APIRouter(prefix="/api/audit/timeline", tags=["Audit Timeline"])

@router.get("/{task_id}")
def get_timeline(task_id: str, db=Depends(get_session)):
    logs = db.query(AuditLog).filter(AuditLog.task_id == task_id).order_by(AuditLog.timestamp.asc()).all()
    return [{
        'timestamp': log.timestamp,
        'actor': log.actor,
        'action': log.action,
        'hash': log.hash
    } for log in logs]
```

**Verification:**
- `/api/audit/timeline/<task_id>` returns valid event sequence.

**Rollback:** Remove API route.

---

## [JUNIE TASK 20]
**Title:** Implement Ethical Drift Monitor

**Preconditions:** Cloud Logging active.

**Plan:**
1. Add `/workers/drift_monitor.py`.
2. Query Cloud Logging for autonomy ratio.
3. Trigger Slack warning if threshold exceeded.

**Edits:**
```python
# /workers/drift_monitor.py
from google.cloud import logging_v2
import os, httpx

THRESHOLD = float(os.getenv('DRIFT_THRESHOLD', 0.7))
SLACK_WEBHOOK = os.getenv('SLACK_COMPLIANCE_WEBHOOK')

def check_drift():
    client = logging_v2.Client(project=os.getenv('GCP_PROJECT_ID'))
    entries = list(client.list_entries(filter_='metric.type="custom.googleapis.com/autonomy_ratio"', page_size=20))
    ratios = [e.payload.get('value', 0) for e in entries if hasattr(e, 'payload')]
    avg_ratio = sum(ratios)/len(ratios) if ratios else 0
    if avg_ratio > THRESHOLD:
        httpx.post(SLACK_WEBHOOK, json={"text": f"⚠️ Ethical Drift Warning: autonomy ratio {avg_ratio:.2f}"})

if __name__ == '__main__':
    check_drift()
```

**Verification:**
- When ratio > threshold → Slack alert sent.

**Rollback:** Delete worker.

---

## [JUNIE TASK 21]
**Title:** Implement Procedural Memory Sync

**Preconditions:** Qdrant vector DB running.

**Plan:**
1. Add `/src/agent_factory/services/memory_sync.py`.
2. Push approved proposals to `qdrant_procedural` index.

**Edits:**
```python
# /src/agent_factory/services/memory_sync.py
from qdrant_client import QdrantClient
import os
client = QdrantClient(url=os.getenv('QDRANT_URL'))

def sync_proposal(proposal_id, content, metadata):
    client.upsert(
        collection_name='qdrant_procedural',
        points=[{
            'id': proposal_id,
            'vector': metadata.get('embedding', []),
            'payload': {'content': content, **metadata}
        }]
    )
    print(f"Synced proposal {proposal_id} to Qdrant.")
```

**Verification:**
- Approved proposals appear in Qdrant.

**Rollback:** Remove service file.

---

## [JUNIE TASK 22]
**Title:** Implement Integrity Verification Cron

**Preconditions:** GCP Logging functional.

**Plan:**
1. Create `/workers/integrity_cron.py`.
2. Compare local and GCP hashes nightly.
3. Send alert if mismatches detected.

**Edits:**
```python
# /workers/integrity_cron.py
from src.agent_factory.database import get_session
from src.agent_factory.models.hitl_schema import AuditLog
from google.cloud import logging_v2
import os, httpx

def run_integrity_check():
    db = get_session()
    local_hashes = {log.hash for log in db.query(AuditLog).all()}
    client = logging_v2.Client(project=os.getenv('GCP_PROJECT_ID'))
    entries = list(client.list_entries(filter_='logName:compliance-kernel-audit', page_size=100))
    gcp_hashes = {e.payload.get('hash') for e in entries if hasattr(e, 'payload')}

    missing = local_hashes - gcp_hashes
    if missing:
        httpx.post(os.getenv('SLACK_COMPLIANCE_WEBHOOK'), json={"text": f"⚠️ Integrity mismatch detected: {len(missing)} missing entries."})
    else:
        print("✅ Integrity check passed.")

if __name__ == '__main__':
    run_integrity_check()
```

**Verification:**
- Cron detects hash mismatch and alerts Slack.

**Rollback:** Delete worker.

---

✅ **End of Document 05 — Governance Maturity Extensions**