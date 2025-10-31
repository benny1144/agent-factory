# Reinitialize and Validate GPT IDE Bridge Connection
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\gpt_ide_bridge_validate.ps1
# Optional: pass -NoReset to skip `gpt-ide --reset`

param(
    [switch]$NoReset
)

$ErrorActionPreference = 'Continue'

# Resolve repo root from this script's directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..')).Path
Set-Location $RepoRoot

# Folders/files
$LogsDir = Join-Path $RepoRoot 'logs'
$Jsonl = Join-Path $LogsDir 'gpt_ide_bridge_validation.jsonl'
$statusOut = Join-Path $RepoRoot 'tasks\tasks_complete\GPT_IDE_Bridge_Validation.status.json'

# Ensure directories
if (-not (Test-Path $LogsDir)) { New-Item -ItemType Directory -Path $LogsDir -Force | Out-Null }
$tasksCompleteDir = Split-Path $statusOut -Parent
if (-not (Test-Path $tasksCompleteDir)) { New-Item -ItemType Directory -Path $tasksCompleteDir -Force | Out-Null }

# Helpers
function New-Envelope {
    param([bool]$ok, [hashtable]$data, [string]$error, [hashtable]$meta)
    if (-not $meta) { $meta = @{} }
    $meta['ts'] = [DateTime]::UtcNow.ToString('o')
    $meta['source'] = 'scripts/gpt_ide_bridge_validate.ps1'
    return @{ ok = $ok; data = $data; error = $error; meta = $meta }
}

function Write-Jsonl {
    param([hashtable]$obj)
    $line = ($obj | ConvertTo-Json -Depth 8 -Compress)
    Add-Content -Path $Jsonl -Value $line
}

# Timer start
$sw = [System.Diagnostics.Stopwatch]::StartNew()

# 1) Reinitialize local service via CLI (best-effort)
$cliFound = $false
try {
    $cmd = Get-Command 'gpt-ide' -ErrorAction SilentlyContinue
    if ($cmd) { $cliFound = $true }
} catch { $cliFound = $false }

$resetOk = $null
$statusText = ''
if ($cliFound) {
    if (-not $NoReset) {
        try {
            $resetOut = & gpt-ide --reset 2>&1
            $resetOk = $true
        } catch {
            $resetOk = $false
        }
    }
    try {
        $statusOutCmd = & gpt-ide --status 2>&1
        $statusText = [string]$statusOutCmd
    } catch {
        $statusText = 'status_failed'
    }
}

# 2) Validate local config file
$HomeDir = $env:USERPROFILE
$configPath = Join-Path $HomeDir '.config\gpt-ide\config.json'
$configExists = Test-Path $configPath
$endpointExpected = 'https://gpt-ide.disagreements.ai'
$configOk = $false
$configData = @{}
if ($configExists) {
    try {
        $cfgJson = Get-Content -Raw -Path $configPath | ConvertFrom-Json -Depth 8
        $endpoint = [string]$cfgJson.endpoint
        $authToken = [string]$cfgJson.auth_token
        $projectRoot = [string]$cfgJson.project_root
        $hasToken = -not [string]::IsNullOrWhiteSpace($authToken)
        $tokenLen = if ($authToken) { $authToken.Length } else { 0 }
        $projMatches = ($projectRoot -replace '/', '\\') -eq ($RepoRoot -replace '/', '\\')
        $endpointMatches = ($endpoint -eq $endpointExpected)
        $configOk = $endpointMatches -and $hasToken -and $projMatches
        $configData = @{
            endpoint = $endpoint
            endpoint_expected = $endpointExpected
            endpoint_matches = $endpointMatches
            has_auth_token = $hasToken
            auth_token_len = $tokenLen
            project_root = $projectRoot
            repo_root = $RepoRoot
            project_root_matches = $projMatches
        }
    } catch {
        $configOk = $false
        $configData = @{ error = "Invalid JSON or read error: $($_.Exception.Message)" }
    }
} else {
    $configData = @{ error = 'Config file not found'; path = $configPath }
}

