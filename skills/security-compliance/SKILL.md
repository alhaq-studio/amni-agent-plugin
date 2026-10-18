---
name: security-compliance
description: >-
  Official Security & Compliance Skill covering zero-knowledge privacy, offline cryptographic license verification
  (ECDSA NIST P-256), Android Accessibility/VPN safety, R8/ProGuard obfuscation, tamper detection,
  and Supabase/Firestore Security Rules auditing. Activate this skill for security architecture, auditing,
  and compliance tasks.
version: 1.0.0
---

# Security & Compliance Skill

This skill defines security standards, cryptographic requirements, and compliance rules for the Amni Product Family.

---

## 1. Cryptographic License Verification (ECDSA P-256)

To maintain F-Droid compliance and offline privacy, Amni applications use an **Offline-First Cryptographic Licensing Model**:

### 1. Verification Specification
- **Algorithm**: NIST P-256 (`secp256r1`) with SHA-256 signature (`SHA256withECDSA`).
- **Format**: `Base64(PayloadJson).Base64(SignatureBytes)`
- **Keyring Architecture**: Keyring maps schema version numbers to Base64 X.509 public keys.
- **Offline Rule**: License validation MUST be executable completely offline without making network requests.

### 2. Validation Flow
```kotlin
val parts = licenseString.split(".")
if (parts.size == 2) {
    val payloadJson = String(Base64.getDecoder().decode(parts[0]), Charsets.UTF_8)
    val signatureBytes = Base64.getDecoder().decode(parts[1])
    val payload = Gson().fromJson(payloadJson, LicensePayload::class.java)
    if (payload.expires > System.currentTimeMillis()) {
        val publicKey = getPublicKeyForVersion(payload.version)
        val sig = Signature.getInstance("SHA256withECDSA")
        sig.initVerify(publicKey)
        sig.update(Base64.getDecoder().decode(parts[0]))
        val isValid = sig.verify(signatureBytes)
    }
}
```

---

## 2. Android Security & Permissions Safety

### 1. Accessibility Service Security
- Scope accessibility service events exclusively to `TYPE_WINDOW_STATE_CHANGED` and `TYPE_WINDOW_CONTENT_CHANGED`.
- NEVER log or transmit text contents from `AccessibilityNodeInfo` to external servers or analytics.
- Mask sensitive input fields (password, PIN, credit card nodes) during inspection.

### 2. Passcode & PIN Hardening
- Store PIN hashes using PBKDF2 with SHA-256 or BCrypt salts in `EncryptedSharedPreferences` / DataStore.
- Implement rate limiting (30-second delay after 5 failed attempts) to prevent brute-force attacks.

---

## 3. Cloud & Database Security Rules

### 1. Supabase PostgreSQL Row Level Security (RLS)
- Enforce RLS on ALL database tables:
  ```sql
  ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
  CREATE POLICY "Users can only access own data" ON user_profiles
    FOR ALL USING (auth.uid() = user_id);
  ```

### 2. Supabase Edge Functions JWT Verification
- Keep `verify_jwt = true` enabled on all deployed Edge Functions unless specifically handling signed external webhooks (e.g., Stripe webhooks verified via Stripe Signature headers).

---

## 4. Related Skills & Cross References

- **`android-local-ai-onnx`**: Local neural network execution with zero external data transmission.
- **`stripe-payments`**: Webhook verification and offline ECDSA license key delivery.
- **`supabase-backend`**: Row Level Security and Edge Function JWT security.

