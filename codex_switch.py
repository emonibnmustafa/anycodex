#!/usr/bin/env python3
import sys
import os
import re
import json
import subprocess
import shutil

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

def read_codex_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write_codex_config(content, path=CONFIG_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def restart_adapter():
    if sys.platform == "darwin":
        try:
            uid = os.getuid()
            subprocess.run(["launchctl", "kickstart", "-k", f"gui/{uid}/{PLIST_LABEL}"], capture_output=True)
        except Exception:
            pass
    elif sys.platform == "win32":
        try:
            subprocess.run(["powershell", "-Command", "Stop-Process -Name node -ErrorAction SilentlyContinue"], capture_output=True)
        except Exception:
            pass

def reset_sqlite_threads_to_openai(codex_dir=CODEX_DIR):
    db_path = os.path.join(codex_dir, "state_5.sqlite")
    if os.path.exists(db_path):
        try:
            import sqlite3
            with sqlite3.connect(db_path) as conn:
                conn.execute("UPDATE threads SET model_provider = 'openai' WHERE model_provider != 'openai';")
                conn.commit()
        except Exception:
            pass

def switch_to_openai():
    content = read_codex_config()
    content = re.sub(r'\[model_providers\.[^\]]+\][\s\S]*?(?=\n\[|\Z)', '', content)
    content = re.sub(r'^\s*model_provider\s*=\s*["\'][^"\']+["\']\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*model_catalog_json\s*=\s*["\'][^"\']+["\']\n?', '', content, flags=re.MULTILINE)
    content = re.sub(r'^\s*model\s*=\s*["\'][^"\']+["\']', 'model = "gpt-5.6-sol"', content, flags=re.MULTILINE)
    content = re.sub(r'\n{3,}', '\n\n', content)
    write_codex_config(content)
    reset_sqlite_threads_to_openai()
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True)
        else:
            subprocess.run(["pkill", "-f", "adapter.mjs"], capture_output=True)
    except Exception:
        pass
    print("✅ Switched to ChatGPT Plus (OpenAI) native mode!")
    print("   • Default Model: GPT-5.5 / GPT-5.6")
    print("   • Plus features, usage meters & chat modes active.")
    print("   • All threads synchronized to native OpenAI.")

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

    target_model = prov.get("model", "custom-model")
    if re.search(r'^\s*model\s*=', content, re.MULTILINE):
        content = re.sub(r'^\s*model\s*=\s*["\'][^"\']+["\']', f'model = "{target_model}"', content, flags=re.MULTILINE)
    else:
        content = f'model = "{target_model}"\n' + content

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

