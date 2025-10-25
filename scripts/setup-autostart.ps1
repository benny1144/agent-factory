# Creates Windows Scheduled Tasks to auto-start Junie Bridge and the Cloudflared tunnel at user logon.
# - Runs with highest privileges (needed for HTTPS 443 binding)
# - Idempotent: uses /F to overwrite tasks if they already exist
# Usage:
#   Run PowerShell as Administrator, then:
#     ./scripts/setup-autostart.ps1            # create tasks
#     ./scripts/setup-autostart.ps1 --run-now  # create and immediately run tasks

param(
  [switch]$RunNow
)

$ErrorActionPreference = 'Stop'

# Require Administrator
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Warning 'Please run PowerShell as Administrator to register Scheduled Tasks with highest privileges.'
  exit 1
}

# Resolve repo root and scripts
$repoRoot    = Split-Path -Parent $PSScriptRoot
$bridgeTask  = Join-Path $repoRoot 'start-bridge-task.ps1'
$tunnelTask  = Join-Path $repoRoot 'start-tunnel.ps1'

if (-not (Test-Path $bridgeTask)) { throw "Missing script: $bridgeTask" }
if (-not (Test-Path $tunnelTask)) { throw "Missing script: $tunnelTask" }

# Build commands (quoted)
$bridgeCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$bridgeTask`""
$tunnelCmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$tunnelTask`""

# Create or update tasks
Write-Host 'Registering Scheduled Task: Junie Bridge' -ForegroundColor Cyan
schtasks /Create /TN "Junie Bridge" /TR "$bridgeCmd" /SC ONLOGON /RL HIGHEST /F | Out-Host

Write-Host 'Registering Scheduled Task: Junie Tunnel' -ForegroundColor Cyan
schtasks /Create /TN "Junie Tunnel" /TR "$tunnelCmd" /SC ONLOGON /RL HIGHEST /F | Out-Host

Write-Host "Done. Tasks 'Junie Bridge' and 'Junie Tunnel' are set to run at logon with highest privileges." -ForegroundColor Green

if ($RunNow) {
  Write-Host 'Starting tasks now...' -ForegroundColor Yellow
  schtasks /Run /TN "Junie Bridge" | Out-Host
  Start-Sleep -Seconds 2
  schtasks /Run /TN "Junie Tunnel" | Out-Host
  Write-Host 'Tasks triggered.' -ForegroundColor Green
}
