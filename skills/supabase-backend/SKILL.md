---
name: supabase-backend
description: >-
  Official Supabase Backend Skill covering Edge Functions (Deno runtime), PostgreSQL database modeling,
  Row Level Security (RLS) policies, Realtime Database sync, CLI operations, database migrations,
  and MCP server integration. Activate this skill for database, auth, and cloud backend tasks.
version: 1.0.0
---

# Supabase Backend Skill

This skill defines standards and patterns for managing Supabase PostgreSQL, Edge Functions, Auth, and Storage across the Amni Product Family.

---

## 1. Database Architecture & Migrations

### 1. DDL Migration Guidelines
- Write declarative SQL migrations in `supabase/migrations/YYYYMMDDHHMMSS_name.sql`.
- Apply migrations using Supabase MCP tool `mcp_supabase_apply_migration` or CLI `supabase db push`.
- Never hardcode UUIDs in migration files.

### 2. Standard Database Schema (`user_licenses` & `user_profiles`)
```sql
CREATE TABLE IF NOT EXISTS public.user_licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    license_key TEXT UNIQUE NOT NULL,
    plan_type TEXT NOT NULL CHECK (plan_type IN ('monthly', 'annual', 'lifetime')),
    status TEXT NOT NULL CHECK (status IN ('active', 'expired', 'cancelled')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_licenses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own licenses" ON public.user_licenses
    FOR SELECT USING (auth.uid() = user_id);
```

---

## 2. Edge Functions (Deno Runtime)
- Place Edge Functions in `supabase/functions/<function-name>/index.ts`.
- Always set proper CORS headers on preflight `OPTIONS` requests.
- Deploy Edge Functions via Supabase MCP tool `mcp_supabase_deploy_edge_function` or CLI `supabase functions deploy`.

---

## 3. Related Skills & Cross References

- **`stripe-payments`**: Supabase Edge Functions handling Stripe checkout sessions and payment webhooks.
- **`security-compliance`**: Row Level Security (RLS) audit rules and JWT verification settings.

