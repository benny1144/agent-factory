$LocalHealth = "http://127.0.0.1:5050/health"
$RemoteHealth = "https://gpt.disagreements.ai/health"
$CloudflaredService = "Cloudflared"
$BridgeScript = "C:\Users\benny\IdeaProjects\agent-factory\scripts\start_junie_bridge.py"
$PythonExe = "python"

function Log($msg) {
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $logPath = "C:\Users\benny\IdeaProjects\agent-factory\logs\watchdog.log"
    $logDir = Split-Path $logPath -Parent
    if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }
    Add-Content $logPath "$timestamp  $msg"
}

function Test-Health($url) {
    try {
        $r = Invoke-RestMethod -Uri $url -TimeoutSec 5 -ErrorAction Stop
        if (($r.status -eq "ok") -or ($r.ok -eq $true)) { return $true } else { return $false }
    } catch { return $false }
}

while ($true) {
    $localOK = Test-Health $LocalHealth
    $remoteOK = Test-Health $RemoteHealth

    if (-not $localOK) {
        Log "Local bridge unhealthy — restarting..."
        Stop-Process -Name python -ErrorAction SilentlyContinue
        Start-Process $PythonExe $BridgeScript
        Start-Sleep -Seconds 10
    }

    if (-not $remoteOK) {
        Log "Remote tunnel unhealthy — restarting Cloudflared..."
        net stop $CloudflaredService | Out-Null
        Start-Sleep -Seconds 5
        net start $CloudflaredService | Out-Null
    }

    Start-Sleep -Seconds 60
}