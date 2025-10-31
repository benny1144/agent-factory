# Start Agent Factory FastAPI backend via uvicorn
# Usage:
#   powershell -ExecutionPolicy Bypass -File \
#     "C:\Users\benny\IdeaProjects\agent-factory\scripts\start_backend_api.ps1"
# Optional: pass -NoReload to disable auto-reload

param(
    [switch]$NoReload
)

$ErrorActionPreference = "Stop"

# Resolve repo root from this script's directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $RepoRoot

# Ensure PYTHONPATH includes ./src so `agent_factory` is importable
$env:PYTHONPATH = (Resolve-Path ".\src").Path

$HostAddr = "127.0.0.1"
$Port = 8000
$App = "agent_factory.server.fastapi_server:app"

# Build uvicorn args
$Args = @("-m", "uvicorn", $App, "--host", $HostAddr, "--port", $Port)
if (-not $NoReload) { $Args += "--reload" }

Write-Host "[Agent Factory] Starting FastAPI backend at http://$HostAddr:$Port (App: $App)" -ForegroundColor Cyan
Write-Host "PYTHONPATH=$($env:PYTHONPATH)" -ForegroundColor DarkGray

# Launch in the current console so logs are visible
python @Args