# 3) Validate remote API health
$healthUrl = 'https://gpt-ide.disagreements.ai/api/health'
$healthOk = $false
$healthPayload = @{}
try {
    $resp = Invoke-RestMethod -Method GET -Uri $healthUrl -TimeoutSec 10 -ErrorAction Stop
    # Expect {"ok": true, "ide": {...}}
    $okField = $false
    if ($resp -is [System.Collections.IDictionary]) { $okField = [bool]$resp['ok'] }
    elseif ($resp.PSObject.Properties.Name -contains 'ok') { $okField = [bool]$resp.ok }
    $healthOk = $okField
    $ideInfo = $null
    if ($resp.PSObject.Properties.Name -contains 'ide') { $ideInfo = $resp.ide }
    $healthPayload = @{ ok = $healthOk; ide = $ideInfo }
} catch {
    $healthOk = $false
    $healthPayload = @{ ok = $false; error = $_.Exception.Message }
}

# Aggregate
$sw.Stop()
$durationMs = [int]$sw.Elapsed.TotalMilliseconds

$overallOk = ($cliFound) -and ($configOk) -and ($healthOk)

$data = @{
    repo_root = $RepoRoot
    cli_found = $cliFound
    reset_ran = (-not $NoReset) -and $cliFound
    reset_ok = $resetOk
    status_text = $statusText
    config = $configData
    health = $healthPayload
}

$envObj = New-Envelope -ok:$overallOk -data:$data -error:$(if ($overallOk) { $null } else { 'Validation failed. See data for details.' }) -meta:@{ duration_ms = $durationMs }
Write-Jsonl -obj $envObj

# Write status json for quick review
try {
    $statusDoc = @{
        task = 'GPT_IDE_Bridge_Validation'
        ok = $overallOk
        ts = [DateTime]::UtcNow.ToString('o')
        health_ok = $healthOk
        config_ok = $configOk
        cli_found = $cliFound
        notes = @{
            run_command = 'powershell -ExecutionPolicy Bypass -File scripts\gpt_ide_bridge_validate.ps1'
            rollback = 'gpt-ide --uninstall; gpt-ide --install'
        }
    } | ConvertTo-Json -Depth 8
    $statusDoc | Set-Content -Path $statusOut -Encoding UTF8
} catch { }

# Console summary
Write-Host "=== GPT IDE Bridge Validation ===" -ForegroundColor Cyan
Write-Host ("Repo Root: {0}" -f $RepoRoot)
Write-Host ("CLI Found: {0}" -f $cliFound)
if ($cliFound) {
    if ($resetOk -ne $null) { Write-Host ("Reset OK: {0}" -f $resetOk) }
    if ($statusText) { Write-Host "gpt-ide --status:"; Write-Host $statusText -ForegroundColor DarkGray }
} else {
    Write-Host "gpt-ide CLI not found in PATH. Please install or open an IDE terminal with plugin tooling available." -ForegroundColor Yellow
}
Write-Host ("Config OK: {0}" -f $configOk)
if (-not $configOk) {
    Write-Host ("Config details: " + ($configData | ConvertTo-Json -Compress)) -ForegroundColor Yellow
}
Write-Host ("Health OK: {0} ({1})" -f $healthOk, $healthUrl)
Write-Host ("Overall: {0}" -f $(if ($overallOk) { 'PASS' } else { 'FAIL' })) -ForegroundColor $(if ($overallOk) { 'Green' } else { 'Red' })

if (-not $overallOk) {
    Write-Host "Rollback guidance:" -ForegroundColor Yellow
    Write-Host "  gpt-ide --uninstall" -ForegroundColor Yellow
    Write-Host "  gpt-ide --install" -ForegroundColor Yellow
}

exit ($(if ($overallOk) { 0 } else { 1 }))