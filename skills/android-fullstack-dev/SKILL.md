---
name: android-fullstack-dev
description: >-
  Official Android Fullstack Development Skill covering Jetpack Compose, Material 3, Edge-to-Edge,
  Kotlin Coroutines/Flow, Clean Architecture, Accessibility Services, Shizuku integration, local storage
  (Room with KSP, DataStore), WorkManager resilient workers, zero-telemetry diagnostic logging, 16 KB page
  memory alignment for Android 15+, R8 minification, and multi-channel store publishing (Google Play AAB,
  F-Droid FOSS, Universal APK). Activate this skill for any Android full-stack development task.
version: 1.0.0
---

# Android Fullstack Development Skill

This skill defines modern, enterprise-grade engineering standards for building high-performance, secure, and resilient Android applications across all layers of the stack.

---

## [Architecture & Component Standards]

### 1. Presentation Layer (Jetpack Compose & Material 3)
- **Jetpack Compose Exclusive**: Build all UI with Compose. Avoid legacy XML views except when hosting specialized platform containers or widgets.
- **Material 3 Design Tokens**:
  - Use `MaterialTheme.colorScheme` and `MaterialTheme.typography` exclusively for styling.
  - Use auto-mirrored icons (`Icons.AutoMirrored.Filled.*`) for directional iconography to support RTL locales automatically.
  - Use `HorizontalDivider` instead of the deprecated `Divider`.
- **State Management & Lifecycle**:
  - Expose UI state through `StateFlow` from ViewModels.
  - Collect state in Composables using `collectAsStateWithLifecycle()` to automatically halt collection when the Composable is not in an active lifecycle state.
  - Support predictive back gestures via `PredictiveBackHandler` for smooth screen transitions.

### 2. Edge-to-Edge Architecture (Android 15+ SDK 35/36 Enforced)
Android 15 (targetSdk 35+) enforces edge-to-edge layout by default. All applications MUST handle system window insets safely:
1. **Activity Setup**: Call `enableEdgeToEdge()` before `setContent` in every Activity:
   ```kotlin
   class MainActivity : ComponentActivity() {
       override fun onCreate(savedInstanceState: Bundle?) {
           enableEdgeToEdge()
           super.onCreate(savedInstanceState)
           setContent {
               AppTheme {
                   MainScaffold()
               }
           }
       }
   }
   ```
2. **System Bar Legibility & Contrast**:
   Ensure status bar and navigation bar icon contrast is controlled dynamically using `WindowInsetsControllerCompat`:
   ```kotlin
   val view = LocalView.current
   if (!view.isInEditMode) {
       SideEffect {
           val window = (view.context as Activity).window
           val insetsController = WindowCompat.getInsetsController(window, view)
           insetsController.isAppearanceLightStatusBars = !darkTheme
           insetsController.isAppearanceLightNavigationBars = !darkTheme
       }
   }
   ```
3. **Manifest Keyboard Inset**: Configure `android:windowSoftInputMode="adjustResize"` in `AndroidManifest.xml` for all Activities displaying text inputs.
4. **Safe Inset Consumption**:
   - Use `Scaffold` and pass `innerPadding` down to scrollable containers:
   ```kotlin
   Scaffold { innerPadding ->
       LazyColumn(
           modifier = Modifier
               .fillMaxSize()
               .consumeWindowInsets(innerPadding),
           contentPadding = innerPadding
       ) {
           // Content items
       }
   }
   ```
   - For floating text fields and bottom sheets, apply `Modifier.imePadding()` to prevent the soft keyboard from obscuring input fields.
   - For camera cutouts and notch displays, apply `Modifier.displayCutoutPadding()` or consume `WindowInsets.safeDrawing`.

### 3. Domain & Data Layer (Clean Architecture)
- **Multi-Module Separation**:
  - `:app`: Presentation, ViewModels, Compose navigation, foreground services, background workers.
  - `:core`: Pure domain logic, platform managers (accessibility, audio, display), license validators, cryptographic utilities.
  - `:data`: Canonical models, Kotlinx Serialization contracts, Room entities, and DAOs.
  - `:backend`: Remote APIs, Supabase clients, cloud synchronization.
  - `:ai`: Native C++ JNI, tokenizers, ONNX/LiteRT runtime integrations.
