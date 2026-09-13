# AnyCodex Windows Uninstaller (PowerShell)

Write-Host "Removing AnyCodex background service..." -ForegroundColor Yellow
$StartupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$VbsPath = Join-Path $StartupDir "anycodex-gateway.vbs"
if (Test-Path $VbsPath) { Remove-Item $VbsPath -Force }

Stop-Process -Name node -ErrorAction SilentlyContinue

$TargetDir = Join-Path $env:USERPROFILE ".codex\anycodex"
if (Test-Path $TargetDir) {
    Remove-Item -Recurse -Force $TargetDir
}

$DesktopShortcut = Join-Path $env:USERPROFILE "Desktop\AnyCodex.cmd"
if (Test-Path $DesktopShortcut) { Remove-Item $DesktopShortcut -Force }

Write-Host "✅ AnyCodex has been uninstalled." -ForegroundColor Green
