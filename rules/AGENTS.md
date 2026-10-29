# Amni Ecosystem Unified Instructions (`AGENTS.md`)

This baseline instruction file is the unified source of truth for the entire **Amni Product Family** across Google Antigravity, Anthropic Claude Code, OpenAI Codex, and GitHub Copilot.

---

## 1. Amni Product Family Ecosystem Matrix

### AmniShield Suite (App, Content & Distraction Blocking)
1. **`AmniShield-Android`** (`d:\PROJECTS\Amni\AmniShield-Android` / `/media/habib/Dev/PROJECTS/AmniShield/AmniShield-Android`):
   - Kotlin, Jetpack Compose, Material 3, Accessibility Service node inspection, synchronized hybrid persistence (`AmniShieldRuleDatabase.kt`, `AmniShieldDataStore.kt`, `SavedPreferencesLoader.kt`), isolated EncryptedSharedPreferences (`SecureKeyStore.kt`).
   - Presentation: Dual-Host (`MainActivity.kt` 4 XML tabs + `FragmentActivity.kt` 18 sub-screens via `FragmentDestination.kt`) alongside pure-Compose adaptive shell `AmniShieldAdaptiveApp.kt` mounted via `mountAdaptiveComposeShell()`.
   - Blocker Pipeline Priority: P0: `AntiUninstallDetector` -> P1: `FocusModeBlocker` -> P2: `WebsiteBlockerDetector` -> P3: `AppBlocker` -> P4: `KeywordBlocker` & `ReelBlocker` (`Channel.CONFLATED` on `Dispatchers.Default`).
   - Current Version: `0.3.5 (2026.10.21)` / `versionCode 145` (Milestones 0.3.2, 0.3.3, 0.3.4 & 0.3.5 completed; Active Milestone: `v0.3.6` / `v1.0`).
   - Core Features: App & URL blocker, keyword filter, focus mode ("Block Selected" default), Reels blocker, ECDSA licensing, diagnostic CrashLogger.
   - Scope Boundaries: Screen visual blur/censoring belongs to `AmniBlur`; VPN DNS packet sinkhole belongs to `AmniGuardFirewall`.
2. **`AmniShield-Windows`** (`/media/habib/Dev/PROJECTS/AmniShield/AmniShield-Windows`):
   - Flutter, Dart, Windows Desktop API, SQLite.
   - Core Features: Desktop focus utility, process monitor, hosts-file URL filter.
3. **`AmniShield-Extension`** (`/media/habib/Dev/PROJECTS/AmniShield/AmniShield-Extension`):
   - JavaScript / TypeScript, WebExtensions API, Manifest V3.
   - Core Features: Browser web filtering, keyword blocking, rule enforcement.
4. **`AmniShield-site`** (`/media/habib/Dev/PROJECTS/AmniShield/AmniShield-site`):
   - Next.js / HTML / Vanilla CSS, Supabase Edge Functions.
   - Core Features: Web portal, pricing, Stripe checkout, user license management.

### AmniBlur & AmniGaze Suite (AI Visual Content Moderation & Screen Censoring)
5. **`AmniBlur-Android`** (`/media/habib/Dev/PROJECTS/AmniBlur/AmniBlur-Android`):
   - Kotlin, Jetpack Compose, LiteRT (TensorFlow Lite), MediaProjection API, System Service Overlay.
   - Core Features: Real-time on-device screen censoring (blur, mosaic, frosted glass) via TFLite vision models.
6. **`AmniBlur-Extention`** (`/media/habib/Dev/PROJECTS/AmniBlur/AmniBlur-Extention`):
   - JavaScript / Node.js, TensorFlow.js (WASM/WebGL), Manifest V3, Content Scripts.
   - Core Features: Real-time AI browser image & video frame moderation.

