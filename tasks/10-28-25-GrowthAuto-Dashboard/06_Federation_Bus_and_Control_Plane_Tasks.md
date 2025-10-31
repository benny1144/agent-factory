# 🧱 Junie Task Document 06 — Federation Bus & Control Plane
**Date:** 2025-10-28  
**Group:** Federation Bus + Agent Factory Expert Integration  
**Scope:** Implement the Federation Bus infrastructure for agent-to-agent communication and integrate Agent Factory Expert as the live governance control plane.  
**Phases Covered:** Federation Expansion (Phase 9)

---

## [JUNIE TASK 23]
**Title:** Implement Federation Bus Core

**Preconditions:** H-OL operational; WebSocket infrastructure functional.

**Plan:**
1. Create `/src/agent_factory/federation/bus/router.py`, `/registry.py`, `/policy_guard.py`, `/observer.py`.
2. Add WebSocket endpoint `/federation/ws/<agent_id>`.
3. Maintain active registry of agents.

**Edits:**
```python
# /src/agent_factory/federation/bus/registry.py
from typing import Dict

class FederationRegistry:
    def __init__(self):
        self.agents: Dict[str, object] = {}

    def register(self, agent_id: str, ws):
        self.agents[agent_id] = ws

    def unregister(self, agent_id: str):
        if agent_id in self.agents:
            del self.agents[agent_id]

    async def broadcast(self, message: dict):
        for ws in self.agents.values():
            await ws.send_json(message)

registry = FederationRegistry()
```

```python
# /src/agent_factory/federation/bus/policy_guard.py
from src.agent_factory.utils.compliance_kernel import log_event

async def enforce_policy(message):
    if message.get('type') == 'directive' and message.get('metadata', {}).get('requires_hitl'):
        log_event('FederationBus', 'blocked_directive', 'policy_guard', message.get('target'), message)
        raise Exception('Directive requires HITL approval')
    log_event('FederationBus', 'allow_message', 'policy_guard', message.get('target'), message)
```

```python
# /src/agent_factory/federation/bus/router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from src.agent_factory.federation.bus.registry import registry
from src.agent_factory.federation.bus.policy_guard import enforce_policy
import json

router = APIRouter(prefix="/federation/ws", tags=["Federation Bus"])

@router.websocket("/{agent_id}")
async def federation_ws(ws: WebSocket, agent_id: str):
    await ws.accept()
    registry.register(agent_id, ws)
    try:
        while True:
            data = await ws.receive_text()
            message = json.loads(data)
            await enforce_policy(message)
            await registry.broadcast(message)
    except WebSocketDisconnect:
        registry.unregister(agent_id)
```

**Verification:**
- Multiple agents connect and broadcast messages.
- Policy guard enforces HITL rules.

**Rollback:** Remove federation module.

---

## [JUNIE TASK 24]
**Title:** Implement Federation Message Schema Validation

**Preconditions:** Federation Bus operational.

**Plan:**
1. Create `/src/agent_factory/federation/schema/federation_message.json`.
2. Add `/src/agent_factory/federation/utils/validator.py` to enforce schema validation.

**Edits:**
```json
# /src/agent_factory/federation/schema/federation_message.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "FederationMessage",
  "type": "object",
  "required": ["id", "source", "target", "type", "timestamp", "payload"],
  "properties": {
    "id": {"type": "string"},
    "source": {"type": "string"},
    "target": {"type": ["string", "array"]},
    "type": {"type": "string"},
    "payload": {"type": "object"},
    "metadata": {"type": "object"},
    "timestamp": {"type": "string", "format": "date-time"},
    "hash": {"type": "string"}
  }
}
```

```python
# /src/agent_factory/federation/utils/validator.py
import jsonschema, json
from src.agent_factory.utils.compliance_kernel import log_event

with open('src/agent_factory/federation/schema/federation_message.json') as f:
    FEDERATION_SCHEMA = json.load(f)

def validate_message(message):
    try:
        jsonschema.validate(instance=message, schema=FEDERATION_SCHEMA)
        return True
    except jsonschema.ValidationError as e:
        log_event('FederationBus', 'invalid_message', 'validator', message.get('target'), {'error': str(e)})
        raise e
```

**Verification:**
- Invalid messages rejected and logged.

**Rollback:** Remove validator.

---

## [JUNIE TASK 25]
**Title:** Integrate Agent Factory Expert (Control Plane Observer)

**Preconditions:** Federation Bus active.

**Plan:**
1. Create `/src/agent_factory/federation/bus/observer.py`.
2. Subscribe Agent Factory Expert to all events as `control_plane`.
3. Generate insights and compliance alerts.

**Edits:**
```python
# /src/agent_factory/federation/bus/observer.py
from src.agent_factory.federation.bus.registry import registry
from src.agent_factory.utils.compliance_kernel import log_event
import asyncio

class ControlPlaneObserver:
    def __init__(self):
        self.id = 'control_plane'

    async def observe_event(self, message):
        log_event('ControlPlane', 'observe', self.id, message.get('target'), message)
        # Generate meta-insight for dashboard
        insight = {
            'source': 'control_plane',
            'type': 'insight',
            'payload': {
                'summary': f"Agent {message['source']} sent {message['type']} to {message['target']}",
                'risk': 'low'
            }
        }
        await registry.broadcast(insight)

observer = ControlPlaneObserver()
```

**Integration:**
```python
# /src/agent_factory/federation/bus/router.py (inside loop)
await observer.observe_event(message)
```

**Verification:**
- Expert receives and broadcasts insights.
- Dashboard InsightFeed shows meta commentary.

**Rollback:** Remove observer import.

---

## [JUNIE TASK 26]
**Title:** Extend Dashboard — Federation Monitor Suite

**Preconditions:** Federation Bus running.

**Plan:**
1. Create `/ui/components/federation/` directory.
2. Add components for monitoring, insights, and directives.

**Edits:**
```javascript
// /ui/components/federation/FederationPanel.jsx
import React, { useEffect, useState } from 'react';
export default function FederationPanel() {
  const [events, setEvents] = useState([]);
  useEffect(() => {
    const ws = new WebSocket(`wss://${window.location.host}/federation/ws/control_plane`);
    ws.onmessage = (msg) => setEvents((e) => [...e, JSON.parse(msg.data)]);
    return () => ws.close();
  }, []);
  return (
    <div className="p-4">
      <h2 className="text-xl font-bold mb-2">Federation Bus Monitor</h2>
      <div className="h-96 overflow-y-scroll bg-gray-900 text-green-400 p-2 rounded-xl">
        {events.map((e, i) => (
          <pre key={i}>{JSON.stringify(e, null, 2)}</pre>
        ))}
      </div>
    </div>
  );
}
```

**Verification:**
- Dashboard displays live federation messages.
- Insights visible in control panel.

**Rollback:** Remove `/ui/components/federation/`.

---

✅ **End of Document 06 — Federation Bus & Control Plane Integration**