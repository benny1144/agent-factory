# --- keepalive.ps1 ---
# Agent Factory Self-Healing Monitor (fixed version)
# Monitors Cloudflared service, Junie Bridge, and external /health
# Author: Benny + GPT-5

$tunnelName   = "Cloudflared"
$bridgeScript = "C:\Users\benny\IdeaProjects\agent-factory\scripts\start_junie_bridge.py"
$python       = "C:\Users\benny\AppData\Local\Programs\Python\Python313\python.exe"
$logFile      = "C:\Users\benny\IdeaProjects\agent-factory\logs\keepalive.log"
$alertLimit   = 3
$windowMins   = 5
$healthURL    = "https://gpt.disagreements.ai/health"

# Optional email configuration (fill in to enable)
$emailTo     = ""
$emailFrom   = ""
$smtpServer  = ""
$smtpPort    = 587
$smtpUser    = ""
$smtpPass    = ""

$restartHistory = @{}

function Write-Log($msg) {
    $stamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    "$stamp  $msg" | Out-File -Append -FilePath $logFile
}

function Send-Toast($title, $message) {
    try {
        $null = New-BurntToastNotification -Text $title, $message
    } catch {
        Write-Log "Toast notification failed: $_"
    }
}

function Send-EmailAlert($subject, $body) {
    if (-not $emailTo -or -not $smtpServer) { return }
    try {
        Send-MailMessage -To $emailTo -From $emailFrom -Subject $subject -Body $body `
            -SmtpServer $smtpServer -Port $smtpPort -UseSsl `
            -Credential (New-Object System.Management.Automation.PSCredential($smtpUser,(ConvertTo-SecureString $smtpPass -AsPlainText -Force)))
        Write-Log "Email alert sent to $emailTo"
    } catch {
        Write-Log "Email alert failed: $_"
    }
}

function Record-Restart($serviceName) {
    $now = Get-Date
    if (-not $restartHistory.ContainsKey($serviceName)) {
        $restartHistory[$serviceName] = @()
    }
    # Append and purge older entries
    $restartHistory[$serviceName] += ,$now
    $restartHistory[$serviceName] = $restartHistory[$serviceName] | Where-Object { $_ -gt ($now.AddMinutes(-$windowMins)) }

    if ($restartHistory[$serviceName].Count -ge $alertLimit) {
        $msg = "$serviceName restarted $($restartHistory[$serviceName].Count)x within $windowMins minutes!"
        Send-Toast "⚠️ $serviceName Unstable" $msg
        Send-EmailAlert "$serviceName unstable" $msg
        Write-Log $msg
    }
}

function Check-Health {
    try {
        $resp = Invoke-WebRequest -Uri $healthURL -UseBasicParsing -TimeoutSec 10
        if ($resp.StatusCode -eq 200 -and $resp.Content -match '"status"\s*:\s*"ok"') {
            return $true
        }
        Write-Log "Healthcheck returned non-OK status: $($resp.StatusCode)"
        return $false
    } catch {
        Write-Log "Healthcheck failed: $_"
        return $false
    }
}

Write-Log "---- Keepalive started ----"

while ($true) {
    try {
        # 1️⃣ Check Cloudflared service
        $cloud = Get-Service -Name $tunnelName -ErrorAction SilentlyContinue
        if ($null -eq $cloud -or $cloud.Status -ne 'Running') {
            Write-Log "Cloudflared not running, restarting..."
            try {
                net start $tunnelName | Out-Null
                Record-Restart $tunnelName
            } catch {
                Write-Log "Failed to start Cloudflared: $_"
            }
        }

        # 2️⃣ Check Junie Bridge by port 5050 instead of process name
        $bridgeListening = (Get-NetTCPConnection -LocalPort 5050 -ErrorAction SilentlyContinue)
        if (-not $bridgeListening) {
            Write-Log "Junie Bridge not detected on port 5050, restarting..."
            Start-Process $python -ArgumentList "`"$bridgeScript`" --federation on --agent Expert" `
                -WindowStyle Hidden -WorkingDirectory (Split-Path $bridgeScript)
            Record-Restart "JunieBridge"
        }

        # 3️⃣ Check /health endpoint
        if (-not (Check-Health)) {
            Write-Log "Healthcheck failed; restarting Cloudflared..."
            try {
                net stop $tunnelName /y | Out-Null
                Start-Sleep -Seconds 3
                net start $tunnelName | Out-Null
                Record-Restart "Cloudflared-Health"
            } catch {
                Write-Log "Failed to restart after healthcheck failure: $_"
            }
        }

        Start-Sleep -Seconds 60
    } catch {
        Write-Log "Unexpected loop error: $_"
        Start-Sleep -Seconds 10
    }
}