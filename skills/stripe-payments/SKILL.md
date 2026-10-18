---
name: stripe-payments
description: >-
  Official Stripe Payments & Billing Skill covering Stripe Checkout integration, subscription billing (Monthly & Annual),
  webhook handling via Supabase Edge Functions, customer portal management, price ID mapping, refund workflows,
  PCI DSS compliance, and offline ECDSA license key delivery. Activate this skill for payment and billing tasks.
version: 1.0.0
---

# Stripe Payments & Billing Skill

This skill defines payment integration architectures, subscription management, and webhook handling workflows for the Amni ecosystem.

---

## 1. Product & Pricing Architecture

### 1. Subscription Tiers
- **Monthly Supporter Pass**: `$4.99 / month`
- **Annual Supporter Pass**: `$39.99 / year` (~33% discount)
- **Lifetime License**: `$79.99 one-time`

---

## 2. Integration Flow (Supabase Edge Function + Stripe Checkout)

### 1. Checkout Session Creation (`create-checkout-session` Edge Function)
```typescript
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import Stripe from "https://esm.sh/stripe@12.0.0?target=deno";

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, {
  apiVersion: "2022-11-15",
  httpClient: Stripe.createFetchHttpClient(),
});

serve(async (req) => {
  const { priceId, userId, email } = await req.json();
  const session = await stripe.checkout.sessions.create({
    payment_method_types: ["card"],
    mode: "subscription",
    line_items: [{ price: priceId, quantity: 1 }],
    customer_email: email,
    metadata: { userId },
    success_url: `https://amnishield.com/checkout/success?session_id={CHECKOUT_SESSION_ID}`,
    cancel_url: `https://amnishield.com/checkout/cancel`,
  });

  return new Response(JSON.stringify({ url: session.url }), {
    headers: { "Content-Type": "application/json" },
  });
});
```

### 2. Webhook Handling (`stripe-webhook` Edge Function)
- Verify `stripe-signature` header using `stripe.webhooks.constructEvent()`.
- Listen for `checkout.session.completed` and `invoice.payment_succeeded`.
- Generate ECDSA signed license key upon payment success and send it via email / Supabase user record.

---

## 3. App Integration Guidelines
- On Android, open Stripe Checkout URLs safely via `CustomTabsIntent` or system browser.
- Listen for deep-link return callbacks: `amnishield://premium/activate?key={LICENSE_KEY}`.
- Store verified license state locally in `EncryptedSharedPreferences` or DataStore.

---

## 4. Related Skills & Cross References

- **`security-compliance`**: Cryptographic ECDSA P-256 license signature creation and offline client validation.
- **`supabase-backend`**: Edge Functions hosting and user license table security.

