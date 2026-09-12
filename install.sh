#!/usr/bin/env bash
set -e

# AnyCodex Installer
# Brings any LLM (Meta Muse Spark, DeepSeek, Groq, Ollama, OpenRouter) to Codex Desktop with full Computer Use and Code Mode.

echo "====================================================="
echo "           🚀 AnyCodex Automated Installer           "
echo "  Run Any LLM in ChatGPT Desktop with Full Tool Parity"
echo "====================================================="

# 1. Prerequisites Check
if [[ "$OSTYPE" != "darwin"* ]]; then
  echo "❌ AnyCodex currently supports macOS."
  exit 1
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
GITHUB_REPO="${ANYCODEX_REPO:-__REPO_PLACEHOLDER__}"
RAW_BASE_URL="https://raw.githubusercontent.com/${GITHUB_REPO}/main"

echo "📦 Setting up AnyCodex directory at: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
mkdir -p "$HOME/.codex"
mkdir -p "$PLIST_DIR"

# Check if running locally from cloned folder or piped via curl
SCRIPT_DIR=""
if [ -n "${BASH_SOURCE[0]}" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fi

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/adapter.mjs" ]; then
  echo "📁 Copying local files..."
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
echo "⚙️  Configuring background gateway service..."
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

# Restart service
launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load -w "$PLIST_FILE"

# 3. Add Shell Aliases
SHELL_RC="$HOME/.zshrc"
if [[ "$SHELL" == *"bash"* ]]; then
  SHELL_RC="$HOME/.bashrc"
fi

ALIAS_BLOCK="
# --- AnyCodex CLI ---
alias anycodex=\"python3 $TARGET_DIR/codex_switch.py\"
alias usemeta=\"python3 $TARGET_DIR/codex_switch.py use meta\"
alias useopenai=\"python3 $TARGET_DIR/codex_switch.py use openai\"
alias setmeta=\"python3 $TARGET_DIR/codex_switch.py set-key meta\"
# --------------------"

if ! grep -q "AnyCodex CLI" "$SHELL_RC" 2>/dev/null; then
  echo "$ALIAS_BLOCK" >> "$SHELL_RC"
  echo "✅ Added 'anycodex', 'usemeta', 'useopenai' aliases to $SHELL_RC"
fi

# Link into user path if available
if [[ -w "/usr/local/bin" ]]; then
  ln -sf "$TARGET_DIR/codex_switch.py" "/usr/local/bin/anycodex" 2>/dev/null || true
elif mkdir -p "$HOME/.local/bin" 2>/dev/null; then
  ln -sf "$TARGET_DIR/codex_switch.py" "$HOME/.local/bin/anycodex" 2>/dev/null || true
fi

# 4. Optional 1-Click Interactive Setup (works even when piped via curl | bash)
if [ -e /dev/tty ]; then
  exec < /dev/tty
  echo ""
  echo "-----------------------------------------------------"
  echo "⚡ Quick Setup:"
  read -p "👉 Would you like to enter your Meta API Key right now? (y/n, default: y): " setup_now
  setup_now=${setup_now:-y}
  if [[ "$setup_now" =~ ^[Yy]$ ]]; then
    read -p "🔑 Paste your Meta API Key: " user_key
    if [[ -n "$user_key" ]]; then
      python3 "$TARGET_DIR/codex_switch.py" set-key meta "$user_key"
      python3 "$TARGET_DIR/codex_switch.py" use meta
      echo "🎉 Meta Muse Spark activated! You are ready to code."
    fi
  fi
  echo "-----------------------------------------------------"
fi

echo ""
echo "🎉 AnyCodex installation complete!"
echo ""
echo "Quick Start Commands:"
echo "  • Reload shell:   source $SHELL_RC"
echo "  • Switch to Meta:  usemeta   (or: anycodex use meta)"
echo "  • Set API Key:     setmeta \"YOUR_KEY\""
echo "  • Back to Plus:    useopenai"
echo "  • Check Status:    anycodex status"
echo "  • Add New LLM:     anycodex add"
echo ""
echo "====================================================="
