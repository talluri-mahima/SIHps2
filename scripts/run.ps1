$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $taskRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) { throw 'Create the Python environment and install requirements.lock first; see README.md.' }
if (-not (Test-Path -LiteralPath 'web\dist\index.html')) { throw 'Build the interface with npm run build in web first.' }
Write-Host 'Evidence Workbench: http://127.0.0.1:8765'
& '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8765
