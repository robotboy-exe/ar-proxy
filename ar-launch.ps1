$dir = $PSScriptRoot
$env:AGENTROUTER_KEY = [Environment]::GetEnvironmentVariable("AGENTROUTER_KEY","User")
if (-not $env:AGENTROUTER_KEY) { Write-Host "AGENTROUTER_KEY is not saved."; exit 1 }
if (-not (Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue)) {
  Start-Process python -ArgumentList "proxy.py" -WorkingDirectory $dir -WindowStyle Hidden
  Start-Sleep -Seconds 2
}
$env:OPENCODE_CONFIG = Join-Path $dir "oc-windows.json"
opencode
