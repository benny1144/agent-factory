# Register Windows Scheduled Task to monitor AgentFactoryAPI and Cloudflared services
# Run from an elevated PowerShell (Run as Administrator)

$ErrorActionPreference = 'Stop'

$monitorScript = 'C:\Users\benny\IdeaProjects\agent-factory\monitor_services.ps1'
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File '$monitorScript'"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "AgentFactoryMonitor" -Description "Monitors and restarts API and Cloudflared if down" -User "SYSTEM" -RunLevel Highest -Force

Write-Host "Scheduled Task 'AgentFactoryMonitor' registered." -ForegroundColor Green
