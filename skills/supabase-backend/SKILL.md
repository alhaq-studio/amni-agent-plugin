---
name: supabase-backend
description: >-
  Official Supabase Backend Skill covering Edge Functions (Deno runtime), PostgreSQL database modeling,
  Row Level Security (RLS) policies, Realtime Database sync, CLI operations, database migrations,
  and MCP server integration. Activate this skill for database, auth, and cloud backend tasks.
version: 1.1.0
---

# Supabase Backend Skill

This skill defines standards and patterns for managing Supabase PostgreSQL, Edge Functions, Auth, and Storage across the Amni Product Family (`AmniShield`, `AmniBlur`, and `AmniQuest`).

---

## 1. Unified Amni Ecosystem Database Schema

All applications in the Amni Ecosystem share a single, unified Supabase instance (`https://jrgpmcomvibgklmvnxud.supabase.co`).

### 1. Unified User Profiles (`public.profiles`)
The `profiles` table is shared between AmniShield (account tier, licenses) and AmniQuest (gamification, launcher state, streaks):
```sql
ALTER TABLE public.profiles
    ADD COLUMN IF NOT EXISTS username TEXT UNIQUE,
    ADD COLUMN IF NOT EXISTS full_name TEXT,
    ADD COLUMN IF NOT EXISTS has_profile BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS xp INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS coins INT NOT NULL DEFAULT 90,
    ADD COLUMN IF NOT EXISTS level INT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS inventory JSONB NOT NULL DEFAULT '{"STREAK_FREEZER": 2}'::jsonb,
    ADD COLUMN IF NOT EXISTS customization_info JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS achievements JSONB NOT NULL DEFAULT '["THE_EARLY_FEW"]'::jsonb,
    ADD COLUMN IF NOT EXISTS active_boosts JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS last_updated BIGINT NOT NULL DEFAULT (extract(epoch from now()) * 1000)::bigint,
    ADD COLUMN IF NOT EXISTS created_on TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS streak JSONB NOT NULL DEFAULT '{"currentStreak": 0, "longestStreak": 0, "lastCompletedDate": "0001-01-01", "streakFailureHistory": {}}'::jsonb,
    ADD COLUMN IF NOT EXISTS "blockedAndroidPackages" JSONB NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS "unlockedAndroidPackages" JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS fcm_tokens JSONB NOT NULL DEFAULT '[]'::jsonb;
```

### 2. Habit & Focus Quests (`public.quests`)
Dedicated table for AmniQuest habits and tasks:
```sql
CREATE TABLE IF NOT EXISTS public.quests (
    id TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    reward INT NOT NULL DEFAULT 5,
    integration_id TEXT NOT NULL DEFAULT 'DEEP_FOCUS',
    selected_days JSONB NOT NULL DEFAULT '[]'::jsonb,
    auto_destruct TEXT NOT NULL DEFAULT '9999-12-31',
    time_range JSONB NOT NULL DEFAULT '[0, 24]'::jsonb,
    created_on TEXT NOT NULL,
    last_completed_on TEXT NOT NULL DEFAULT '0001-01-01',
    instructions TEXT NOT NULL DEFAULT '',
    quest_json TEXT NOT NULL DEFAULT '',
    is_destroyed BOOLEAN NOT NULL DEFAULT FALSE,
    last_updated BIGINT NOT NULL DEFAULT (extract(epoch from now()) * 1000)::bigint,
    "isHardLock" BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.quests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own quests" ON public.quests
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
```

### 3. Habit Completion History (`public.quest_stats`)
```sql
CREATE TABLE IF NOT EXISTS public.quest_stats (
    id TEXT PRIMARY KEY,
    quest_id TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.quest_stats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own stats" ON public.quest_stats
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);
```

### 4. Licenses (`public.user_licenses`)
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

### 5. Storage Buckets (`profile`)
Avatar bucket (`profile`) configured with 5 MB maximum file size and authenticated-owner write policies:
```sql
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('profile', 'profile', TRUE, 5242880, ARRAY['image/jpeg', 'image/png', 'image/webp'])
ON CONFLICT (id) DO UPDATE SET public = TRUE;
```

---

## 2. Offline-First & Guest Migration Architecture

1. **Zero Egress for Guest Users**:
   - Apps must function 100% offline without mandatory account creation.
   - Sync workers MUST guard execution: if `isAnonymous || userId.isBlank()`, terminate immediately with `Result.success()`.
2. **Seamless Account Linking Pattern**:
   - When a guest user connects an account (`onAuthenticationSuccess(userId, email)`), rebind local SQLite / Room entities from anonymous/blank IDs to the authenticated `userId`.
   - Never wipe local habit history or progression upon account creation.
3. **Additive Conflict Resolution**:
   - When merging profile state during sync, resolve conflicting fields additively:
     - XP, Level, Coins, Streak: `maxOf(remote, local)`
     - Inventory: Set union of owned items
     - Avatars / Remote URLs: Remote precedence
4. **Immediate Push Post-Link**:
   - When pulling first-time sync data, immediately schedule a push of local guest data to guarantee bidirectional convergence.

---

## 3. Edge Functions (Deno Runtime)
- Place Edge Functions in `supabase/functions/<function-name>/index.ts`.
- Always set proper CORS headers on preflight `OPTIONS` requests.
- Deploy Edge Functions via Supabase MCP or CLI `supabase functions deploy`.

---

## 4. Related Skills & Cross References
- **`stripe-payments`**: Supabase Edge Functions handling Stripe checkout sessions and payment webhooks.
- **`security-compliance`**: Row Level Security (RLS) audit rules and JWT verification settings.
