$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Workspace = Join-Path $env:USERPROFILE '.openclaw\workspace'
if (-not (Test-Path $Workspace)) { throw "OpenClaw workspace not found: $Workspace" }
Write-Host "Installing openclaw-task-watchdog into $Workspace"
Copy-Item (Join-Path $RepoRoot 'tools') (Join-Path $Workspace 'tools') -Recurse -Force
Copy-Item (Join-Path $RepoRoot 'tasks') (Join-Path $Workspace 'tasks') -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $RepoRoot 'config') (Join-Path $Workspace 'config') -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $RepoRoot 'docs\OPERATE.md') (Join-Path $Workspace 'OPERATE.md') -Force
Write-Host ''
Write-Host 'Install complete.'
Write-Host 'Recommended next steps:'
Write-Host '1) Run acceptance:'
Write-Host '   python tools\run_report_delivery_acceptance.py'
Write-Host '2) Check live status:'
Write-Host '   python tools\report_delivery_status.py'
Write-Host '3) Read docs/OPERATE.md in the workspace if you want operator details.'
