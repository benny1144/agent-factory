# Configure NSSM service for AgentFactoryAPI
# Run this script from an elevated PowerShell (Run as Administrator)

$ErrorActionPreference = 'Stop'

# Ensure log directory exists
$logDir = "C:\Users\benny\IdeaProjects\agent-factory\logs"
if (-not (Test-Path $logDir)) {
  New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

$nssm = "C:\Users\benny\Downloads\Disagreement.AI\ageny-factory\nssm.exe"

# Core configuration
& $nssm set AgentFactoryAPI Application "C:\Users\benny\IdeaProjects\agent-factory\.venv\Scripts\python.exe"
& $nssm set AgentFactoryAPI AppParameters "-m uvicorn agent_factory.server.fastapi_server:app --host 127.0.0.1 --port 8000"
& $nssm set AgentFactoryAPI AppDirectory "C:\Users\benny\IdeaProjects\agent-factory"
& $nssm set AgentFactoryAPI AppEnvironmentExtra "PYTHONPATH=C:\Users\benny\IdeaProjects\agent-factory\src"

# Startup mode: delayed auto start
& $nssm set AgentFactoryAPI Start SERVICE_DELAYED_AUTO_START

# Logs
& $nssm set AgentFactoryAPI AppStdout "C:\Users\benny\IdeaProjects\agent-factory\logs\AgentFactoryAPI.log"
& $nssm set AgentFactoryAPI AppStderr "C:\Users\benny\IdeaProjects\agent-factory\logs\AgentFactoryAPI.log"

Write-Host "NSSM configuration for AgentFactoryAPI applied." -ForegroundColor Green
