#!/usr/bin/env bash
set -e

# AnyCodex Installer
# Run ANY LLM in OpenAI Codex & ChatGPT Desktop with 100% Tool Parity (Computer Use, Code Mode, Zero Limits).
# GitHub: https://github.com/emonibnmustafa/anycodex

echo "============================================================"
echo "               ⚡ OPEN ANYCODEX INSTALLER                   "
echo "  Run Any LLM in ChatGPT Desktop with 100% Full Tool Parity "
echo "============================================================"

# 1. Platform Check
if [[ "$OSTYPE" != "darwin"* ]]; then
  if [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "win32"* ]] || [[ "$OSTYPE" == "cygwin"* ]]; then
    echo "💡 Detected Windows environment!"
    echo "   For native Windows installation, please run in PowerShell:"
    echo "   irm https://raw.githubusercontent.com/emonibnmustafa/anycodex/main/install.ps1 | iex"
    exit 0
  fi
fi

if ! command -v node >/dev/null 2>&1; then
  echo "❌ Node.js is required but not found. Please install Node.js (e.g. brew install node)."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Python 3 is required but not found. Please install Python 3."
  exit 1
fi

TARGET_DIR="$HOME/.codex/anycodex"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_LABEL="com.codex.anycodex-adapter"
PLIST_FILE="$PLIST_DIR/$PLIST_LABEL.plist"
NODE_PATH="$(command -v node)"
GITHUB_REPO="${ANYCODEX_REPO:-emonibnmustafa/anycodex}"
RAW_BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/main"

echo "📦 Setting up AnyCodex at: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
mkdir -p "$HOME/.codex"
mkdir -p "$PLIST_DIR"

SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/adapter.mjs" ]; then
  echo "📁 Copying local AnyCodex components..."
  cp "$SCRIPT_DIR/adapter.mjs" "$TARGET_DIR/adapter.mjs"
  cp "$SCRIPT_DIR/codex_switch.py" "$TARGET_DIR/codex_switch.py"
  cp "$SCRIPT_DIR/uninstall.sh" "$TARGET_DIR/uninstall.sh" 2>/dev/null || true
  if [ -f "$SCRIPT_DIR/providers.example.json" ]; then
    cp "$SCRIPT_DIR/providers.example.json" "$TARGET_DIR/providers.example.json"
  fi
else
  echo "🌐 Downloading latest AnyCodex components..."
  curl -fsSL "${RAW_BASE_URL}/adapter.mjs" -o "$TARGET_DIR/adapter.mjs"
  curl -fsSL "${RAW_BASE_URL}/codex_switch.py" -o "$TARGET_DIR/codex_switch.py"
  curl -fsSL "${RAW_BASE_URL}/uninstall.sh" -o "$TARGET_DIR/uninstall.sh" 2>/dev/null || true
  curl -fsSL "${RAW_BASE_URL}/providers.example.json" -o "$TARGET_DIR/providers.example.json" 2>/dev/null || true
fi

chmod +x "$TARGET_DIR/codex_switch.py"
chmod +x "$TARGET_DIR/uninstall.sh" 2>/dev/null || true

# Initialize custom_providers.json if not existing
if [[ ! -f "$HOME/.codex/custom_providers.json" ]]; then
  if [[ -f "$TARGET_DIR/providers.example.json" ]]; then
    cp "$TARGET_DIR/providers.example.json" "$HOME/.codex/custom_providers.json"
  else
    python3 "$TARGET_DIR/codex_switch.py" list >/dev/null 2>&1 || true
  fi
fi

# 2. Configure launchd Background Service
echo "⚙️  Configuring background gateway daemon..."
cat << LAUNCHD_EOF > "$PLIST_FILE"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$NODE_PATH</string>
        <string>$TARGET_DIR/adapter.mjs</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/.codex/anycodex.out.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/.codex/anycodex.err.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin</string>
    </dict>
</dict>
</plist>
LAUNCHD_EOF

# Restart launchd service
launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load -w "$PLIST_FILE"

# 3. Add Shell Helpers
add_shell_helpers() {
  local RC_FILE="$1"
  if [[ -f "$RC_FILE" ]]; then
    if ! grep -q "anycodex" "$RC_FILE"; then
      cat << 'RC_EOF' >> "$RC_FILE"

# --- AnyCodex CLI Helpers ---
anycodex() { python3 "$HOME/.codex/anycodex/codex_switch.py" "$@"; }
usemeta() { anycodex use meta; }
useopenai() { anycodex use openai; }
setmeta() { anycodex set-key meta "$1"; }
# ---------------------------------
RC_EOF
      echo "✅ Added CLI shortcuts (anycodex, usemeta, useopenai) to $RC_FILE"
    fi
  fi
}

add_shell_helpers "$HOME/.zshrc"
add_shell_helpers "$HOME/.bashrc"

# 4. Interactive Dual-App Setup or API Key
echo ""
echo "============================================================"
echo "           🎉 AnyCodex Core Setup Complete!            "
echo "============================================================"
echo "Gateway running on: http://127.0.0.1:8765/v1"
echo ""

if [[ "$1" == "--dual-app" ]]; then
  python3 "$TARGET_DIR/codex_switch.py" dual-app
else
  echo "💡 TIP: Want to run official ChatGPT Plus AND AnyCodex"
  echo "   side-by-side at the exact same time without switching?"
  echo "   Run: anycodex dual-app"
fi

echo ""
echo "Commands to get started:"
echo "  anycodex status             -> View active provider & health"
echo "  anycodex dual-app           -> Setup standalone side-by-side app"
echo "  anycodex use meta           -> Switch to Meta Muse Spark (Free Unlimited)"
echo "  anycodex use openai         -> Switch back to official ChatGPT Plus"
echo "  anycodex list               -> List all available providers"
echo ""
echo "Restart your terminal or run: source ~/.zshrc"
