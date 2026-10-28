$ErrorActionPreference = 'Stop'
$prototypeRoot = Split-Path -Parent $PSScriptRoot
$prototypePython = Join-Path $prototypeRoot '.venv\Scripts\python.exe'
$prototypeSuffix = '-m uvicorn app.main:app --host 127.0.0.1 --port 8765'
# Only stop this checkout's exact loopback prototype command, never arbitrary Python.
$prototypeProcesses = @(Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -and $_.CommandLine.Contains($prototypePython) -and $_.CommandLine.EndsWith($prototypeSuffix) })
foreach ($prototypeProcess in $prototypeProcesses) {
    Stop-Process -Id $prototypeProcess.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 500
& (Join-Path $PSScriptRoot 'start-prototype.ps1')
