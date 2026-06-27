# 打包脚本：生成无控制台单文件 exe（后台运行：悬浮球 + 托盘）
# 前置：.\venv 已安装核心依赖
# 用法：.\build.ps1
$ErrorActionPreference = "Stop"

Write-Host "==> 生成应用图标" -ForegroundColor Cyan
& .\venv\Scripts\python generate_icon.py
if (-not (Test-Path "assets\glm.ico")) { throw "图标生成失败" }

Write-Host "==> 确保 PyInstaller 已安装" -ForegroundColor Cyan
& .\venv\Scripts\python -m pip install pyinstaller | Out-Null

# PySide6 未用到的大模块（WebEngine/Qt3D/QML/Charts/SQL 等），排除以瘦身
$unusedQt = @(
    'QtQml','QtQuick','QtQuick3D','QtQuickWidgets','QtQuickControls2',
    'QtQuickTemplates2','QtQuickParticles','QtQuickShapes','QtQuickTest',
    'QtWebEngineCore','QtWebEngineWidgets','QtWebChannel','QtWebEngineQuick',
    'Qt3DCore','Qt3DRender','Qt3DInput','Qt3DLogic','Qt3DExtras','Qt3DAnimation',
    'QtCharts','QtDataVisualization','QtDataVisualizationQml',
    'QtMultimedia','QtMultimediaWidgets',
    'QtPdf','QtPdfWidgets',
    'QtBluetooth','QtNfc','QtPositioning','QtLocation','QtSensors',
    'QtSerialPort','QtSerialBus','QtSql','QtTest','QtHelp',
    'QtDesigner','QtUiTools','QtRemoteObjects','QtScxml','QtStateMachine'
)

$pyargs = @(
    '--noconfirm','--clean','--windowed','--onefile',
    '--name','glm-monitor',
    '--icon','assets\glm.ico',
    '--exclude-module','rich',
    '--exclude-module','plotext'
)
foreach ($q in $unusedQt) { $pyargs += '--exclude-module'; $pyargs += "PySide6.$q" }
$pyargs += 'monitor.py'

Write-Host "==> PyInstaller 打包（--windowed --onefile，排除 $($unusedQt.Count) 个未用 PySide6 模块）" -ForegroundColor Cyan
& .\venv\Scripts\pyinstaller @pyargs
if ($LASTEXITCODE -ne 0) { throw "PyInstaller 打包失败（退出码 $LASTEXITCODE）" }

if (Test-Path "dist\glm-monitor.exe") {
    $size = [math]::Round((Get-Item "dist\glm-monitor.exe").Length / 1MB, 1)
    Write-Host ""
    Write-Host "==> 打包完成：dist\glm-monitor.exe ($size MB)" -ForegroundColor Green
    Write-Host "    使用：把 .env 放到 exe 旁，双击运行" -ForegroundColor Yellow
    Write-Host "    数据/日志存于：%APPDATA%\glm-monitor\" -ForegroundColor Yellow
} else {
    throw "打包失败：dist\glm-monitor.exe 未生成"
}