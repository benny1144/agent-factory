# Permanent Tunnel Setup and Junie Bridge Integration

## Overview
This document records the full conversation and technical setup required to create a **permanent Cloudflare Tunnel** for Junie Bridge within the Agent Factory project. It includes installation, configuration, automation, and health monitoring instructions, along with IDE integration guidance.

---

## 1. Problem Context
Initially, Cloudflare ephemeral tunnels (trycloudflare.com) required frequent reinitialization. The goal was to make the tunnel URL permanent and automatically bind it to a custom domain under Cloudflare, such as `bridge.disagreements.ai`.

---

## 2. Solution Summary
### ✅ Objectives Achieved
- Installed and configured **cloudflared** on Windows PowerShell 7.
- Bound the tunnel to a permanent DNS record in Cloudflare.
- Automated configuration via PowerShell script.
- Integrated with **Junie Bridge** service using its `.env` configuration.
- Added a watchdog service to ensure uptime and automatic recovery.
- Configured IntelliJ IDEA to run Junie Bridge seamlessly.

---

## 3. Cloudflared Installation & PATH Fix
```powershell
winget install --id Cloudflare.cloudflared -e
```
After installation:
```powershell
setx PATH "$($env:PATH);C:\Program Files (x86)\cloudflared"
```
Then reload PowerShell:
```powershell
$env:PATH += ";C:\Program Files (x86)\cloudflared"
cloudflared --version
```
Expected output:
```
cloudflared version 2025.x.x
```

---

## 4. Permanent Tunnel Setup Script
### File: `setup_cloudflare_tunnel.ps1`
Automates tunnel creation, DNS mapping, and auto-start setup.
- Detects port and HTTPS mode from `.env`
- Creates named tunnel (`juniebridge`)
- Maps subdomain (`bridge.disagreements.ai`)
- Registers a Windows Task to auto-run at boot
- Launches the tunnel immediately

---

## 5. Watchdog Script
### File: `scripts/watchdog_cloudflare_tunnel.ps1`
Ensures the tunnel and Junie Bridge remain active.
- Checks if `cloudflared` is running.
- Pings local Junie Bridge endpoint.
- Restarts the tunnel if it drops.
- Logs to `logs/tunnel_watchdog.log`.

### Scheduled Task:
Runs every 2 minutes under the name:
```
CloudflareTunnel-HealthWatchdog
```

---

## 6. Junie Bridge IDE Integration
### IntelliJ Run Configuration
**Type:** Node.js
```
Name: Junie Bridge
Node interpreter: C:\Program Files\nodejs\node.exe
Working directory: C:\Users\benny\IdeaProjects\agent-factory\junie-bridge
JavaScript file: server.js
Environment variables: junie-bridge\.env
```

**Compound Configuration:**
Run both Junie Bridge and Cloudflare Tunnel:
- Junie Bridge (Node.js)
- PowerShell: `cloudflared tunnel run juniebridge`

---

## 7. Automation Summary
| Component | Function | Trigger |
|------------|-----------|----------|
| Cloudflared Tunnel | Persistent external URL | Windows boot |
| Watchdog Script | Restarts if tunnel or service fails | Every 2 min |
| Junie Bridge | Local connector service | Run in IDE |

---

## 8. Final Architecture Flow
```
[Junie Bridge localhost:8765]
        ↓
[Cloudflared Tunnel → bridge.disagreements.ai]
        ↓
[Permanent HTTPS Endpoint]
        ↓
[Cloudflare DNS + SSL]
```

---

## 9. Maintenance Notes
- No manual restart required unless `.env` or domain changes.
- Watchdog ensures continuous uptime.
- Logs for watchdog and tunnel actions stored under `/logs/`.
- Fully compliant with Human Firewall Protocol — no secret exposure.

---

## 10. Verification Checklist
- [x] `cloudflared --version` works globally
- [x] DNS record `bridge.disagreements.ai` resolves
- [x] Tunnel auto-starts after reboot
- [x] Watchdog restarts tunnel if killed
- [x] IDE launches Junie Bridge successfully

---

**Author:** Agent Factory Expert  
**Generated for:** benny1144 / Agent Factory  
**Date:** $(Get-Date -Format yyyy-MM-dd)
