[JUNIE TASK]

Title: Implement Genesis Listener Auto-Health-Check, Self-Recovery, and Dashboard Integration

Preconditions:

Repo: benny1144/agent-factory

Branch: maintenance/genesis_healthloop

GenesisOrchestrator active at /agents/architect_genesis/main.py

Governance Console (FastAPI + React UI) deployed and accessible

Audit logging functional (/compliance/audit_log/)

🧩 Part 1 — Auto-Health-Check & Self-Recovery Loop

Plan:

Add Health Monitor to GenesisOrchestrator (/agents/architect_genesis/main.py):

def _start_health_monitor(self):
import threading, requests, time, datetime
def monitor():
while self.active and getattr(self, "listener_active", False):
time.sleep(getattr(self, "healthcheck_interval", 60))
try:
r = requests.get(f"http://127.0.0.1:{self.listener_port}/ping", timeout=3)
if r.status_code == 200 and r.json().get("ok"):
self.healthcheck_failures = 0
self._log(f"[Health] OK on port {self.listener_port}")
self._emit_health_event("ok")
else:
raise Exception("Unexpected response")
except Exception as e:
self.healthcheck_failures += 1
self._log(f"[Health] Failed check {self.healthcheck_failures}/"
f"{self.max_failures}: {e}")
self._emit_health_event("fail")
if self.healthcheck_failures >= self.max_failures:
self._log("[Genesis] Listener unresponsive — attempting restart")
try:
self.listen(self.listener_port)
self.healthcheck_failures = 0
self._emit_health_event("restart")
except Exception as re:
self._log(f"[Genesis] Listener restart failed: {re}")
self._emit_health_event("fatal")
threading.Thread(target=monitor, daemon=True).start()

def _emit_health_event(self, status: str):
# Emits to audit log and dashboard (see Part 2)
event = {
"ts": datetime.datetime.utcnow().isoformat(),
"port": getattr(self, "listener_port", None),
"status": status,
"mode": getattr(self, "mode", None)
}
self._log(f"[HealthEvent] {event}")
try:
with open("compliance/audit_log/genesis_health.csv", "a") as f:
f.write(f"{event['ts']},{event['port']},{event['status']},{event['mode']}\n")
except Exception:
pass


Add configuration in /config/genesis.yaml or .env:

GENESIS_HEALTHCHECK_INTERVAL=60
GENESIS_MAX_FAILURES=3


Call _start_health_monitor() at the end of listen().

Audit Logging:
Each ping result is recorded in /compliance/audit_log/genesis_health.csv.

Verification:

[Health] OK on port 5055 appears every minute in logs/genesis_session_*.log.

/ping endpoint responds with {"ok": true}.

Killing the listener triggers [Genesis] Listener unresponsive — attempting restart.

Rollback:
Comment out _start_health_monitor() and remove its thread launch.

🧩 Part 2 — Governance Dashboard Integration

Plan:

Backend (FastAPI) — Add new route in /governance/api/health.py:

from fastapi import APIRouter
import csv, os
router = APIRouter()

@router.get("/health/genesis")
def get_genesis_health():
path = "compliance/audit_log/genesis_health.csv"
if not os.path.exists(path):
return {"ok": False, "data": []}
with open(path) as f:
reader = csv.reader(f)
rows = [{"timestamp": r[0], "port": r[1], "status": r[2], "mode": r[3]} for r in reader]
return {"ok": True, "data": rows[-100:]}  # last 100 entries


Mount this router in the main FastAPI app under /health.

Frontend (React / Vite UI) — Add Genesis Health widget:

Create /src/components/dashboard/GenesisHealthCard.tsx:

import { useEffect, useState } from "react";

export default function GenesisHealthCard() {
const [data, setData] = useState([]);
useEffect(() => {
const fetchHealth = async () => {
const r = await fetch(`${import.meta.env.VITE_API_URL}/health/genesis`);
const j = await r.json();
if (j.ok) setData(j.data);
};
fetchHealth();
const id = setInterval(fetchHealth, 60000);
return () => clearInterval(id);
}, []);
const latest = data[data.length - 1];
return (
<div className="p-4 bg-gray-900 rounded-2xl shadow text-gray-200">
<h2 className="text-lg font-bold mb-2">Genesis Health</h2>
{latest ? (
<div>
<p>Status: <span className={`font-semibold ${latest.status==="ok"?"text-green-400":"text-red-400"}`}>{latest.status}</span></p>
<p>Port: {latest.port}</p>
<p>Mode: {latest.mode}</p>
<p>Updated: {latest.timestamp}</p>
</div>
) : <p>No data yet.</p>}
</div>
);
}


Import this component into your main Dashboard.tsx grid.

Telemetry Feed:

Each [HealthEvent] log automatically appends to the audit CSV and appears in the dashboard via the /health/genesis endpoint.

Optional: Stream updates with WebSocket broadcast if the dashboard already supports live push.

Testing:

Start Genesis listener and open the dashboard.

Confirm “Genesis Health: ok” card updates every minute.

Stop Genesis temporarily → dashboard shows “fail” or “restart” within 60 seconds.

Verification:

genesis_health.csv continuously populates.

Dashboard component displays live health state.

Audit ledger logs listener restarts as separate events.

Rollback:

Remove /governance/api/health.py route import.

Delete GenesisHealthCard.tsx from the dashboard components.

Remove health loop thread call from GenesisOrchestrator.

✅ Expected Outcome

Genesis automatically monitors its listener every 60 seconds.

Listener restarts autonomously after three failed checks.

All health events recorded to /compliance/audit_log/genesis_health.csv.

Governance Dashboard displays a real-time “Genesis Health” card showing status (ok / fail / restart / fatal).

Once Junie executes this task:

Run

python -m tools.genesis_admin --reactivate architect_mode --listen 5055


Open your Governance Dashboard — you’ll see a new card “Genesis Health” with green OK indicators pulsing every minute.