$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Workspace = Join-Path $env:USERPROFILE '.openclaw\workspace'
if (-not (Test-Path $Workspace)) { throw "OpenClaw workspace not found: $Workspace" }
Write-Host "Installing openclaw-hard-delivery into $Workspace"
Copy-Item (Join-Path $RepoRoot 'tools') (Join-Path $Workspace 'tools') -Recurse -Force
Copy-Item (Join-Path $RepoRoot 'tasks') (Join-Path $Workspace 'tasks') -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $RepoRoot 'config') (Join-Path $Workspace 'config') -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $RepoRoot 'docs\OPERATE.md') (Join-Path $Workspace 'OPERATE.md') -Force
Write-Host 'Install complete. Recommended next step:'
Write-Host 'python tools\run_report_delivery_acceptance.py'