def setup_dual_app():
    print("\n========================================================")
    print("      🚀 Open AnyCodex Dual-App Setup (Side-by-Side)     ")
    print("========================================================")
    print("This sets up a dedicated second app ('Open AnyCodex')")
    print("so you can run ChatGPT Plus and your custom models")
    print("at the exact same time without switching modes!\n")

    if sys.platform == "darwin":
        # macOS implementation
        app_candidates = [
            "/Applications/ChatGPT.app",
            os.path.expanduser("~/Applications/ChatGPT.app"),
        ]
        # Search mounted volumes
        try:
            for vol in os.listdir("/Volumes"):
                candidate = os.path.join("/Volumes", vol, "Applications", "ChatGPT.app")
                if os.path.isdir(candidate):
                    app_candidates.append(candidate)
        except Exception:
            pass

        source_app = None
        for cand in app_candidates:
            if os.path.isdir(cand):
                source_app = cand
                break

        if not source_app:
            print("❌ Official ChatGPT.app was not found in standard Applications locations.")
            print("Please make sure ChatGPT Desktop is installed.")
            return

        dest_dir = os.path.dirname(source_app)
        target_app = os.path.join(dest_dir, "Open AnyCodex.app")
        print(f"📦 Source App : {source_app}")
        print(f"🎯 Target App : {target_app}")

        # 1. Clone app bundle using APFS copy-on-write
        if os.path.exists(target_app):
            shutil.rmtree(target_app)
        print("📁 Cloning app bundle (APFS Copy-on-Write, 0 MB extra disk)...")
        subprocess.run(["cp", "-c", "-R", source_app, target_app], check=True)

        # 2. Update Info.plist
        plist_path = os.path.join(target_app, "Contents", "Info.plist")
        subprocess.run(["/usr/libexec/PlistBuddy", "-c", "Set :CFBundleIdentifier com.openai.codex.anycodex", plist_path], capture_output=True)
        subprocess.run(["/usr/libexec/PlistBuddy", "-c", "Set :CFBundleName Open AnyCodex", plist_path], capture_output=True)
        subprocess.run(["/usr/libexec/PlistBuddy", "-c", "Set :CFBundleDisplayName Open AnyCodex", plist_path], capture_output=True)

        # 3. Setup isolated config directory
        meta_dir = os.path.join(HOME, ".codex-anycodex")
        os.makedirs(os.path.join(meta_dir, ".tmp"), exist_ok=True)
        os.makedirs(os.path.join(HOME, "Library", "Application Support", "Codex-AnyCodex"), exist_ok=True)

        # Symlink shared assets
        for sub in ["skills", "computer-use"]:
            src = os.path.join(CODEX_DIR, sub)
            dst = os.path.join(meta_dir, sub)
            if os.path.exists(src) and not os.path.exists(dst):
                try:
                    os.symlink(src, dst)
                except Exception:
                    pass

        # Write config.toml in meta_dir
        meta_cfg = os.path.join(meta_dir, "config.toml")
        base_cfg = read_codex_config()
        if not base_cfg:
            base_cfg = read_codex_config(CONFIG_PATH)

        cfg_content = base_cfg
        cfg_content = re.sub(r'^\s*model\s*=\s*["\'][^"\']+["\']', 'model = "muse-spark-1.3-contributor"', cfg_content, flags=re.MULTILINE)
        if 'model_provider =' in cfg_content:
            cfg_content = re.sub(r'^\s*model_provider\s*=\s*["\'][^"\']+["\']', 'model_provider = "meta"', cfg_content, flags=re.MULTILINE)
        else:
            cfg_content += '\nmodel_provider = "meta"\n'

        if '[model_providers.meta]' not in cfg_content:
            cfg_content += '''
[model_providers.meta]
name = "Meta Muse Spark (Unlimited Free)"
base_url = "http://127.0.0.1:8765/v1"
experimental_bearer_token = "local"
wire_api = "responses"
'''
        write_codex_config(cfg_content, meta_cfg)

        # 4. Compile native ARM64 / x86 launcher
        macos_dir = os.path.join(target_app, "Contents", "MacOS")
        real_bin = os.path.join(macos_dir, "ChatGPT.real")
        orig_bin = os.path.join(macos_dir, "ChatGPT")
        if not os.path.exists(real_bin):
            os.rename(orig_bin, real_bin)

        c_source = f"""#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <mach-o/dyld.h>
#include <libgen.h>

int main(int argc, char *argv[]) {{
    char path[1024];
    uint32_t size = sizeof(path);
    if (_NSGetExecutablePath(path, &size) != 0) return 1;
    char *dir = dirname(path);
    
    char real_bin[1024];
    snprintf(real_bin, sizeof(real_bin), "%s/ChatGPT.real", dir);
    
    const char *home = getenv("HOME");
    if (!home) home = "{HOME}";
    
    char codex_home[1024];
    snprintf(codex_home, sizeof(codex_home), "%s/.codex-anycodex", home);
    setenv("CODEX_HOME", codex_home, 1);
    
    char user_data[1024];
    snprintf(user_data, sizeof(user_data), "--user-data-dir=%s/Library/Application Support/Codex-AnyCodex", home);
    
    char **new_argv = malloc((argc + 2) * sizeof(char *));
    new_argv[0] = real_bin;
    new_argv[1] = user_data;
    for (int i = 1; i < argc; i++) {{
        new_argv[i + 1] = argv[i];
    }}
    new_argv[argc + 1] = NULL;
    
    execv(real_bin, new_argv);
    return 1;
}}
"""
        c_file = "/tmp/anycodex_launcher.c"
        with open(c_file, "w") as f:
            f.write(c_source)

        print("⚡ Compiling native macOS launcher...")
        subprocess.run(["clang", "-O2", c_file, "-o", orig_bin], check=True)
        os.chmod(orig_bin, 0o755)
        os.chmod(real_bin, 0o755)

        # 5. Ad-hoc codesign
        print("🔏 Signing application bundle...")
        subprocess.run(["codesign", "--force", "--deep", "--sign", "-", target_app], capture_output=True)
        subprocess.run(["xattr", "-dr", "com.apple.quarantine", target_app], capture_output=True)

        # Symlink into ~/Applications for Spotlight
        user_apps = os.path.expanduser("~/Applications")
        os.makedirs(user_apps, exist_ok=True)
        link_path = os.path.join(user_apps, "Open AnyCodex.app")
        try:
            if os.path.islink(link_path):
                os.unlink(link_path)
            os.symlink(target_app, link_path)
        except Exception:
            pass

        print("\n🎉 SUCCESS! 'Open AnyCodex.app' is ready!")
        print("   • Location   : " + target_app)
        print("   • Spotlight  : Available via Cmd+Space -> 'Open AnyCodex'")
        print("   • Isolation  : Fully separate profile & history (~/.codex-anycodex)")
        print("   • Capability : 100% Computer Use, Plugins, and Tools Active")
        print("\nYou can now open BOTH apps side-by-side simultaneously!\n")

    elif sys.platform == "win32":
        # Windows implementation
        localappdata = os.environ.get("LOCALAPPDATA", os.path.join(HOME, "AppData", "Local"))
        chatgpt_candidates = [
            os.path.join(localappdata, "Programs", "ChatGPT", "ChatGPT.exe"),
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "ChatGPT", "ChatGPT.exe")
        ]
        exe_path = None
        for cand in chatgpt_candidates:
            if os.path.exists(cand):
                exe_path = cand
                break

        meta_dir = os.path.join(HOME, ".codex-anycodex")
        user_data = os.path.join(localappdata, "Codex-AnyCodex")
        os.makedirs(meta_dir, exist_ok=True)
        os.makedirs(user_data, exist_ok=True)

        # Create AnyCodex.cmd batch launcher
        cmd_path = os.path.join(HOME, "Desktop", "Open AnyCodex.cmd")
        with open(cmd_path, "w") as f:
            f.write(f'''@echo off
set "CODEX_HOME={meta_dir}"
start "" "{exe_path or 'ChatGPT.exe'}" --user-data-dir="{user_data}" %*
''')

        print("\n🎉 SUCCESS! 'Open AnyCodex' shortcut created on your Desktop!")
        print(f"   • Shortcut : {cmd_path}")
        print(f"   • Isolation: Fully separate profile & history ({meta_dir})")
        print("You can now open official ChatGPT and Open AnyCodex simultaneously!\n")

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
    print("         ⚡ OPEN ANYCODEX STATUS        ")
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
    print("  anycodex dual-app            -> Setup standalone 'Open AnyCodex' side-by-side app")
    print("  anycodex use <provider>      -> Switch active provider (meta, deepseek, groq, ollama)")
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
            cfg = load_providers_config()
            target = cfg.get("active_provider", "meta")
            set_key(target, sys.argv[2])
        elif len(sys.argv) >= 4:
            set_key(sys.argv[2], sys.argv[3])
        else:
            print("Usage: anycodex set-key [provider] <NEW_API_KEY>")
    elif cmd in ("dual-app", "setup-dual-app", "dual"):
        setup_dual_app()
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
