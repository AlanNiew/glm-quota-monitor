# 打包脚本：生成无控制台单文件 exe（后台运行：悬浮球 + 托盘）
# 前置：.\venv 已安装核心依赖
# 用法：.\build.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> 生成应用图标" -ForegroundColor Cyan
& .\venv\Scripts\python generate_icon.py
if (-not (Test-Path "assets\glm.ico")) { throw "图标生成失败" }

Write-Host "==> 确保 PyInstaller 已安装" -ForegroundColor Cyan
& .\venv\Scripts\python -m pip install pyinstaller | Out-Null

Write-Host "==> PyInstaller 打包（--windowed --onefile，排除 rich/plotext）" -ForegroundColor Cyan
& .\venv\Scripts\pyinstaller --noconfirm --clean --windowed --onefile `
    --name glm-monitor `
    --icon "assets\glm.ico" `
    --exclude-module rich `
    --exclude-module plotext `
    --collect-all PySide6 `
    monitor.py

if (Test-Path "dist\glm-monitor.exe") {
    $size = [math]::Round((Get-Item "dist\glm-monitor.exe").Length / 1MB, 1)
    Write-Host ""
    Write-Host "==> 打包完成：dist\glm-monitor.exe ($size MB)" -ForegroundColor Green
    Write-Host "    使用：把 .env 放到 exe 旁，双击运行" -ForegroundColor Yellow
    Write-Host "    数据/日志存于：%APPDATA%\glm-monitor\" -ForegroundColor Yellow
} else {
    throw "打包失败：dist\glm-monitor.exe 未生成"
}
