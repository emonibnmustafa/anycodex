#!/usr/bin/env python3
import sys
import os
import re
import json
import subprocess

HOME = os.path.expanduser("~")
CODEX_DIR = os.path.join(HOME, ".codex")
CONFIG_PATH = os.path.join(CODEX_DIR, "config.toml")
PROVIDERS_PATH = os.path.join(CODEX_DIR, "custom_providers.json")
PLIST_LABEL = "com.codex.anycodex-adapter"

DEFAULT_PROVIDERS = {
    "active_provider": "meta",
    "providers": {
        "meta": {
            "name": "Meta Muse Spark (Unlimited Free)",
            "base_url": "https://api.meta.ai",
            "api_key": "",
            "model": "muse-spark-1.3-contributor",
            "wire_api": "responses"
        },
        "deepseek": {
            "name": "DeepSeek Coder",
            "base_url": "https://api.deepseek.com",
            "api_key": "",
            "model": "deepseek-coder",
            "wire_api": "responses"
        },
        "groq": {
            "name": "Groq Llama 3",
            "base_url": "https://api.groq.com/openai",
            "api_key": "",
            "model": "llama-3.3-70b-versatile",
            "wire_api": "responses"
        },
        "ollama": {
            "name": "Local Ollama",
            "base_url": "http://127.0.0.1:11434",
            "api_key": "ollama",
            "model": "qwen2.5-coder:latest",
            "wire_api": "responses"
        },
        "openrouter": {
            "name": "OpenRouter",
            "base_url": "https://openrouter.ai/api",
            "api_key": "",
            "model": "anthropic/claude-3.5-sonnet",
            "wire_api": "responses"
        }
    }
}

