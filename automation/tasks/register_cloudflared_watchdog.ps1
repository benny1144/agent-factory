# Registers a Windows Scheduled Task to run the Cloudflared watchdog every 5 minutes as SYSTEM
# Usage (Admin PowerShell):
#   powershell -ExecutionPolicy Bypass -File automation\tasks\register_cloudflared_watchdog.ps1

$TaskName = "CloudflaredWatchdog"
$ScriptPath = "C:\Users\benny\IdeaProjects\agent-factory\monitor_cloudflared.ps1"

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File '$ScriptPath'"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration ([TimeSpan]::MaxValue)

Register-ScheduledTask -Action $action -Trigger $trigger -TaskName $TaskName -Description "Monitors and restarts Cloudflared if reconnect errors appear" -User "SYSTEM" -RunLevel Highest -Force
