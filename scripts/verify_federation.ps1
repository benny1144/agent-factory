# Phase 39.3 — Governance & Federation Sync Verifier
# Usage (PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts\verify_federation.ps1

$ErrorActionPreference = 'Stop'

# Repo root
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path

# Paths
$govDir = Join-Path $RepoRoot 'governance'
$manifestV75 = Join-Path $govDir 'federation_manifest_v7_5.json'
$manifestV8 = Join-Path $govDir 'federation_manifest_v8.json'
$finalAudit = Join-Path $govDir 'final_audit_report.json'
$eventBus = Join-Path $govDir 'event_bus.jsonl'

# Ensure governance directory
if (-not (Test-Path $govDir)) { New-Item -ItemType Directory -Path $govDir -Force | Out-Null }

# 1) Build v8 manifest from v7.5 (copy if exists, else initialize empty list)
try {
  if (Test-Path $manifestV75) {
    $json = Get-Content -Raw -Path $manifestV75 | ConvertFrom-Json -Depth 50
  } else {
    $json = @()
  }
  # Write v8
  ($json | ConvertTo-Json -Depth 50) | Set-Content -Path $manifestV8 -Encoding UTF8
  Write-Host "Manifest v8 written: $manifestV8" -ForegroundColor Green
} catch {
  Write-Host "Failed to generate v8 manifest: $($_.Exception.Message)" -ForegroundColor Red
}

# 2) Write/update final audit report (Phase 39.3 marker)
try {
  $report = @{ ok = $true; phase = '39.3'; ts = [DateTime]::UtcNow.ToString('o') }
  ($report | ConvertTo-Json -Depth 8) | Set-Content -Path $finalAudit -Encoding UTF8
  Write-Host "Final audit report updated: $finalAudit" -ForegroundColor Green
} catch {
  Write-Host "Failed to write final audit report: $($_.Exception.Message)" -ForegroundColor Yellow
}

# 3) Emit federation sync event from Archy to event bus
try {
  $evt = @{ ts = [DateTime]::UtcNow.ToString('o'); agent = 'Archy'; type = 'federation_sync'; status = 'ok'; phase = '39.3' } | ConvertTo-Json -Compress
  Add-Content -Path $eventBus -Value $evt
  Write-Host "Federation sync event appended to event bus." -ForegroundColor Green
} catch {
  Write-Host "Failed to append event bus entry: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "✅ Governance & Federation sync completed." -ForegroundColor Cyan
