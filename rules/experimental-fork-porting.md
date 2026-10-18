---
trigger: model_decision
description: "Guidelines and invariants for cherry-picking and porting features or fixes from experimental forks/branches into production Amni repositories."
---

# Experimental Fork & Feature Branch Porting Standards

When porting features, performance optimizations, or bug fixes from experimental forks or branches (e.g., between `AmniQuest` and `AmniShield`, or experimental branch to main):

---

## 1. Single-Source ViewModel Invariant
- Never duplicate ViewModels across build flavors (`src/play` vs `src/fdroid`).
- All unified ViewModels MUST reside in `app/src/main/java` or `app/src/main/kotlin`.
- Flavor source sets (`src/play`, `src/fdroid`) should only contain flavor-specific bridges, dependency injection modules, or license validators.
- Defining ViewModels in flavor directories causes KSP duplicate symbol collisions, build failures, and architectural divergence.

---

## 2. Windows Multi-Drive KSP & Gradle Safety
- On Windows systems with multiple drives (e.g. repository on `D:\` and Gradle cache on `C:\Users\...`):
  - KSP incremental compilation caches can encounter drive boundary resolution mismatches.
  - When porting build configurations or KSP plugins, verify builds with `./gradlew clean` and `./gradlew assembleRelease` to confirm clean cache generation.

---

## 3. Strict Store & FOSS Flavor Separation
- `play` / `playstore` flavor: GMS dependencies, Play Billing, Stripe Checkout integration, Firebase Crashlytics (if configured).
- `fdroid` flavor: Strictly FOSS. Zero Google Play services, zero proprietary analytics, zero closed SDKs.
- License validation must share the common cryptographic domain model (`LicenseValidator` via ECDSA NIST P-256) while allowing flavor-specific acquisition mechanisms.

---

## 4. Release Validation Gate (`lintVital`)
- Always execute `./gradlew lintVitalRelease` (or flavor equivalents like `lintVitalPlaystoreRelease`) before tagging or finalizing distribution artifacts.
- Look out for XML namespace declaration errors (`xmlns:app="http://schemas.android.com/apk/res-auto"`) in vector drawables or layout resources, which pass debug builds but break `lintVital`.

---

## 5. Universal Zero Emoji Policy
- Never carry over UTF-8 emojis or unicode pictographs from experimental code, comments, or documentation into production repositories.

