# Store & FOSS Compliance Reference

This guide documents the multi-flavor build strategy for Google Play Store vs. F-Droid distribution.

---

## 1. Flavor Matrix

| Flavor | Target Channel | Proprietary SDKs Allowed? | Core Features |
| :--- | :--- | :--- | :--- |
| `play` / `playstore` | Google Play Store | Yes (Google Play Billing, Stripe, Crashlytics) | Full app blocking, Reels filter, in-app purchases, ECDSA licensing |
| `fdroid` | F-Droid / GitHub Releases | NO (Strictly 100% FOSS) | Full app blocking, Reels filter, offline ECDSA licensing only |

---

## 2. Invariant Rules

1. **Zero Proprietary SDKs in F-Droid**:
   - Never import GMS (`play-services-*`), Firebase Crashlytics, or Google Play Billing in `src/fdroid` or common `src/main` without flavor abstraction.
   - Use Gradle dependency configurations: `playImplementation(...)` vs `fdroidImplementation(...)`.

2. **Unified Core Domain**:
   - Keep domain entities, Room databases, and ViewModels in `src/main`.
   - Use interface bridges (e.g., `LicenseValidator`, `BillingBridge`) to inject flavor-specific implementations.

