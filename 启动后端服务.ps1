# Facebook Ads 数据同步服务启动脚本
# 使用 PowerShell 执行

$Host.UI.RawUI.WindowTitle = "Facebook Ads 数据同步服务"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   Facebook Ads 数据同步服务启动器" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 获取脚本所在目录
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ScriptDir "backend"

# 检查后端目录是否存在
if (-not (Test-Path $BackendDir)) {
    Write-Host "错误: 找不到 backend 目录" -ForegroundColor Red
    Write-Host "请确保此脚本位于项目根目录" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

# 切换到后端目录
Set-Location $BackendDir

Write-Host "正在检查依赖..." -ForegroundColor Yellow

# 检查 Python 是否安装
$PythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $PythonCmd) {
    Write-Host "错误: 未找到 Python，请先安装 Python" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
    exit 1
}

# 检查依赖是否已安装
$Dependencies = @("flask", "flask_cors", "requests")
$MissingDeps = @()

foreach ($Dep in $Dependencies) {
    try {
        python -c "import $Dep" 2>$null
        if ($LASTEXITCODE -ne 0) {
            $MissingDeps += $Dep
        }
    } catch {
        $MissingDeps += $Dep
    }
}

# 安装缺失的依赖
if ($MissingDeps.Count -gt 0) {
    Write-Host "正在安装缺失的依赖: $($MissingDeps -join ', ')" -ForegroundColor Yellow
    pip install $MissingDeps -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "依赖安装失败，请手动运行: pip install flask flask-cors requests" -ForegroundColor Red
        Read-Host "按 Enter 键退出"
        exit 1
    }
}

Write-Host ""
Write-Host "启动后端服务..." -ForegroundColor Green
Write-Host "访问地址: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "API 端点:" -ForegroundColor Gray
Write-Host "  POST /api/sync       - 同步数据" -ForegroundColor Gray
Write-Host "  GET  /api/data       - 获取数据" -ForegroundColor Gray
Write-Host "  GET  /api/accounts   - 获取账户列表" -ForegroundColor Gray
Write-Host "  GET  /api/token-status - 检查 Token" -ForegroundColor Gray
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 启动服务
try {
    python server.py
} catch {
    Write-Host "启动失败: $_" -ForegroundColor Red
    Read-Host "按 Enter 键退出"
}
