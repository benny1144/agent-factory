param (
    [string]$TargetAgent = "Archy"
)

Write-Host ">>> Running Federation Verification Script..." -ForegroundColor Cyan

# --- Manifest check ---
$manifestPath = "federation\context_manifest.json"
if (!(Test-Path $manifestPath)) {
    Write-Host "ERROR: Missing federation manifest at $manifestPath" -ForegroundColor Red
    exit 1
}
$manifest = Get-Content $manifestPath | ConvertFrom-Json
if ($manifest.agents -notcontains "AgentFactoryExpert" -or
        $manifest.agents -notcontains $TargetAgent -or
        $manifest.agents -notcontains "Genesis") {
    Write-Host "ERROR: Incomplete federation manifest." -ForegroundColor Red
    exit 1
}
Write-Host "OK: Federation manifest valid." -ForegroundColor Green

# --- Bridge process check ---
$bridgeRunning = Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match "start_junie_bridge" }

if (!$bridgeRunning) {
    Write-Host "ERROR: Bridge daemon not active. Start it first." -ForegroundColor Red
    exit 1
}
Write-Host "OK: Bridge process running." -ForegroundColor Green

# --- Send test ping ---
$pingFile = "tasks\from_expert\Test_Federation_Connectivity.json"
$pingData = @{
    type      = "ping"
    target    = $TargetAgent
    origin    = "AgentFactoryExpert"
    timestamp = (Get-Date).ToString("o")
} | ConvertTo-Json -Compress
Set-Content -Path $pingFile -Value $pingData
Write-Host "Sent test ping to $TargetAgent." -ForegroundColor Cyan

# --- Wait for response ---
$responseFound = $false
for ($i = 0; $i -lt 15; $i++) {
    $responses = Get-ChildItem -Path "tasks\to_expert" -Filter "${TargetAgent}_Response_*.json" -ErrorAction SilentlyContinue
    if ($responses) {
        Write-Host "Response received: $($responses[-1].Name)" -ForegroundColor Green
        $responseFound = $true
        break
    }
    Start-Sleep -Seconds 1
}
if (-not $responseFound) {
    Write-Host "No response detected within timeout." -ForegroundColor Red
    exit 1
}

# --- Log tail ---
if (Test-Path "logs\control_plane_activity.jsonl") {
    Write-Host "Recent log entries:" -ForegroundColor Cyan
    Get-Content "logs\control_plane_activity.jsonl" -Tail 3
}

Write-Host "Federation verification successful." -ForegroundColor Green
exit 0
