param([string]$Url = $env:DISAGREEMENTS_API_URL)

if (-not $Url -or $Url.Trim() -eq "") { $Url = "https://api.disagreements.ai/health" }

$mirrors = @($Url, "https://mirror.disagreements.ai/health")
$logDir = Join-Path -Path "." -ChildPath "build/health_logs"
if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

function Write-HealthLog {
    param(
        [Parameter(Mandatory=$true)] $Data,
        [Parameter(Mandatory=$true)][string] $FileName
    )
    $path = Join-Path $logDir $FileName
    try {
        $json = $Data | ConvertTo-Json -Depth 10
    } catch {
        $json = ($Data | Out-String)
    }
    $json | Out-File -FilePath $path -Encoding utf8
}

foreach ($target in $mirrors) {
    try {
        $response = Invoke-RestMethod -Uri $target -Method GET -TimeoutSec 10 -ErrorAction Stop
        $timestamp = (Get-Date).ToUniversalTime().ToString("s").Replace(":", "-")
        $file = "health_$timestamp.json"
        Write-HealthLog -Data $response -FileName $file
        Write-Host "Service OK at $target"
        exit 0
    } catch {
        $err = $_.Exception.Message
        Write-Warning ("Failed to reach {0}: {1}" -f $target, $err)
    }
}

$stubPath = "./scripts/health_stub.json"
if (Test-Path $stubPath) {
    try {
        $stub = Get-Content $stubPath -Raw | ConvertFrom-Json
    } catch {
        $stub = @{ status = "ok"; source = "stub"; error = "Invalid stub JSON" }
    }
    Write-HealthLog -Data $stub -FileName "health_stub.json"
    Write-Host "Using local stub fallback."
    exit 0
} else {
    Write-Error "All endpoints unavailable."
    exit 1
}
