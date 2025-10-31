# Federation Activation & Live Command Flow — Verification Report

Date: 2025-10-28 14:26 (local)
Report ID: Federation-Activation-2025-10-28
Author: Junie (JetBrains AI Implementor)
Location: tasks/reviews/Federation_Activation_Verification.md

---

## 1) Scope
Lean, operator-focused checklist to activate the Federation Bridge and verify live command flow between AgentFactoryExpert → Archy (and Genesis where applicable). No UI layer required.

## 2) Preconditions
- Repo: `agent-factory`
- `federation/context_manifest.json` present and valid
  - Agents include: `AgentFactoryExpert`, `Archy`, `Genesis`
- Poetry environment active (optional; the bridge uses plain Python)
- These paths exist (created automatically by the bridge if missing):
  - `tasks/from_expert/`
  - `tasks/to_expert/`
  - `logs/`
  - `governance/`

## 3) What was added in this step
- Bridge daemon script: `scripts/start_junie_bridge.py`
  - CLI: `--federation on|off`, `--agent Expert|Archy|Genesis`, `--poll`, `--heartbeat`
  - Logs control-plane events to `logs/control_plane_activity.jsonl` (includes "Bridge Online" and heartbeats)
  - Watches `tasks/from_expert/*.json` for commands
  - On `{type:"ping"}` creates `tasks/to_expert/Archy_Response_<UTC-ISO-safe>.json`
  - Appends exchange entries to `governance/federation_audit.jsonl`
  - Windows-safe timestamps, repo-root path safety via `utils.paths.PROJECT_ROOT`

## 4) Activation Steps (Windows PowerShell)
1) Confirm manifest contents
```powershell
Get-Content federation\context_manifest.json
```
Expect to see `"AgentFactoryExpert"`, `"Archy"`, `"Genesis"` under `agents`.

2) Start the bridge daemon (keep this session running)
```powershell
python scripts/start_junie_bridge.py --federation on --agent Expert
```
You should see a new entry in `logs/control_plane_activity.jsonl` for `"Bridge Online"`.

3) Send a connectivity ping from Expert → Archy
```powershell
New-Item -Path tasks\from_expert\Test_Federation_Connectivity.json -Value '{"type": "ping", "target": "Archy", "origin": "AgentFactoryExpert"}' -Force
```
Wait ~5–10 seconds.

4) Check for response files
```powershell
dir tasks\to_expert
```
Expect: `Archy_Response_<timestamp>.json`

5) Verify control-plane and governance logs
```powershell
Get-Content logs\control_plane_activity.jsonl | Select-String "Bridge Online"
Get-Content logs\control_plane_activity.jsonl | Select-String "processed"
Get-Content governance\federation_audit.jsonl | Select-String "AgentFactoryExpert"
```

## 5) Expected Artifacts
- Control-plane log entries:
  - `logs/control_plane_activity.jsonl` includes `{"event":"Bridge Online", ...}` and later `{"event":"processed", ...}`
- Governance audit record:
  - `governance/federation_audit.jsonl` contains an entry documenting the `ping` exchange
- Response file content (example):
```json
{
  "ok": true,
  "reply": "pong",
  "origin": "AgentFactoryExpert",
  "target": "Archy",
  "ts": "2025-10-28T14:26:00Z",
  "meta": {
    "source": "junie_bridge",
    "request_file": "tasks/from_expert/Test_Federation_Connectivity.json"
  }
}
```

## 6) Acceptance Criteria
- ✅ `"Bridge Online"` entry present in `logs/control_plane_activity.jsonl`
- ✅ `ping` → `Archy_Response_*.json` present under `tasks/to_expert/`
- ✅ Exchange appended to `governance/federation_audit.jsonl`
- ✅ No errors or silent failures (errors, if any, appear as JSON envelopes in the control-plane log and the loop continues)

## 7) Troubleshooting
- No response appears:
  - Ensure the daemon process is running and watching `tasks/from_expert`
  - Validate ping JSON is well-formed and saved with `.json` extension
  - Inspect `logs/control_plane_activity.jsonl` for `invalid_json` or other error envelopes
- Manifest/agents not detected:
  - Re-check `federation/context_manifest.json` formatting; restart the daemon
- Multiple pings:
  - The bridge processes each file once using `(filename, mtime)` to avoid duplicates

## 8) Rollback
- Stop the daemon (if it’s the only Python process):
```powershell
Stop-Process -Name "python" -Force
```
- Remove the bridge script:
```powershell
Remove-Item scripts\start_junie_bridge.py
```
- Optional: clean test artifacts
```powershell
Remove-Item tasks\from_expert\Test_Federation_Connectivity.json -Force
Remove-Item tasks\to_expert\Archy_Response_*.json -Force
```

## 9) Security & Governance
- No secrets introduced; append-only JSONL logs
- All paths resolved relative to repo root; Windows-safe filenames
- Federation events recorded in both control-plane and governance audit logs

---

### Machine-Readable Envelope
```json
{
  "id": "Federation-Activation-2025-10-28",
  "title": "Federation Activation & Live Command Flow — Verification",
  "ts": "2025-10-28T14:26:00Z",
  "preconditions": {
    "manifest": "federation/context_manifest.json",
    "agents": ["AgentFactoryExpert", "Archy", "Genesis"]
  },
  "commands": {
    "start": "python scripts/start_junie_bridge.py --federation on --agent Expert",
    "ping": "New-Item -Path tasks\\from_expert\\Test_Federation_Connectivity.json -Value '{\"type\": \"ping\", \"target\": \"Archy\", \"origin\": \"AgentFactoryExpert\"}' -Force",
    "logs_online": "Get-Content logs\\control_plane_activity.jsonl | Select-String \"Bridge Online\""
  },
  "evidence_paths": [
    "logs/control_plane_activity.jsonl",
    "governance/federation_audit.jsonl",
    "tasks/to_expert/Archy_Response_<timestamp>.json"
  ],
  "acceptance": {
    "bridge_online": true,
    "ping_response": true,
    "audit_logged": true
  }
}
```
