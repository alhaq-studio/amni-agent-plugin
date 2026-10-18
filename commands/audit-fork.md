---
description: Audit an experimental fork or feature branch against production invariants before merging
allowed-tools: Read, grep_search, find_by_name, run_command
argument-hint: [target-branch-or-ref]
---

# Audit Fork Command (`/audit-fork`)

Audit the branch or commit reference specified in `$1` (defaults to HEAD or current feature branch) against Amni ecosystem invariants:

1. **Check Modified Files**:
   - Files changed vs target: !`git diff --name-only $1`

2. **Run Invariant Checks**:
   - Run Zero-Emoji check: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/check_no_emojis.py`
   - Run Single-Source ViewModel check: `python ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/verify_flavor_sources.py`

3. **Check Android 15+ Native Alignment**:
   - Inspect any modified `CMakeLists.txt` for `-Wl,-z,max-page-size=16384`.
   - Inspect any modified `build.gradle.kts` for `useLegacyPackaging = false`.

4. **Report Audit Results**:
   - Generate structured report listing passed checks and any detected invariant violations.

