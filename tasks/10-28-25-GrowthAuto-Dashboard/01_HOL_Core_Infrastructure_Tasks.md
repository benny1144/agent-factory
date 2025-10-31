# 🧱 Junie Task Document 01 — H-OL Core Infrastructure
**Date:** 2025-10-28  
**Group:** Human Operations Layer (Core Infrastructure)  
**Scope:** Establish the foundational models, services, API routes, WebSocket bridge, and authentication for Agent Factory’s Human Operations Layer.  
**Phases Covered:** 1–3

---

## [JUNIE TASK 1]
**Title:** Implement H-OL ORM Models and Schema

**Preconditions:**  
- PostgreSQL running.  
- SQLAlchemy + Alembic migrations configured.  

**Plan:**  
1. Create `/src/agent_factory/models/hitl_schema.py` defining `HITLTask`, `ArchyChat`, `AuditLog`, and `Notification`.  
2. Generate Alembic migration.  
3. Apply migrations to DB.

**Edits:**
```python
# /src/agent_factory/models/hitl_schema.py
from sqlalchemy import Column, String, Integer, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from src.agent_factory.database import Base

class HITLTask(Base):
    __tablename__ = 'hitl_tasks'
    id = Column(String, primary_key=True)
    title = Column(String)
    description = Column(String)
    status = Column(String, default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    assigned_to = Column(String)

class ArchyChat(Base):
    __tablename__ = 'archy_chat'
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey('hitl_tasks.id'))
    sender = Column(String)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    component = Column(String)
    action = Column(String)
    actor = Column(String)
    actor_type = Column(String)
    phase = Column(String)
    target_id = Column(String)
    task_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(JSON)
    hash = Column(String)

class Notification(Base):
    __tablename__ = 'notifications'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String)
    message = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**Tests:**
```bash
pytest tests/test_schema_integrity.py
```

**Verification:**
- Tables created successfully.
- Relationships valid.

**Rollback:**
```bash
alembic downgrade -1
```

---

## [JUNIE TASK 2]
**Title:** Implement HITL Repository Layer

**Preconditions:** Models and DB ready.

**Plan:**
1. Create `/src/agent_factory/services/hitl_repository/`.
2. Add `task_service.py`, `chat_service.py`, `audit_service.py`, and `notification_service.py`.

**Edits:**
```python
# /src/agent_factory/services/hitl_repository/task_service.py
def create_task(db, title, description, assigned_to):
    task = HITLTask(title=title, description=description, assigned_to=assigned_to)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task

def update_task_status(db, task_id, status, actor):
    task = db.query(HITLTask).filter(HITLTask.id == task_id).first()
    task.status = status
    db.commit()
    return task

# /src/agent_factory/services/hitl_repository/chat_service.py
def add_chat_message(db, task_id, sender, message):
    chat = ArchyChat(task_id=task_id, sender=sender, message=message)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat
```

**Verification:**
- CRUD operations functional.

**Rollback:** Delete files in `/hitl_repository/`.

---

## [JUNIE TASK 3]
**Title:** Implement API Endpoints for H-OL

**Preconditions:** Repo and services ready.

**Plan:**
1. Create `/src/agent_factory/api/hitl_tasks.py`, `/archy_chat.py`, `/audit.py`, `/notifications.py`.
2. Implement REST CRUD endpoints.

**Edits:**
```python
# /src/agent_factory/api/hitl_tasks.py
from fastapi import APIRouter, Depends
from src.agent_factory.services.hitl_repository import task_service
from src.agent_factory.database import get_session

router = APIRouter(prefix="/api/hitl_tasks", tags=["HITL Tasks"])

@router.post("")
def create_task(data: dict, db=Depends(get_session)):
    return task_service.create_task(db, data['title'], data.get('description', ''), data.get('assigned_to'))

@router.get("")
def list_tasks(db=Depends(get_session)):
    return db.query(HITLTask).all()
```

**Tests:**
```bash
pytest tests/test_api_hitl_tasks.py
```

**Verification:**
- API endpoints functional.
- CRUD roundtrip verified.

**Rollback:** Remove API files.

---

## [JUNIE TASK 4]
**Title:** Implement WebSocket Bridge

**Preconditions:** API + Repository operational.

**Plan:**
1. Create `/src/agent_factory/api/websocket_bridge.py`.
2. Add `event_emitter.py` for broadcast support.

**Edits:**
```python
# /src/agent_factory/api/websocket_bridge.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.agent_factory.utils.auth import verify_jwt

router = APIRouter(prefix="/ws", tags=["WebSocket Bridge"])
connections = {}

@router.websocket("/notifications")
async def websocket_endpoint(ws: WebSocket, token: str):
    user = verify_jwt(token)
    await ws.accept()
    connections[user['id']] = ws
    try:
        while True:
            data = await ws.receive_text()
    except WebSocketDisconnect:
        del connections[user['id']]
```

**Verification:**
- WS connections stable.
- Broadcast to connected clients successful.

**Rollback:** Disable `/ws/notifications` route.

---

## [JUNIE TASK 5]
**Title:** Scoped Authentication & Role Filtering

**Preconditions:** WebSocket bridge online.

**Plan:**
1. Add `/src/agent_factory/utils/auth.py` for JWT verification.
2. Add role-based filters.

**Edits:**
```python
# /src/agent_factory/utils/auth.py
import jwt, os

def verify_jwt(token: str):
    secret = os.getenv('JWT_SECRET_KEY')
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise Exception('Token expired')
    except jwt.InvalidTokenError:
        raise Exception('Invalid token')
```

**Verification:**
- Invalid tokens rejected.
- Authorized users only.

**Rollback:** Remove `auth.py` and WS token validation.

---

✅ **End of Document 01 — H-OL Core Infrastructure**