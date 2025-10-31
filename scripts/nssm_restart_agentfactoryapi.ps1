# Restart the AgentFactoryAPI service managed by NSSM
# Run this script from an elevated PowerShell (Run as Administrator)

$ErrorActionPreference = 'Stop'

$nssm = "C:\Users\benny\Downloads\Disagreement.AI\ageny-factory\nssm.exe"

& $nssm stop AgentFactoryAPI
Start-Sleep -Seconds 5
& $nssm start AgentFactoryAPI

Write-Host "AgentFactoryAPI service restarted via NSSM." -ForegroundColor Green
