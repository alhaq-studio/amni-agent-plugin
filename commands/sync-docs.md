---
description: Synchronize ARCHITECTURE.md and project documentation based on recent git changes
allowed-tools: Read, Write, Edit, grep_search, find_by_name, run_command
argument-hint: [optional-target-file]
---

# Sync Documentation Command (`/sync-docs`)

Inspect recent git changes and synchronize project documentation (`ARCHITECTURE.md`, `README.md`, or `$1`):

1. **Inspect Modified Architecture & Modules**:
   - Check modified files: !`git status --short`
   - Review recent diff summary: !`git diff --stat HEAD~1`

2. **Verify Invariants**:
   - Confirm module boundaries and responsibilities are accurate.
   - Ensure all public APIs, ViewModels, Room entities, or WorkManager workers touched in the diff are documented.
   - Verify that the zero emoji policy is strictly maintained across all updated documentation files.

3. **Update Documentation**:
   - If architectural changes occurred, make concise, targeted updates to `ARCHITECTURE.md`.
   - Keep documentation minimal, precise, and under 150 lines per file to prevent context window bloat.

