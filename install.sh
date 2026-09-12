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

echo "📦 Setting up AnyCodex directory at: $TARGET_DIR"
mkdir -p "$TARGET_DIR"
mkdir -p "$HOME/.codex"
mkdir -p "$PLIST_DIR"

# Copy engine scripts
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/adapter.mjs" "$TARGET_DIR/adapter.mjs"
cp "$SCRIPT_DIR/codex_switch.py" "$TARGET_DIR/codex_switch.py"
chmod +x "$TARGET_DIR/codex_switch.py"

# Initialize custom_providers.json if not existing
if [[ ! -f "$HOME/.codex/custom_providers.json" ]]; then
  if [[ -f "$SCRIPT_DIR/providers.example.json" ]]; then
    cp "$SCRIPT_DIR/providers.example.json" "$HOME/.codex/custom_providers.json"
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

# Also link into /usr/local/bin or ~/.local/bin if writable
if [[ -w "/usr/local/bin" ]]; then
  ln -sf "$TARGET_DIR/codex_switch.py" "/usr/local/bin/anycodex" 2>/dev/null || true
elif mkdir -p "$HOME/.local/bin" 2>/dev/null; then
  ln -sf "$TARGET_DIR/codex_switch.py" "$HOME/.local/bin/anycodex" 2>/dev/null || true
fi

echo ""
echo "🎉 AnyCodex installation complete!"
echo ""
echo "Quick Start:"
echo "  1. Reload your shell:  source $SHELL_RC"
echo "  2. Switch to Meta:     usemeta   (or: anycodex use meta)"
echo "  3. Set your API Key:   setmeta \"YOUR_KEY\""
echo "  4. Switch to OpenAI:   useopenai"
echo "  5. View status:        anycodex status"
echo "  6. Add custom model:   anycodex add"
echo ""
echo "For more details, visit: https://github.com/your-username/anycodex"
echo "====================================================="
