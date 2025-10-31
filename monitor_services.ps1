$logPath = "C:\Users\benny\IdeaProjects\agent-factory\logs\service_monitor.log"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$services = @("AgentFactoryAPI", "Cloudflared")

foreach ($service in $services) {
    $svc = Get-Service -Name $service -ErrorAction SilentlyContinue
    if ($null -eq $svc) {
        "$date $service not found." | Out-File -FilePath $logPath -Append
        continue
    }
    if ($svc.Status -ne 'Running') {
        "$date $service is $($svc.Status). Restarting..." | Out-File -FilePath $logPath -Append
        Start-Service -Name $service
        "$date Restarted $service." | Out-File -FilePath $logPath -Append
    } else {
        "$date $service is running." | Out-File -FilePath $logPath -Append
    }
}

