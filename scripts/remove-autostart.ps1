# Removes the Windows Scheduled Tasks created for Junie auto-start
# Usage:
#   Run PowerShell as Administrator, then:
#     ./scripts/remove-autostart.ps1

$ErrorActionPreference = 'Stop'

# Optional: check admin
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
  Write-Warning 'Please run PowerShell as Administrator to remove Scheduled Tasks created with highest privileges.'
  exit 1
}

Write-Host 'Deleting Scheduled Task: Junie Tunnel' -ForegroundColor Cyan
schtasks /Delete /TN "Junie Tunnel" /F | Out-Host

Write-Host 'Deleting Scheduled Task: Junie Bridge' -ForegroundColor Cyan
schtasks /Delete /TN "Junie Bridge" /F | Out-Host

Write-Host 'Done. Tasks removed.' -ForegroundColor Green