- **Modern Local Persistence (Room 2.6+ & KSP)**:
  - Use Kotlin Symbol Processing (KSP) instead of deprecated `kapt` for Room annotation compilation: `ksp(libs.androidx.room.compiler)`.
  - Export schemas and configure auto-migrations:
    ```kotlin
    @Database(
        entities = [TaskEntity::class],
        version = 2,
        autoMigrations = [AutoMigration(from = 1, to = 2)],
        exportSchema = true
    )
    ```
  - Expose database queries as reactive `Flow<List<T>>` with SQLite foreign key cascading.
- **Preferences DataStore**: Use `Preferences DataStore` for key-value settings, theme preferences, and feature flags. Never use raw SharedPreferences on the main thread.
- **Coroutine Dispatchers**:
  - `Dispatchers.IO`: Disk persistence, file I/O, database queries, network calls.
  - `Dispatchers.Default`: CPU-intensive data transformations, JSON serialization, image processing.
  - `Dispatchers.Main`: UI state emissions and Composable event callbacks.

---

## [System Services & Accessibility (App Blocking & Filtering)]

Digital wellness and screen monitoring applications (e.g. AmniShield, Curbox) rely heavily on Android Accessibility Services and system monitoring.

### 1. Decoupled Asynchronous Event Processing
Accessibility event callbacks execute on the system main binder thread. Performing synchronous DOM walks or disk I/O in `onAccessibilityEvent` causes UI freezes and system ANRs.
- **Channel-Based Pipeline**: Route incoming events through a Kotlin `Channel<AccessibilityEvent>` with non-blocking `trySend()` and process deferred checks in a background coroutine worker:
  ```kotlin
  private val eventChannel = Channel<AccessibilityEvent>(capacity = 64)

  override fun onAccessibilityEvent(event: AccessibilityEvent?) {
      val rootNode = rootInActiveWindow ?: return
      try {
          // Priority 0: Immediate synchronous check (Anti-Uninstall)
          if (antiUninstallDetector.check(rootNode)) {
              pressHome()
              return
          }
          // Deferred asynchronous checks (Keywords, Feed Suppression)
          val eventCopy = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
              AccessibilityEvent(event!!)
          } else {
              @Suppress("DEPRECATION")
              AccessibilityEvent.obtain(event!!)
          }
          if (eventChannel.trySend(eventCopy).isFailure) {
              @Suppress("DEPRECATION")
              eventCopy.recycle()
          }
      } finally {
          // Central service exclusively owns rootNode lifecycle
          rootNode.recycle()
      }
  }
  ```

### 2. Node Lifecycle Invariant
- **Central Ownership**: The host `AccessibilityService` exclusively owns the lifecycle of `rootNode`. It MUST be recycled exactly once in the `finally` block of `onAccessibilityEvent`.
- **Sub-detector Invariant**: Interceptors, detectors, and helper functions must **NEVER** call `rootNode.recycle()`. They must only recycle child nodes that they instantiate during internal stack or queue traversals.

### 3. Chain of Responsibility & Strict Short-Circuiting
Organize blocker logic in a strict priority chain:
- **Priority 0 (Highest)**: Anti-Uninstall / Device Admin protection (Play Store, Settings App Info).
- **Priority 1**: Application Blocker & Active Focus Space.
- **Priority 2**: Website Blocker & Real-time Keyword Action Handler.
- **Priority 3**: Reel & Short-Form Content Feed Suppression.
- **Early Return**: When a higher-priority interceptor triggers a block action (`pressHome()` or launching `WarningActivity`), return immediately to abort downstream node walks.

### 4. UI Hiding & Granular Inspection (Curbox NodeFinder Pattern)
For granular UI element suppression (e.g. hiding the YouTube Shorts shelf or Instagram Explore tab while keeping direct messages functional):
- **Anchor Search**: Whenever possible, use platform batched finders (`findAccessibilityNodeInfosByViewId` or `findAccessibilityNodeInfosByText`) as an anchor to obtain a small candidate set before evaluating additional matchers (class, description, clickable).
- **Execution Budget (`onVisit`)**: Charge visited nodes against a per-frame budget to prevent infinite traversals on cyclic DOM hierarchies.
- **Immediate Candidate Recycling**: If a candidate node fails predicate matching, immediately recycle it:
  ```kotlin
  for (candidate in candidates) {
      if (matchesAll(candidate, matchers)) {
          return candidate
      } else {
          candidate.recycle()
      }
  }
  ```

