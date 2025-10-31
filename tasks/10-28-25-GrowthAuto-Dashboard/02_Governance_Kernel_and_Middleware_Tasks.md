# 🧱 Junie Task Document 02 — Governance Kernel & Middleware
**Date:** 2025-10-28  
**Group:** Compliance Kernel + Governance Middleware  
**Scope:** Implement immutable audit trails, event hashing, governance middleware, and local compliance logging for Agent Factory’s Human Operations Layer.  
**Phases Covered:** Phase 4

---

## [JUNIE TASK 6]
**Title:** Implement Compliance Kernel (Hashing + Audit Logging)

**Preconditions:**  
- DB models from Document 01 in place.  
- Environment variable `GCP_PROJECT_ID` set.

**Plan:**
1. Create `/src/agent_factory/utils/hashing.py` and `/src/agent_factory/utils/compliance_kernel.py`.
2. Integrate SHA-256 hashing for event bodies.
3. Add function `log_event(component, action, actor, target_id, details)`.
4. Store hashes in `AuditLog` and mirror locally.

**Edits:**
```python
# /src/agent_factory/utils/hashing.py
import hashlib, json

def compute_event_hash(event: dict) -> str:
    serialized = json.dumps(event, sort_keys=True).encode('utf-8')
    return hashlib.sha256(serialized).hexdigest()

# /src/agent_factory/utils/compliance_kernel.py
from src.agent_factory.models.hitl_schema import AuditLog
from src.agent_factory.utils.hashing import compute_event_hash
from datetime import datetime
from src.agent_factory.database import get_session

def log_event(component: str, action: str, actor: str, target_id: str, details: dict = None):
    db = get_session()
    event = {
        'component': component,
        'action': action,
        'actor': actor,
        'target_id': target_id,
        'details': details or {},
        'timestamp': datetime.utcnow().isoformat()
    }
    event_hash = compute_event_hash(event)
    record = AuditLog(
        component=component,
        action=action,
        actor=actor,
        actor_type='system' if actor.startswith('agent_') else 'human',
        phase='Governance Kernel',
        target_id=target_id,
        details=details,
        hash=event_hash
    )
    db.add(record)
    db.commit()
    return event_hash
```

**Tests:**
```bash
pytest tests/test_compliance_kernel.py
```

**Verification:**
- Hash computed and stored for every event.
- Duplicate events yield identical hashes.

**Rollback:** Delete files `/utils/hashing.py` and `/utils/compliance_kernel.py`.

---

## [JUNIE TASK 7]
**Title:** Implement Governance Middleware (Global API Event Capture)

**Preconditions:** Compliance Kernel functional.

**Plan:**
1. Create `/src/agent_factory/utils/governance_middleware.py`.
2. Intercept all API and WebSocket events.
3. Compute event hash and call `log_event()`.

**Edits:**
```python
# /src/agent_factory/utils/governance_middleware.py
from starlette.middleware.base import BaseHTTPMiddleware
from src.agent_factory.utils.compliance_kernel import log_event
import json

class GovernanceMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        try:
            actor = request.headers.get('X-User', 'anonymous')
            component = request.url.path
            action = request.method
            details = {
                'status_code': response.status_code,
                'path': str(request.url.path),
                'method': request.method
            }
            log_event(component, action, actor, None, details)
        except Exception as e:
            print(f"[GovernanceMiddleware] Error: {e}")
        return response
```

**Integration:**
```python
# /src/agent_factory/main.py
from src.agent_factory.utils.governance_middleware import GovernanceMiddleware

app.add_middleware(GovernanceMiddleware)
```

**Tests:**
```bash
pytest tests/test_governance_middleware.py
```

**Verification:**
- Every API call generates an `AuditLog` entry.
- Each entry contains valid SHA-256 hash.

**Rollback:** Remove middleware import from `main.py`.

---

## [JUNIE TASK 8]
**Title:** Extend AuditLog Model for Local + Cloud Traceability

**Preconditions:** Governance Middleware active.

**Plan:**
1. Add fields for `gcp_log_id` and `sync_status` to `AuditLog`.
2. Prepare schema migration.

**Edits:**
```python
# /src/agent_factory/models/hitl_schema.py
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    component = Column(String)
    action = Column(String)
    actor = Column(String)
    actor_type = Column(String)
    phase = Column(String)
    target_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON)
    hash = Column(String)
    gcp_log_id = Column(String, nullable=True)
    sync_status = Column(String, default='local')
```

**Tests:**
```bash
alembic revision --autogenerate -m "Add GCP trace fields to AuditLog"
alembic upgrade head
```

**Verification:**
- Fields exist in DB.
- Default `sync_status` set to `local`.

**Rollback:**
```bash
alembic downgrade -1
```

---

## [JUNIE TASK 9]
**Title:** Add Local Compliance Console Commands

**Preconditions:** Compliance Kernel active.

**Plan:**
1. Create `/scripts/compliance_console.py`.
2. Add basic commands to view and verify audit logs.

**Edits:**
```python
# /scripts/compliance_console.py
import click
from src.agent_factory.database import get_session
from src.agent_factory.models.hitl_schema import AuditLog

@click.group()
def cli():
    pass

@cli.command()
def list_logs():
    db = get_session()
    for log in db.query(AuditLog).all():
        print(f"[{log.timestamp}] {log.actor} -> {log.component}: {log.action} | {log.hash}")

@cli.command()
def verify_hashes():
    db = get_session()
    valid = 0
    total = 0
    for log in db.query(AuditLog).all():
        total += 1
        computed = compute_event_hash({
            'component': log.component,
            'action': log.action,
            'actor': log.actor,
            'timestamp': log.timestamp.isoformat(),
            'details': log.details or {}
        })
        if computed == log.hash:
            valid += 1
    print(f"Integrity check: {valid}/{total} entries valid")

if __name__ == '__main__':
    cli()
```

**Tests:**
```bash
python scripts/compliance_console.py list_logs
python scripts/compliance_console.py verify_hashes
```

**Verification:**
- Logs printed to console.
- Hash verification successful.

**Rollback:** Delete `/scripts/compliance_console.py`.

---

✅ **End of Document 02 — Governance Kernel & Middleware**