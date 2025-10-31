$logPath = "C:\Users\benny\IdeaProjects\agent-factory\logs\cloudflared_watchdog.log"
$date = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

try {
    $status = Get-Service -Name "Cloudflared" -ErrorAction SilentlyContinue
    if ($null -eq $status) {
        "$date Cloudflared service not found." | Out-File -FilePath $logPath -Append
        exit
    }

    $output = & sc queryex Cloudflared
    $tunnelErrors = Get-Content "C:\Windows\System32\config\systemprofile\.cloudflared\cloudflared.log" -ErrorAction SilentlyContinue -Tail 40 |
        Select-String "1033|reconnecting|error" -SimpleMatch

    if ($tunnelErrors) {
        "$date Cloudflared showing reconnect errors, restarting..." | Out-File -FilePath $logPath -Append
        Restart-Service -Name "Cloudflared" -Force
        "$date Restarted Cloudflared." | Out-File -FilePath $logPath -Append
    }
    elseif ($status.Status -ne "Running") {
        "$date Cloudflared is $($status.Status). Restarting..." | Out-File -FilePath $logPath -Append
        Start-Service -Name "Cloudflared"
        "$date Restarted Cloudflared." | Out-File -FilePath $logPath -Append
    }
    else {
        "$date Cloudflared running normally." | Out-File -FilePath $logPath -Append
    }
}
catch {
    "$date Error checking Cloudflared: $_" | Out-File -FilePath $logPath -Append
}
