# ======================================================================
#  Cloudflared Tunnel Auto-Service Setup Script
#  Author: ChatGPT / Benny Setup Automation
#  Purpose: Verify, configure, and start a persistent Cloudflare Tunnel
# ======================================================================

$tunnelName = "GPT-IDE"
$configPath = "C:\Users\benny\IdeaProjects\agent-factory\.cloudflared\config.yml"
$cloudflaredExe = "C:\Program Files (x86)\cloudflared\cloudflared.exe"

Write-Host "=== Cloudflared Tunnel Service Setup ===" -ForegroundColor Cyan

# 1️⃣ Verify cloudflared exists
if (-Not (Test-Path $cloudflaredExe)) {
    Write-Host "❌ Cloudflared not found at $cloudflaredExe" -ForegroundColor Red
    Write-Host "Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/ and try again."
    exit 1
} else {
    Write-Host "✅ Cloudflared found."
}

# 2️⃣ Check for tunnel config
if (-Not (Test-Path $configPath)) {
    Write-Host "❌ Missing config.yml at $configPath" -ForegroundColor Red
    Write-Host "Please create it before running this script."
    exit 1
} else {
    Write-Host "✅ Found config.yml"
}

# 3️⃣ Extract tunnel ID
$tunnelId = (Select-String -Path $configPath -Pattern "^tunnel:\s*(.*)" | ForEach-Object { $_.Matches.Groups[1].Value.Trim() })
if (-Not $tunnelId) {
    Write-Host "❌ Could not read tunnel ID from config.yml" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Tunnel ID: $tunnelId"

# 4️⃣ Verify credentials file
$credFile = "$env:USERPROFILE\.cloudflared\$tunnelId.json"
if (-Not (Test-Path $credFile)) {
    Write-Host "⚠️  Missing credentials file, regenerating..."
    & $cloudflaredExe tunnel token $tunnelId
    if (-Not (Test-Path $credFile)) {
        Write-Host "❌ Failed to generate credentials file." -ForegroundColor Red
        exit 1
    }
}
Write-Host "✅ Credentials file OK"

# 5️⃣ Create Windows service (idempotent)
$cmd = "`"$cloudflaredExe`" --config `"$configPath`" tunnel run $tunnelName"

Write-Host "🔧 Registering Windows service..."
$existing = Get-Service -Name "Cloudflared" -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "⚙️  Updating existing Cloudflared service..."
    sc.exe delete Cloudflared | Out-Null
    Start-Sleep -Seconds 2
}

sc.exe create Cloudflared binPath= "$cmd" start= auto | Out-Null
Set-Service -Name Cloudflared -StartupType AutomaticDelayedStart

Write-Host "✅ Service registered successfully."

# 6️⃣ Start service
Write-Host "🚀 Starting Cloudflared service..."
try {
    net start Cloudflared | Out-Null
    Write-Host "✅ Cloudflared service started successfully." -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to start Cloudflared service. Check Event Viewer or nssm logs." -ForegroundColor Red
}

# 7️⃣ Health check
Start-Sleep -Seconds 5
try {
    $resp = Invoke-WebRequest -Uri "https://gpt-ide.disagreements.ai/health" -UseBasicParsing -TimeoutSec 10
    if ($resp.StatusCode -eq 200) {
        Write-Host "🌐 Health check OK — Cloudflare Tunnel is live!" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Health endpoint returned status $($resp.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️ Unable to reach https://gpt-ide.disagreements.ai/health yet." -ForegroundColor Yellow
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
