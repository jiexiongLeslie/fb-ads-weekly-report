$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$logs = Join-Path $root "logs"

if (-not (Test-Path $logs)) {
    New-Item -ItemType Directory -Path $logs | Out-Null
}

$existing = Get-NetTCPConnection -LocalPort 5003 -State Listen -ErrorAction SilentlyContinue
if ($existing) {
    exit 0
}

Add-Content -Path (Join-Path $logs "startup.log") -Value "$(Get-Date -Format s) starting service"

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
    Add-Content -Path (Join-Path $logs "startup.log") -Value "$(Get-Date -Format s) py launcher not found"
    exit 1
}

py -c "import flask, flask_cors, requests" 2>$null
if ($LASTEXITCODE -ne 0) {
    py -m pip install flask flask-cors requests -q
}

$pythonw = py -c "import pathlib, sys; print(pathlib.Path(sys.executable).with_name('pythonw.exe'))"
if (-not (Test-Path $pythonw)) {
    $pythonw = (py -c "import sys; print(sys.executable)")
}

$env:FB_REPORT_PORT = "5003"
$outLog = Join-Path $logs "server.log"
$errLog = Join-Path $logs "server.err.log"

Start-Process `
    -FilePath $pythonw `
    -ArgumentList "server.py" `
    -WorkingDirectory $backend `
    -WindowStyle Hidden `
    -RedirectStandardOutput $outLog `
    -RedirectStandardError $errLog

Add-Content -Path (Join-Path $logs "startup.log") -Value "$(Get-Date -Format s) started via $pythonw"
