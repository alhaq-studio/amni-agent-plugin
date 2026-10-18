# Amni Ecosystem Master Agent Plugin (`amni-ecosystem`)

Official multi-platform agent plugin and developer framework for the **Amni Product Family** (`AmniShield`, `AmniBlur`, and `AmniQuest`), maintained by **Alhaq Studio** ([alhaq.uk](https://alhaq.uk)).

---

## 1. Overview

The `amni-ecosystem` plugin provides unified architectural standards, deterministic lifecycle guardrails, on-demand domain skills, and Model Context Protocol (MCP) servers across all AI coding assistants:
- **Google Antigravity IDE & CLI (`agy`)**
- **Anthropic Claude Code**
- **VS Code & GitHub Copilot Agent Plugins**
- **OpenAI Codex CLI & Cloud Agents**

---

## 2. Core Features

- **Multi-Manifest Standard**: Dual support via `plugin.json` (Google Antigravity) and `.claude-plugin/plugin.json` (Claude Code & VS Code Copilot).
- **Zero-Emoji Deterministic Gatekeeper**: Python hook inspecting in-memory edits and git commits to strictly prevent UTF-8 emojis in production code, UI, strings, comments, and logs.
- **Single-Source ViewModel Invariant**: Prevents duplicate ViewModels across Android flavor source sets (`src/play` and `src/fdroid`), preventing KSP duplicate class collisions.
- **Packaged Amni Skills**:
  - `android-local-ai-onnx`: SigLIP 2 zero-shot vision classification, SentencePiece C++ JNI, 16 KB page memory alignment, multi-precision tensor extraction, and WorkManager downloads.
  - `android-fullstack-dev`: Modern Jetpack Compose, Material 3, Accessibility node inspection recycling, Shizuku integration, and Room DB.
  - `security-compliance`: ECDSA NIST P-256 cryptographic offline licensing, zero-knowledge privacy auditing, ProGuard/R8 obfuscation.
  - `stripe-payments`: Stripe Checkout, subscription billing, and Supabase Edge Function webhook handlers.
  - `supabase-backend`: Edge Functions (Deno runtime), PostgreSQL modeling, and Row Level Security (RLS).
  - `marketing-growth`: ASO, store copy, release notes, and community updates without emojis.
- **Preconfigured MCP Tooling**: Native server configurations for Supabase, Stripe CLI, and Dart/Flutter.

---

## 3. Quick Installation

### Option A: One-Line Installer (Recommended for Team & Developers)

#### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/alhaq-studio/amni-agent-plugin/main/scripts/install.ps1 | iex
```

#### macOS & Linux (Bash)
```bash
curl -fsSL https://raw.githubusercontent.com/alhaq-studio/amni-agent-plugin/main/scripts/install.sh | bash
```

The script automatically clones or updates the repository to `~/.agents/plugins/amni-ecosystem/` and registers it in your local agent configuration.

---

### Option B: Manual Installation by Platform

#### 1. Google Antigravity (`agy` & IDE)
Register the plugin path in `~/.gemini/config/plugins.json`:
```json
{
  "entries": [
    { "path": "~/.agents/plugins/amni-ecosystem" }
  ]
}
```

#### 2. Anthropic Claude Code
Install the plugin directly using the Claude CLI:
```bash
claude plugin install alhaq-studio/amni-agent-plugin
```
Or symlink the folder into `~/.claude/plugins/amni-ecosystem`.

#### 3. VS Code & GitHub Copilot
Enable agent plugins in VS Code `settings.json`:
```json
{
  "chat.useAgentsMdFile": true,
  "chat.plugins.enabled": true,
  "github.copilot.chat.codeGeneration.useInstructionFiles": true
}
```
Clone or link the repository into `.vscode/agent-plugins/amni-ecosystem` or your user plugins folder.

---

## 4. MCP Server Setup & Environment Variables

The plugin includes preconfigured MCP servers in `mcp_config.json` and `.claude-plugin/mcp.json`. 

To activate them, set the required environment variables in your local shell profile (`.bashrc`, `.zshrc`, or Windows Environment Variables):

### Supabase MCP Server
Provides schema exploration, database migrations, and SQL execution.
- `SUPABASE_URL`: Your Supabase project URL (e.g. `https://xyzcompany.supabase.co`).
- `SUPABASE_SERVICE_ROLE_KEY`: Your Supabase service role secret key.

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="your-service-role-key"
```

### Stripe CLI MCP Server
Provides real-time event listening and webhook testing.
1. Install the official Stripe CLI.
2. Authenticate locally:
   ```bash
   stripe login
   ```

### Dart / Flutter MCP Server
Provides semantic Dart analysis and code fixes. Requires the Dart SDK to be present in your system `PATH`.

---

## 5. Wiring Repositories to the Central Plugin

To connect any project repository (e.g., `AmniQuest`, `AmniShield-Android`, `AmniBlur-Android`) to this central plugin, add a 40-line `AGENTS.md` and a `.agents/rules.json` file to the root of your project:

### `.agents/rules.json`
```json
{
  "inherits": [
    { "path": "~/.agents/plugins/amni-ecosystem/rules/AGENTS.md" }
  ]
}
```

### `AGENTS.md`
```markdown
# Project Guidelines

## Mandatory Skill & Rule Triggers
- BEFORE modifying JNI, CMake, ONNX, LiteRT -> MUST activate android-local-ai-onnx skill.
- BEFORE modifying play or fdroid source sets -> MUST check single-source ViewModel rule.
- BEFORE modifying ECDSA licensing or Supabase RLS -> MUST activate security-compliance skill.
```

---

## 6. Development & Verification

Run the built-in deterministic verification suite locally:

```bash
# Check zero emoji compliance across all files
python hooks/scripts/check_no_emojis.py .

# Verify single-source ViewModels
python hooks/scripts/verify_flavor_sources.py --stop-check
```

---

## 7. License

Licensed under the [Apache License, Version 2.0](LICENSE). Copyright 2026 Alhaq Studio (alhaq.uk).