### 5. Privileged Operations via Shizuku (Non-Root)
For operations requiring privileged system permissions (e.g. toggling `WRITE_SECURE_SETTINGS` to enable app-specific grayscale filters without root):
- **Dependencies**: Use official Maven coordinates `dev.rikka.shizuku:api` and `dev.rikka.shizuku:provider`.
- **One-Time Permission Grant**: Request permission via Shizuku shell (`pm grant <package> android.permission.WRITE_SECURE_SETTINGS`).
- **Grayscale / Monochromacy Mode**: Toggle without root via:
  ```kotlin
  Settings.Secure.putInt(contentResolver, "accessibility_display_daltonizer_enabled", 1)
  Settings.Secure.putInt(contentResolver, "accessibility_display_daltonizer", 0) // Monochromacy
  ```
- **Self-Healing Auto-Restart**: If OEM battery killers terminate the accessibility service, Shizuku can re-enable it via:
  `settings put secure enabled_accessibility_services <package>/<service>`

### 6. Auto Do Not Disturb (DND) State Preservation
When automating DND via `NotificationManager.setInterruptionFilter`:
- Check `NotificationManager.isNotificationPolicyAccessGranted`. If missing, direct to `Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS`.
- **State Invariant (`KEY_WAS_TURNED_ON_BY_US`)**: Record whether DND was activated by the application. Never deactivate DND when a scheduled block ends if the user had already activated DND manually.

### 7. Android 13+ Restricted Settings Handling
When users install APKs from outside Google Play (e.g. F-Droid, GitHub Releases), Android 13+ marks Accessibility and Notification Listener permissions as "Restricted Settings":
- Detect if accessibility binding is restricted.
- Guide the user with clear instructions: open `Settings.ACTION_APPLICATION_DETAILS_SETTINGS` -> tap the 3-dot overflow menu in the top right -> tap "Allow restricted settings" -> authenticate with biometric/PIN.

### 8. Strongly Typed AIDL IPC
- When exposing services across processes or external integrations, define explicit AIDL contracts (`.aidl`) and validate caller package signatures before dispatching commands.

---

## [Foreground Services & Resilient WorkManager]

### 1. Android 14/15/16 Foreground Service Types
Foreground services MUST declare explicit types in `AndroidManifest.xml` matching their runtime behavior:
```xml
<service
    android:name=".services.AppBlockerService"
    android:foregroundServiceType="dataSync|specialUse"
    android:exported="false" />
```
Declare corresponding permissions: `<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />`.

### 2. Resilient Background Workers (`WorkManager`)
- **Quota Handling**: Background tasks that download large model assets or synchronize database backups must specify:
  `setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)` to avoid silent task cancellation when system expedited quotas are exhausted.
- **HTTP Range 200 vs 206 Resilient Resumes**: Inspect server response codes during chunked downloads. If the server returns `206 Partial Content`, append to the file; if it returns `200 OK`, truncate the file and reset byte offsets to prevent file corruption.
- **Unique Work Deduplication**: Use `ExistingWorkPolicy.KEEP` to prevent multiple concurrent downloads for identical assets.

---

## [Diagnostic & Crash Logging (Zero-Telemetry Architecture)]

In privacy-first applications, crash reports and diagnostic logs must NEVER be transmitted to external servers without explicit user consent.

1. **Global Uncaught Exception Handler**:
   Install a custom `Thread.UncaughtExceptionHandler` during `Application.onCreate()` to capture fatal crashes locally.
2. **Rolling File Cache**:
   Store logs in `context.filesDir/logs/app_logs.txt`. Rotate across 5 rolling files with a strict 500 KB per-file ceiling (~2 MB total maximum footprint).
3. **PII Sanitization Pipeline**:
   All log messages MUST pass through regex redaction before writing to disk:
   - Passwords and master PINs -> `[REDACTED_SECRET]`
   - Supabase tokens, JWTs, Bearer headers -> `[REDACTED_TOKEN]`
   - Email addresses -> `[REDACTED_EMAIL]`
4. **Diagnostic Export via FileProvider**:
   Provide an in-app diagnostic viewer (`DiagnosticsScreen`) allowing users to inspect, copy, or export logs via Android `FileProvider` sharesheets.

