#!/usr/bin/env bash
set -e

echo "====================================================="
echo "           🗑️  AnyCodex Uninstaller                 "
echo "====================================================="

PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_LABEL="com.codex.anycodex-adapter"
PLIST_FILE="$PLIST_DIR/$PLIST_LABEL.plist"
TARGET_DIR="$HOME/.codex/anycodex"

# 1. Stop and remove launchd service
if [[ -f "$PLIST_FILE" ]]; then
  echo "⏹️  Stopping and removing background gateway..."
  launchctl unload "$PLIST_FILE" 2>/dev/null || true
  rm -f "$PLIST_FILE"
fi

# 2. Revert Codex config to native OpenAI
if [[ -f "$TARGET_DIR/codex_switch.py" ]]; then
  python3 "$TARGET_DIR/codex_switch.py" use openai 2>/dev/null || true
fi

# 3. Clean up shell aliases
clean_rc() {
  local rc="$1"
  if [[ -f "$rc" ]]; then
    sed -i '' '/# --- AnyCodex CLI ---/,/# --------------------/d' "$rc" 2>/dev/null || true
    echo "🧹 Cleaned aliases from $rc"
  fi
}

clean_rc "$HOME/.zshrc"
clean_rc "$HOME/.bashrc"

# 4. Remove CLI links
rm -f "/usr/local/bin/anycodex" 2>/dev/null || true
rm -f "$HOME/.local/bin/anycodex" 2>/dev/null || true

# 5. Remove anycodex directory
if [[ -d "$TARGET_DIR" ]]; then
  rm -rf "$TARGET_DIR"
  echo "🗑️  Removed $TARGET_DIR"
fi

echo ""
echo "✅ AnyCodex has been completely uninstalled."
echo "Your ChatGPT Desktop / Codex app has been restored to native OpenAI mode."
echo "====================================================="
