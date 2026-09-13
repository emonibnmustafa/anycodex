# ⚡ AnyCodex

> **Run ANY LLM (Meta Muse Spark, DeepSeek, Groq, Ollama, OpenRouter) inside OpenAI Codex & ChatGPT Desktop with 100% Tool Parity — Full Computer Use (CUA), Code Mode, and Zero Subscription Limits.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform: macOS & Windows](https://img.shields.io/badge/Platform-macOS%20%7C%20Windows-lightgrey.svg)]()
[![Tool Parity: 100%](https://img.shields.io/badge/Tool%20Parity-100%25%20CUA%20%2B%20Code-brightgreen.svg)]()
[![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-success.svg)]()

---

## 🌟 Why AnyCodex?

OpenAI Codex and the official ChatGPT Desktop application are revolutionary tools for coding, pairing, and automating your screen with **Computer Use**. However:
- OpenAI rate limits and usage caps quickly run out during heavy programming sessions.
- Developers often want to use **unlimited free models** like **Meta Muse Spark**, ultra-fast models like **Groq**, cost-effective powerhouses like **DeepSeek**, or 100% private local offline models via **Ollama**.
- Until now, switching providers broke tools, corrupted thread histories, or required sacrificing desktop automation.

**AnyCodex** completely solves this. It functions as an ultra-fast, local translation gateway and profile manager that connects Codex Desktop to **any OpenAI-compatible LLM endpoint** with:
- 🖱️ **100% Full Computer Use (CUA) Parity**: Real mouse clicks, keystrokes, screenshots, window control, and browser automation.
- 💻 **100% Code Mode Parity**: Instant local bash execution, terminal interaction, file editing, and test verification.
- 🪟 **Side-by-Side Dual-App Mode**: Run official ChatGPT Plus (OpenAI) and AnyCodex at the exact same time without profile or session conflicts.
- 🔄 **Instant 1-Command Hot-Switching**: Seamlessly toggle between providers (`anycodex use meta`, `anycodex use deepseek`, `anycodex use openai`).
- 🔒 **100% Local & Zero Telemetry**: Operates exclusively on `127.0.0.1:8765`. Your API keys, code, and prompts never touch third-party servers.

---

## 🚀 1-Command Quick Installation

### 🍏 macOS (Terminal)
Run this single command in your Terminal:

```bash
curl -fsSL https://raw.githubusercontent.com/emonibnmustafa/anycodex/main/install.sh | bash
```

### 🪟 Windows PC (PowerShell)
Open PowerShell as Administrator and run:

```powershell
irm https://raw.githubusercontent.com/emonibnmustafa/anycodex/main/install.ps1 | iex
```

> **What the installer does automatically:**
> 1. Sets up the local AnyCodex gateway in `~/.codex/anycodex`.
> 2. Starts the zero-config background daemon (`launchd` on macOS, Startup service on Windows).
> 3. Adds fast CLI shortcuts (`anycodex`, `usemeta`, `useopenai`).
> 4. Offers to create the standalone **Side-by-Side App** so you can run ChatGPT Plus and AnyCodex concurrently!

---

## 🪟 Side-by-Side Dual-App Mode (The Superpower)

Want to keep your official ChatGPT Plus app for OpenAI models, while running a dedicated second app for unlimited free Meta Muse Spark or DeepSeek?

Run:
```bash
anycodex dual-app
```

| App | Location | Model Used | Profile & Storage | Best For |
| :--- | :--- | :--- | :--- | :--- |
| **ChatGPT (Official)** | Applications / Start Menu | OpenAI `GPT-5.6 Sol` | Default (`~/.codex`) | Official Plus account tasks |
| **AnyCodex** | Applications / Desktop | `Meta Muse Spark` / Custom | Isolated (`~/.codex-anycodex`) | Unlimited free heavy coding & long pairing sessions |

- **Zero Extra Storage:** On macOS, utilizes APFS Copy-on-Write cloning (0 MB extra disk space).
- **Independent Profiles:** Separate Chromium user data directories and separate SQLite databases ensure windows, cookies, and chat threads NEVER collide.
- **Keep Both Open:** Run both apps side-by-side simultaneously on your screen!

---

## 🕹️ CLI Command Reference

AnyCodex comes with an intuitive, cross-platform CLI:

| Command | Shortcut | Description |
| :--- | :--- | :--- |
| `anycodex status` | — | View current active provider, base URL, model, and gateway health |
| `anycodex dual-app` | — | Setup or refresh the standalone Side-by-Side desktop application |
| `anycodex use meta` | `usemeta` | Switch to Meta Muse Spark (Unlimited Free for contributors) |
| `anycodex use <provider>` | — | Switch to any configured provider (`deepseek`, `groq`, `ollama`, etc.) |
| `anycodex use openai` | `useopenai` | Revert to official ChatGPT Plus (OpenAI) native mode |
| `anycodex set-key <prov> <key>` | `setmeta <key>` | Update the API key for a provider instantly |
| `anycodex add` | — | Interactive prompt to register any custom base URL & model |
| `anycodex list` | — | List all configured providers |
| `anycodex restart` | — | Restart the local background adapter gateway |

---

## 🌐 Supported Providers Out of the Box

### 1. Meta AI (Muse Spark)
- **Model:** `muse-spark-1.3-contributor`
- **Key Feature:** Unlimited free usage with full CUA desktop automation.
- **Setup:**
  ```bash
  anycodex set-key meta "YOUR_META_KEY"
  anycodex use meta
  ```

### 2. DeepSeek (DeepSeek Coder / V3)
- **Model:** `deepseek-coder`
- **Base URL:** `https://api.deepseek.com`
- **Setup:**
  ```bash
  anycodex set-key deepseek "sk-YOUR_DEEPSEEK_KEY"
  anycodex use deepseek
  ```

### 3. Groq (Ultra-Low Latency)
- **Model:** `llama-3.3-70b-versatile`
- **Base URL:** `https://api.groq.com/openai`
- **Setup:**
  ```bash
  anycodex set-key groq "gsk_YOUR_GROQ_KEY"
  anycodex use groq
  ```

### 4. Local Ollama (100% Offline & Private)
- **Model:** `qwen2.5-coder:latest` (or any installed model)
- **Base URL:** `http://127.0.0.1:11434`
- **Setup:**
  ```bash
  ollama run qwen2.5-coder
  anycodex use ollama
  ```

### 5. OpenRouter / Custom Endpoints
- Connect any OpenAI-compatible API (vLLM, LMStudio, Mistral, Together AI, Claude via OpenRouter):
  ```bash
  anycodex add
  ```

---

## 🏗️ How It Works (Architecture)

```
┌────────────────────────────────────────────────────────┐
│               ChatGPT Desktop / Codex App              │
│       Code Mode (exec) + Computer Use (CUA) Tools      │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP / SSE Stream
                           ▼
┌────────────────────────────────────────────────────────┐
│           AnyCodex Gateway (127.0.0.1:8765)        │
│  • Bidirectional Tool Translation (exec <-> CUA)       │
│  • Strict-Mode Schema Flattening & Normalization       │
│  • 64-Character Tool Name Length Clamping & Mapping    │
│  • Real-time SSE Stream Event Translation              │
└──────────────────────────┬─────────────────────────────┘
                           │ Standard OpenAI-Compatible API
                           ▼
┌────────────────────────────────────────────────────────┐
│                  Upstream Provider                     │
│    Meta AI | DeepSeek | Groq | Ollama | OpenRouter     │
└────────────────────────────────────────────────────────┘
```

### Key Technical Innovations
1. **Bidirectional Code Mode Bridge:** Translates Codex's internal V8 isolate `custom_tool_call` on `exec` into standard OpenAPI function calls, and maps upstream results back to Codex flawlessly.
2. **Strict-Mode Schema Sanitizer:** Upstream function-calling validators (like Meta's) reject combiners like `oneOf`/`anyOf`/`allOf` at the root parameters level. AnyCodex flattens and normalizes schemas into clean objects.
3. **Deterministic 64-Character Name Mapper:** Codex plugins often emit 70–90 character tool names. AnyCodex safely clamps and bi-directionally maps names under the 64-character limit.

---

## 🗑️ Uninstallation

If you ever wish to completely remove AnyCodex:

### macOS:
```bash
curl -fsSL https://raw.githubusercontent.com/emonibnmustafa/anycodex/main/uninstall.sh | bash
```

### Windows:
```powershell
irm https://raw.githubusercontent.com/emonibnmustafa/anycodex/main/uninstall.ps1 | iex
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an Issue for new provider presets, feature requests, or bug reports.

## 📄 License

This project is licensed under the [MIT License](LICENSE).