---

## [Performance, Native NDK & Build Optimization]

### 1. 16 KB Memory Page Alignment for Android 15+ (API 35+)
Google Play requires apps targeting Android 15+ on 16 KB page-size devices to align native code.
- **Gradle Configuration (`build.gradle.kts`)**:
  ```kotlin
  android {
      defaultConfig {
          ndk {
              abiFilters.addAll(listOf("armeabi-v7a", "arm64-v8a", "x86", "x86_64"))
          }
      }
      packaging {
          jniLibs {
              useLegacyPackaging = false
          }
      }
  }
  ```
- **CMake Linker Configuration (`CMakeLists.txt`)**:
  Packaging alone is insufficient if the native linker defaults to 4 KB pages. You MUST pass the linker flag:
  ```cmake
  if(COMMAND target_link_options)
      target_link_options(<target_name> PRIVATE "-Wl,-z,max-page-size=16384")
  else()
      set_target_properties(<target_name> PROPERTIES LINK_FLAGS "-Wl,-z,max-page-size=16384")
  endif()
  ```

### 2. R8 Minification & Code Shrinking
- Enable `isMinifyEnabled = true` and `isShrinkResources = true` in release build types.
- Annotate data transfer objects (DTOs), serialized JSON classes, native JNI classes, and reflection targets with `@Keep`.
- Continuously run `./gradlew lintVitalRelease` in CI to catch XML namespace mismatches and manifest errors prior to bundling.

---

## [Security, Cryptographic Licensing & Build Flavors]

### 1. Offline Cryptographic Licensing (ECDSA NIST P-256)
Support offline license verification without phone-home server telemetry:
- Verify signatures using `SHA256withECDSA` and the application's embedded public key.
- Verify license expiration dates and hardware entitlements completely offline.

### 2. Multi-Flavor Build Separation
Maintain clean separation of build flavors:
- **`playstore`**: Includes Google Play Billing (`com.android.billingclient:billing-ktx`), Firebase Messaging (FCM), and Google Services plugin. Generates signed Android App Bundle (`.aab`) via `./gradlew bundlePlaystoreRelease`.
- **`fdroid`**: 100% Free and Open-Source Software (FOSS). Strictly excludes proprietary Google Play and Firebase dependencies. Uses offline licensing and direct donation links. Generates signed Universal APK via `./gradlew assembleFdroidRelease`.
- **`universal`**: Sideload build for GitHub Releases with independent billing or donation integrations. Generates APK via `./gradlew assembleUniversalRelease`.

### 3. Google Play Policy: Prominent Disclosure for Accessibility
When publishing an app utilizing Accessibility Services for App/Web blocking or Digital Wellbeing:
- You MUST display an in-app Prominent Disclosure dialog BEFORE prompting the system accessibility settings.
- The disclosure must clearly state: (a) what data is observed (e.g. foreground package names, browser URLs), (b) the exact purpose (e.g. blocking distracting apps and adult content), and (c) that no data is collected, sold, or transmitted off-device.

---

## [On-Device AI & Local LLM Integration]

For tasks involving on-device neural network inference, Vision-Language Models (SigLIP 2, CLIP), local LLMs (Gemma, Gemini Nano AICore), SentencePiece C++ JNI, and multi-precision tensor extraction:
- **Activate and refer directly to the specialized skills: ndroid-local-ai-onnx (for SigLIP 2 zero-shot vision classification, ONNX Runtime Mobile, SentencePiece C++ JNI, 16 KB page memory alignment, and multi-precision tensor extraction) and ndroid-local-llm-dev (for LiteRT and Gemini Nano AICore)**.

---

## [Related Skills & Cross References]

- **ndroid-local-ai-onnx**: Specialized on-device AI and ONNX Runtime Mobile development, SigLIP 2 zero-shot vision classification, SentencePiece C++ JNI, 16 KB page alignment for Android 15+, multi-precision tensor extraction, and WorkManager resilient model downloads.
- **security-compliance**: ECDSA NIST P-256 cryptographic license verification and zero-knowledge privacy standards.
- **stripe-payments**: Stripe Checkout, subscription billing, and Play Billing integration.
- **supabase-backend**: Cloud synchronization and Row Level Security.
