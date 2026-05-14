$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $scriptDir "backend"

if (-not (Test-Path $backendDir)) {
    Write-Host "[ERROR] backend directory was not found." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

$py = Get-Command py -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host "[ERROR] Python launcher 'py' was not found. Please install Python or add it to PATH." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Set-Location $backendDir

py -c "import flask, flask_cors, requests" 2>$null
if ($LASTEXITCODE -ne 0) {
    py -m pip install flask flask-cors requests -q
}

$env:FB_REPORT_PORT = "5003"
Write-Host "Service URL: http://localhost:5003" -ForegroundColor Cyan
py server.py
