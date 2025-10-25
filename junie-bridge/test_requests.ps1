<#
Junie Bridge — PowerShell helper functions

Usage (from repo root):

  # Load the functions into your session
  . .\junie-bridge\test_requests.ps1

  # Call /health
  Invoke-JunieHealth -SkipCertificateCheck

  # Search for "TODO" (HTTPS self-signed -> use -SkipCertificateCheck on pwsh, or we set a .NET bypass on Windows PowerShell)
  Invoke-JunieSearch -Query "TODO" -MaxResults 10 -SkipCertificateCheck

  # Open a file in IntelliJ at line 1
  Invoke-JunieOpen -Path "README.md" -Line 1 -SkipCertificateCheck

Notes
- Headers and body are built with variables to avoid PowerShell line-continuation pitfalls.
- Token and base URL are resolved from junie-bridge/.env when present; fall back to defaults.
- For Windows PowerShell (5.1), -SkipCertificateCheck is not available. We temporarily bypass cert validation when the switch is used.
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-JunieEnv {
  [CmdletBinding()]
  param(
    [string]$EnvPath = (Join-Path $PSScriptRoot '.env')
  )
  $cfg = @{}
  if (Test-Path $EnvPath) {
    foreach ($line in Get-Content -LiteralPath $EnvPath) {
      if (-not $line -or $line.Trim().StartsWith('#')) { continue }
      $idx = $line.IndexOf('=')
      if ($idx -lt 0) { continue }
      $k = $line.Substring(0, $idx).Trim()
      $v = $line.Substring($idx + 1).Trim()
      $cfg[$k] = $v
    }
  }
  $useHttps = ($cfg['USE_HTTPS'] ?? 'false').ToLower() -eq 'true'
  $port = if ($cfg.ContainsKey('PORT') -and $cfg['PORT']) { [int]$cfg['PORT'] } else { 8765 }
  $token = if ($cfg.ContainsKey('JUNIE_TOKEN') -and $cfg['JUNIE_TOKEN']) { $cfg['JUNIE_TOKEN'] } else { 'dev' }
  $scheme = if ($useHttps) { 'https' } else { 'http' }
  $baseUrl = "${scheme}://localhost:${port}"
  [pscustomobject]@{ BaseUrl = $baseUrl; Token = $token; UseHttps = $useHttps }
}

function Use-InsecureCertBypassIfNeeded {
  param([switch]$SkipCertificateCheck)
  if (-not $SkipCertificateCheck) { return }
  # pwsh (PowerShell 7+) supports -SkipCertificateCheck on Invoke-RestMethod; Windows PowerShell 5.1 does not.
  $isPwsh = $PSVersionTable.PSEdition -eq 'Core'
  if (-not $isPwsh) {
    # Temporarily bypass SSL validation for this session (Windows PowerShell only)
    add-type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
  public bool CheckValidationResult(ServicePoint srvPoint, X509Certificate certificate, WebRequest request, int certificateProblem) { return true; }
}
"@
    [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
  }
}

function Invoke-JunieHealth {
  [CmdletBinding()]
  param([switch]$SkipCertificateCheck)
  $envCfg = Get-JunieEnv
  $headers = @{ 'X-Junie-Token' = $envCfg.Token }
  Use-InsecureCertBypassIfNeeded -SkipCertificateCheck:$SkipCertificateCheck
  $params = @{ Method = 'GET'; Uri = "$($envCfg.BaseUrl)/health"; Headers = $headers }
  if ($PSVersionTable.PSEdition -eq 'Core' -and $SkipCertificateCheck) { $params['SkipCertificateCheck'] = $true }
  Invoke-RestMethod @params
}

function Invoke-JunieSearch {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)] [string]$Query,
    [string[]]$Glob = @('**/*'),
    [int]$MaxResults = 200,
    [switch]$Regex,
    [switch]$CaseSensitive,
    [switch]$SkipCertificateCheck
  )
  $envCfg = Get-JunieEnv
  $headers = @{ 'Content-Type' = 'application/json'; 'X-Junie-Token' = $envCfg.Token }
  $bodyObj = @{ query = $Query; glob = $Glob; maxResults = $MaxResults; regex = [bool]$Regex; caseSensitive = [bool]$CaseSensitive }
  $json = $bodyObj | ConvertTo-Json -Depth 6
  Use-InsecureCertBypassIfNeeded -SkipCertificateCheck:$SkipCertificateCheck
  $params = @{ Method = 'POST'; Uri = "$($envCfg.BaseUrl)/search"; Headers = $headers; Body = $json }
  if ($PSVersionTable.PSEdition -eq 'Core' -and $SkipCertificateCheck) { $params['SkipCertificateCheck'] = $true }
  Invoke-RestMethod @params
}

function Invoke-JunieOpen {
  [CmdletBinding()]
  param(
    [Parameter(Mandatory)] [string]$Path,
    [int]$Line = 1,
    [switch]$SkipCertificateCheck
  )
  $envCfg = Get-JunieEnv
  $headers = @{ 'Content-Type' = 'application/json'; 'X-Junie-Token' = $envCfg.Token }
  $bodyObj = @{ path = $Path; line = $Line }
  $json = $bodyObj | ConvertTo-Json -Depth 4
  Use-InsecureCertBypassIfNeeded -SkipCertificateCheck:$SkipCertificateCheck
  $params = @{ Method = 'POST'; Uri = "$($envCfg.BaseUrl)/ide/open"; Headers = $headers; Body = $json }
  if ($PSVersionTable.PSEdition -eq 'Core' -and $SkipCertificateCheck) { $params['SkipCertificateCheck'] = $true }
  Invoke-RestMethod @params
}

Export-ModuleMember -Function Invoke-JunieHealth,Invoke-JunieSearch,Invoke-JunieOpen