def load_providers_config():
    if not os.path.exists(PROVIDERS_PATH):
        save_providers_config(DEFAULT_PROVIDERS)
        return DEFAULT_PROVIDERS
    try:
        with open(PROVIDERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            merged = {**DEFAULT_PROVIDERS, **data}
            merged["providers"] = {**DEFAULT_PROVIDERS["providers"], **(data.get("providers") or {})}
            return merged
    except Exception:
        return DEFAULT_PROVIDERS

def save_providers_config(cfg):
    os.makedirs(CODEX_DIR, exist_ok=True)
    with open(PROVIDERS_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def read_codex_config():
    if not os.path.exists(CONFIG_PATH):
        return ""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return f.read()

def write_codex_config(content):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        f.write(content)

def restart_adapter():
    try:
        uid = os.getuid()
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/{PLIST_LABEL}"], capture_output=True)
    except Exception:
        pass

def switch_to_openai():
    content = read_codex_config()
    content = re.sub(r'^\s*model_provider\s*=\s*["\'][^"\']+["\']\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*model_catalog_json\s*=\s*["\'][^"\']+["\']\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*model\s*=\s*["\'][^"\']+["\']', 'model = "gpt-5.5"', content, flags=re.MULTILINE)
    content = re.sub(r'\n{3,}', '\n\n', content)
    write_codex_config(content)

    print("✅ Switched to ChatGPT Plus (OpenAI) native mode!")
    print("   • Default Model: GPT-5.5 / GPT-5.6")
    print("   • Plus features, usage meters & chat modes active.")

def switch_to_custom(provider_id):
    cfg = load_providers_config()
    if provider_id not in cfg.get("providers", {}):
        print(f"❌ Provider '{provider_id}' not found. Run 'anycodex list' to see available providers.")
        return

    prov = cfg["providers"][provider_id]
    cfg["active_provider"] = provider_id
    save_providers_config(cfg)

    content = read_codex_config()
    custom_provider_section = f'''[model_providers.{provider_id}]
name = "{prov.get('name', provider_id)}"
base_url = "http://127.0.0.1:8765/v1"
experimental_bearer_token = "local"
wire_api = "responses"
'''
    if f'[model_providers.{provider_id}]' not in content:
        content = content + '\n' + custom_provider_section

    # Ensure model
    target_model = prov.get("model", "custom-model")
    if re.search(r'^\s*model\s*=', content, re.MULTILINE):
        content = re.sub(r'^\s*model\s*=\s*["\'][^"\']+["\']', f'model = "{target_model}"', content, flags=re.MULTILINE)
    else:
        content = f'model = "{target_model}"\n' + content

    # Ensure model_provider
    if re.search(r'^\s*model_provider\s*=', content, re.MULTILINE):
        content = re.sub(r'^\s*model_provider\s*=\s*["\'][^"\']+["\']', f'model_provider = "{provider_id}"', content, flags=re.MULTILINE)
    else:
        content = re.sub(rf'(model\s*=\s*"{re.escape(target_model)}"\n)', rf'\1model_provider = "{provider_id}"\n', content)

    content = re.sub(r'\n{3,}', '\n\n', content)
    write_codex_config(content)
    restart_adapter()

    key = prov.get("api_key", "")
    key_preview = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else ("Configured" if key else "⚠️ Not set (run: anycodex set-key)")

    print(f"✅ Switched to {prov.get('name', provider_id)}!")
    print(f"   • Model     : {target_model}")
    print(f"   • Base URL  : {prov.get('base_url')}")
    print(f"   • API Key   : {key_preview}")
    print(f"   • Gateway   : http://127.0.0.1:8765/v1")
    print(f"   • Full Tools & Computer Use: ACTIVE")

def set_key(provider_id, key):
    cfg = load_providers_config()
    if provider_id not in cfg.get("providers", {}):
        print(f"❌ Provider '{provider_id}' not found.")
        return
    cfg["providers"][provider_id]["api_key"] = key.strip()
    save_providers_config(cfg)
    # Also write legacy file for backward compatibility if meta
    if provider_id == "meta":
        with open(os.path.join(CODEX_DIR, "meta_key.txt"), "w") as f:
            f.write(key.strip())
    restart_adapter()
    print(f"✅ API Key updated for '{provider_id}' successfully! No restart needed.")

def add_provider():
    print("\n--- Add Custom OpenAI-Compatible Provider ---")
    pid = input("Unique ID (e.g. mistral, vllm, myllm): ").strip().lower()
    if not pid:
        print("Canceled.")
        return
    name = input(f"Display Name [{pid}]: ").strip() or pid
    base_url = input("Base URL (e.g. https://api.mistral.ai or http://localhost:8000): ").strip()
    api_key = input("API Key (leave blank for local models): ").strip()
    model = input("Model name / slug (e.g. mistral-large-latest): ").strip()

    cfg = load_providers_config()
    cfg["providers"][pid] = {
        "name": name,
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "wire_api": "responses"
    }
    save_providers_config(cfg)
    print(f"\n✅ Provider '{pid}' added!")
    print(f"To use it immediately, run: anycodex use {pid}")

def print_status():
    content = read_codex_config()
    m_prov = re.search(r'^\s*model_provider\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    provider_id = m_prov.group(1).lower() if m_prov else "openai"
    m_model = re.search(r'^\s*model\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    model = m_model.group(1) if m_model else "unknown"

    cfg = load_providers_config()
    prov = cfg.get("providers", {}).get(provider_id, {})

    key = prov.get("api_key", "")
    key_preview = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else ("Configured" if key else "Not set")

    print("========================================")
    print("            ANYCODEX STATUS             ")
    print("========================================")
    if provider_id == "openai":
        print("  Active Mode : 🟢 CHATGPT PLUS (Native OpenAI)")
        print(f"  Model       : {model}")
        print("  Quotas/Usage: Managed by OpenAI account")
    else:
        print(f"  Active Mode : 🔵 {prov.get('name', provider_id).upper()}")
        print(f"  Model       : {model}")
        print(f"  Base URL    : {prov.get('base_url', 'Default')}")
        print(f"  API Key     : {key_preview}")
        print("  Gateway     : Running on 127.0.0.1:8765")
        print("  CUA & Tools : Fully Enabled")
    print("========================================")
    print("Quick Commands:")
    print("  anycodex use <provider>      -> Switch active provider (e.g. meta, deepseek, groq, ollama)")
    print("  anycodex use openai          -> Switch back to official ChatGPT Plus")
    print("  anycodex set-key <prov> <key>-> Update API key instantly")
    print("  anycodex add                 -> Add custom OpenAI-compatible endpoint")
    print("  anycodex list                -> List all configured providers")

def list_providers():
    cfg = load_providers_config()
    active = cfg.get("active_provider", "meta")
    print("\nConfigured Providers:")
    print("  * openai (Native ChatGPT Plus)")
    for pid, p in cfg.get("providers", {}).items():
        is_active = " [ACTIVE]" if pid == active else ""
        print(f"  • {pid:<12} : {p.get('name')} (Model: {p.get('model')}){is_active}")
    print("\nSwitch with: anycodex use <name>")

def main():
    if len(sys.argv) < 2:
        print_status()
        return

    cmd = sys.argv[1].lower()
    if cmd in ("use", "switch"):
        if len(sys.argv) < 3:
            print("Usage: anycodex use [openai|meta|deepseek|groq|ollama|<custom>]")
            return
        target = sys.argv[2].lower()
        if target in ("openai", "chatgpt", "plus"):
            switch_to_openai()
        else:
            switch_to_custom(target)
    elif cmd in ("set-key", "key", "setkey"):
        if len(sys.argv) == 3:
            # anycodex set-key <KEY> (defaults to active provider or meta)
            cfg = load_providers_config()
            target = cfg.get("active_provider", "meta")
            set_key(target, sys.argv[2])
        elif len(sys.argv) >= 4:
            # anycodex set-key <provider> <KEY>
            set_key(sys.argv[2], sys.argv[3])
        else:
            print("Usage: anycodex set-key [provider] <NEW_API_KEY>")
    elif cmd in ("add", "add-provider", "new"):
        add_provider()
    elif cmd in ("list", "ls", "all"):
        list_providers()
    elif cmd in ("status", "info"):
        print_status()
    elif cmd in ("restart", "reload"):
        restart_adapter()
        print("✅ Adapter restarted.")
    elif cmd in ("meta", "usemeta"):
        switch_to_custom("meta")
    elif cmd in ("openai", "useopenai"):
        switch_to_openai()
    else:
        print(f"Unknown command: {cmd}")
        print("Run 'anycodex' without arguments for help.")

if __name__ == "__main__":
    main()