### AmniQuest (Habit Gamification & Offline AI Verification)
7. **`AmniQuest`** (`d:\PROJECTS\Amni\AmniQuest`):
   - Kotlin, Jetpack Compose, ONNX Runtime Mobile, SentencePiece C++ JNI, Room SQLite.
   - Core Features: Minimalist launcher, offline photo habit verification, zero-shot SigLIP 2 vision classification.

---

## 2. Fundamental System Principles

1. **Zero-Knowledge & On-Device Processing**:
   - All visual content moderation (LiteRT on Android, TensorFlow.js in Browser Extension, ONNX Runtime in AmniQuest) MUST execute 100% locally on-device.
   - Zero personal data, telemetry, screen frames, or captured images are ever transmitted to remote servers.
2. **Cryptographic Offline-First Licensing**:
   - Pro/Supporter Pass features utilize offline cryptographic NIST P-256 ECDSA public key verification (`SHA256withECDSA`).
   - Users can activate their license key completely offline without requiring network connectivity.
3. **Open-Source Core + Supporter Pass Model**:
   - Core filtering and censoring remain 100% Free and Open-Source forever.
   - Supporter Passes (Monthly $4.99 / Annual $39.99) unlock optional cross-device cloud sync via Supabase.
4. **Store & FOSS Compliance**:
   - Maintain strict build flavor separation (`playstore` with GMS/Stripe checkout vs `fdroid` FOSS flavor strictly free of proprietary SDKs).
5. **Brand Consistency**:
   - The ecosystem brand is strictly "Amni" (with an "i": `AmniShield`, `AmniBlur`, `AmniQuest`, `amni-ecosystem`).

---

## 3. Mandatory Skill & Rule Triggers

- BEFORE modifying JNI, CMake, ONNX, LiteRT, or Tokenizers -> MUST activate `android-local-ai-onnx` skill.
- BEFORE modifying `play` or `fdroid` source sets -> MUST check `experimental-fork-porting` rule (never duplicate ViewModels across flavors; unify in `src/main`).
- BEFORE modifying ECDSA licensing, ProGuard, or Supabase RLS -> MUST activate `security-compliance` skill.
- BEFORE modifying Stripe subscriptions, checkout sessions, or webhooks -> MUST activate `stripe-payments` skill.
- BEFORE modifying Supabase Edge Functions, database migrations, or schemas -> MUST activate `supabase-backend` skill.
- BEFORE drafting store copy, release notes, changelogs, or ASO -> MUST activate `marketing-growth` skill.
- AFTER completing any feature or bug fix altering module structure -> MUST run `sync-docs` check on `ARCHITECTURE.md`.

---

## 4. STRICT UNIVERSAL UI & CODE QUALITY RULE: NO EMOJIS IN CODE OR UI

1. **ZERO EMOJI POLICY**: Do NOT use UTF-8 emojis or emoji-based unicode characters anywhere in code, UI layouts, components, strings, comments, logs, or commit messages across ANY project type (Android, Web/React, Desktop, VS Code extensions, or CLI).
2. **USE PRODUCTION ICON LIBRARIES ONLY**:
   - **Web & React (TSX/JSX/HTML)**: Use Lucide React (`lucide-react`), Material UI Icons (`@mui/icons-material`), FontAwesome, or inline SVGs.
   - **Android (Kotlin/Compose/XML)**: Use Vector Drawables (`ic_*.xml`), Material Symbols, or Compose `ImageVector`.
   - **VS Code Extensions & Webviews**: Use official Codicons (`@vscode/codicons`) or inline SVGs.
   - **Desktop & CLI (Python/C++/Electron)**: Use standard UI icon fonts, native framework drawables, or clean plain-text tags (`[OK]`, `[INFO]`, `[FAIL]`, `[WARNING]`, `[ERROR]`).
3. **ACCESSIBILITY & STYLING COMPLIANCE**:
   - Icons must support theme-based color tinting (CSS variables, dynamic color, or vector tinting).
   - Icons must use explicit `aria-label` attributes or screen-reader descriptions instead of unicode strings.

