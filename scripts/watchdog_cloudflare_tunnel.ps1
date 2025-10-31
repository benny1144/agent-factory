<#
.SYNOPSIS
  Cloudflare Tunnel Watchdog for Junie Bridge.
  Ensures the tunnel and local service stay online.
.DESCRIPTION
  - Pings local Junie Bridge (via .env PORT or default 8765)
  - Verifies cloudflared tunnel process is running
  - Restarts tunnel if down
  - Logs all actions to logs\tunnel_watchdog.log
  - Optional: register a Scheduled Task to run every 2 minutes (-InstallTask)
#>

param(
  [switch]$InstallTask,
  [string]$TunnelName = "juniebridge",
  [string]$EnvFile = "C:\\Users\\benny\\IdeaProjects\\agent-factory\\junie-bridge\\.env",
  [string]$ProjectRoot = "C:\\Users\\benny\\IdeaProjects\\agent-factory",
  [string]$CloudflaredExe = "C:\\Program Files (x86)\\cloudflared\\cloudflared.exe"
)

$ErrorActionPreference = 'SilentlyContinue'

$logDir  = Join-Path $ProjectRoot "logs"
$logFile = Join-Path $logDir "tunnel_watchdog.log"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Log {
  param([string]$msg)
  $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  "$timestamp  $msg" | Out-File -Append -FilePath $logFile -Encoding utf8
}

# --- Read .env for PORT ---
$port = 8765
if (Test-Path $EnvFile) {
  $envLines = Get-Content $EnvFile | Where-Object { $_ -match "=" -and $_ -notmatch "^#" }
  foreach ($line in $envLines) {
    $key,$value = $line -split "=",2
    if ($key -eq "PORT") { $port = $value.Trim() }
  }
}
$localUrl = "http://localhost:$port"

# --- Health check local service ---
$serviceHealthy = $false
try {
  $resp = Invoke-WebRequest -Uri $localUrl -UseBasicParsing -TimeoutSec 3
  if ($resp.StatusCode -eq 200) { $serviceHealthy = $true }
} catch { $serviceHealthy = $false }

if (-not $serviceHealthy) {
  Log "⚠️  Junie Bridge not responding at $localUrl"
}

# --- Check tunnel process ---
$tunnelRunning = $false
try {
  $procs = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
  if ($procs) {
    foreach ($p in $procs) {
      if ($p.Path -eq $CloudflaredExe) { $tunnelRunning = $true }
    }
  }
} catch { $tunnelRunning = $false }

if (-not $tunnelRunning) {
  Log "🔁 Tunnel not detected; restarting..."
  try {
    Start-Process -FilePath $CloudflaredExe -ArgumentList "tunnel run $TunnelName" -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 5
    Log "✅ Tunnel restarted."
  } catch {
    Log "❌ Failed to restart tunnel: $($_.Exception.Message)"
  }
} else {
  Log "✅ Tunnel healthy and active."
}

# --- Install Scheduled Task (every 2 minutes) ---
if ($InstallTask) {
  try {
    $taskName = "CloudflareTunnel-HealthWatchdog"
    $action   = New-ScheduledTaskAction -Execute "pwsh.exe" -Argument "-NoLogo -NoProfile -File `"$($MyInvocation.MyCommand.Path)`""
    $trigger  = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 2) -RepetitionDuration ([TimeSpan]::MaxValue)
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description "Cloudflare Tunnel watchdog (Junie Bridge)" -RunLevel Highest -Force | Out-Null
    Log "🕐 Scheduled Task installed: $taskName (every 2 minutes)"
    Write-Host "Scheduled Task installed: $taskName"
  } catch {
    Log "❌ Failed to install Scheduled Task: $($_.Exception.Message)"
    Write-Host "Failed to install Scheduled Task: $($_.Exception.Message)"
  }
}
