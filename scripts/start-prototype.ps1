$ErrorActionPreference = 'Stop'
$prototypeRoot = Split-Path -Parent $PSScriptRoot
$prototypePython = Join-Path $prototypeRoot '.venv\Scripts\python.exe'
$prototypeData = Join-Path $prototypeRoot '.data'
if (-not (Test-Path -LiteralPath $prototypePython)) { throw 'Install the project environment first. See README.md.' }
$prototypeHealth = $null
try {
    $prototypeHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/v1/health' -TimeoutSec 3
} catch { }
if ($null -ne $prototypeHealth) {
    if ($prototypeHealth.profile -eq 'development') { Write-Output 'Prototype already running: http://127.0.0.1:8765'; exit 0 }
    throw 'Port 8765 is occupied by a different application.'
}
New-Item -ItemType Directory -Path $prototypeData -Force | Out-Null
$prototypeProcess = Start-Process -FilePath $prototypePython -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765') -WorkingDirectory $prototypeRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $prototypeData 'server.stdout.log') -RedirectStandardError (Join-Path $prototypeData 'server.stderr.log')
Set-Content -LiteralPath (Join-Path $prototypeData 'server.pid') -Value $prototypeProcess.Id
for ($prototypeAttempt = 0; $prototypeAttempt -lt 25; $prototypeAttempt++) {
    try {
        $prototypeHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8765/v1/health' -TimeoutSec 2
        if ($prototypeHealth.profile -eq 'development') { Write-Output 'Prototype ready: http://127.0.0.1:8765'; exit 0 }
    } catch { }
    Start-Sleep -Seconds 1
}
throw 'The prototype did not start. Inspect .data/server.stderr.log.'
