# Open AnyCodex Windows Installer (PowerShell)
# Run ANY LLM in OpenAI Codex & ChatGPT Desktop with 100% Tool Parity.
# GitHub: https://github.com/emonibnmustafa/anycodex

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "               ⚡ OPEN ANYCODEX INSTALLER (WINDOWS)         " -ForegroundColor Cyan
Write-Host "  Run Any LLM in ChatGPT Desktop with 100% Full Tool Parity " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Node.js
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Node.js is required but not found." -ForegroundColor Red
    Write-Host "Please install Node.js from https://nodejs.org or via winget: winget install OpenJS.NodeJS" -ForegroundColor Yellow
    exit 1
}

# 2. Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python 3 is required but not found." -ForegroundColor Red
    Write-Host "Please install Python 3 from https://python.org or via winget: winget install Python.Python.3.11" -ForegroundColor Yellow
    exit 1
}

$CodexDir = Join-Path $env:USERPROFILE ".codex"
$TargetDir = Join-Path $CodexDir "anycodex"
$Repo = "emonibnmustafa/anycodex"
$BaseUrl = "https://raw.githubusercontent.com/$Repo/main"

Write-Host "📦 Setting up Open AnyCodex directory at: $TargetDir" -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null
New-Item -ItemType Directory -Force -Path $CodexDir | Out-Null

# Download components
Write-Host "🌐 Downloading Open AnyCodex components..." -ForegroundColor Green
Invoke-WebRequest -Uri "$BaseUrl/adapter.mjs" -OutFile (Join-Path $TargetDir "adapter.mjs")
Invoke-WebRequest -Uri "$BaseUrl/codex_switch.py" -OutFile (Join-Path $TargetDir "codex_switch.py")
Invoke-WebRequest -Uri "$BaseUrl/providers.example.json" -OutFile (Join-Path $TargetDir "providers.example.json")

$CustomProv = Join-Path $CodexDir "custom_providers.json"
if (-not (Test-Path $CustomProv)) {
    Copy-Item (Join-Path $TargetDir "providers.example.json") $CustomProv
}

# 3. Setup Startup Gateway (VBS silent background runner)
$StartupDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Startup"
$VbsPath = Join-Path $StartupDir "anycodex-gateway.vbs"
$AdapterPath = (Join-Path $TargetDir "adapter.mjs").Replace("\", "\\")

$VbsContent = @"
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "node `"$AdapterPath`"", 0, False
"@
Set-Content -Path $VbsPath -Value $VbsContent -Encoding ASCII

# Kill existing node adapter instances and start fresh
Stop-Process -Name node -ErrorAction SilentlyContinue
Start-Process "wscript.exe" -ArgumentList "`"$VbsPath`"" -WindowStyle Hidden
Write-Host "⚙️  Background gateway daemon started on http://127.0.0.1:8765" -ForegroundColor Green

# 4. Add PowerShell Profile Aliases
$ProfilePath = $PROFILE
if (-not (Test-Path $ProfilePath)) {
    New-Item -ItemType File -Force -Path $ProfilePath | Out-Null
}

$ProfileContent = Get-Content $ProfilePath -Raw -ErrorAction SilentlyContinue
if ($ProfileContent -notmatch "anycodex") {
    $AliasBlock = @"

# --- Open AnyCodex CLI Helpers ---
function anycodex { python "$TargetDir\codex_switch.py" `$args }
function usemeta { anycodex use meta }
function useopenai { anycodex use openai }
function setmeta { param(`$key) anycodex set-key meta `$key }
# ---------------------------------
"@
    Add-Content -Path $ProfilePath -Value $AliasBlock
    Write-Host "✅ Added PowerShell functions (anycodex, usemeta, useopenai) to profile!" -ForegroundColor Green
}

# 5. Dual-App Setup on Windows
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "           🎉 Open AnyCodex Installation Complete!          " -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Setting up 'Open AnyCodex' Desktop shortcut..." -ForegroundColor Yellow
python (Join-Path $TargetDir "codex_switch.py") dual-app

Write-Host "Commands to get started:" -ForegroundColor Cyan
Write-Host "  anycodex status             -> View active provider & health"
Write-Host "  anycodex dual-app           -> Setup side-by-side desktop app"
Write-Host "  anycodex use meta           -> Switch to Meta Muse Spark (Unlimited Free)"
Write-Host "  anycodex use openai         -> Switch back to official ChatGPT Plus"
Write-Host "  anycodex list               -> List all available providers"
Write-Host ""
Write-Host "Please restart your PowerShell window or run: . `$PROFILE" -ForegroundColor Yellow
