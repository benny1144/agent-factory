# Triggers the scheduled tasks to start immediately (useful after running setup)
# Usage:
#   ./scripts/run-autostart-now.ps1

$ErrorActionPreference = 'Stop'

Write-Host 'Starting Scheduled Task: Junie Bridge' -ForegroundColor Cyan
schtasks /Run /TN "Junie Bridge" | Out-Host

Start-Sleep -Seconds 2

Write-Host 'Starting Scheduled Task: Junie Tunnel' -ForegroundColor Cyan
schtasks /Run /TN "Junie Tunnel" | Out-Host

Write-Host 'Done triggering tasks.' -ForegroundColor Green
