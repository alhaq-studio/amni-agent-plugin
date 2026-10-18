#!/usr/bin/env python3
"""
Amni Ecosystem Single-Source ViewModel Invariant Enforcer.
Deterministic hook script to prevent duplicate ViewModel classes across Android build flavors
(e.g., src/play vs src/fdroid), preventing KSP collision errors and architectural drift.
"""

import sys
import os
import re
import json
import subprocess
from typing import List, Tuple, Dict, Any, Optional

ALLOWED_FLAVOR_BRIDGES = {
    "LicenseFlavorModule.kt",
    "FlavorConfig.kt",
    "BillingBridge.kt",
    "BillingModule.kt",
    "FlavorModule.kt"
}

IGNORED_DIRS = {
    ".git", ".gradle", ".idea", "build", "node_modules",
    "__pycache__", ".kotlin", ".gradle_home"
}

FLAVOR_DIR_PATTERN = re.compile(r"[/\\]src[/\\](play|fdroid|playstore)[/\\]", re.IGNORECASE)
VIEWMODEL_NAME_PATTERN = re.compile(r"(ViewModel|ViewVM|VM)\.kt$", re.IGNORECASE)
CLASS_VIEWMODEL_PATTERN = re.compile(
    r"\bclass\s+([A-Za-z0-9_]+)\s*(?:<[^>]+>)?\s*(?:@[A-Za-z0-9_.]+\s*)*(?:constructor\s*)?(?:\([^)]*\))?\s*:\s*[^\{]*\b(?:androidx\.lifecycle\.)?(?:Android)?ViewModel\b",
    re.DOTALL
)

def is_allowed_flavor_file(filename: str) -> bool:
    if filename in ALLOWED_FLAVOR_BRIDGES:
        return True
    if filename.endswith("Module.kt") or filename.endswith("Bridge.kt") or filename.endswith("Flavor.kt"):
        return True
    return False

def check_content_for_flavor_viewmodel(content: str, source_name: str, flavor_name: str) -> List[Tuple[str, str]]:
    """Check text content for ViewModel class inheritance inside a flavor."""
    violations = []
    matches = CLASS_VIEWMODEL_PATTERN.findall(content)
    for class_name in matches:
        violations.append((
            "ViewModel Class Definition In Flavor",
            f"Class '{class_name}' extends ViewModel/AndroidViewModel inside '{flavor_name}' flavor source set. Move this ViewModel to 'app/src/main/' to avoid duplicate KSP symbol definitions."
        ))
    return violations

def check_file_for_flavor_viewmodel(file_path: str) -> List[Tuple[str, str]]:
    """Return list of (violation_type, description) if file is a forbidden flavor ViewModel."""
    norm_path = os.path.normpath(file_path)

    # Check if file resides in a flavor source directory
    flavor_match = FLAVOR_DIR_PATTERN.search(norm_path)
    if not flavor_match:
        return []

    flavor_name = flavor_match.group(1)
    file_basename = os.path.basename(norm_path)

    violations = []

    # 1. Check filename for ViewModel pattern
    if VIEWMODEL_NAME_PATTERN.search(file_basename):
        violations.append((
            "ViewModel Filename In Flavor",
            f"File '{file_basename}' in '{flavor_name}' flavor source set matches ViewModel naming pattern. ViewModels must reside in 'app/src/main/'."
        ))

    # 2. Check file content for ViewModel class inheritance
    if os.path.isfile(norm_path):
        try:
            with open(norm_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                violations.extend(check_content_for_flavor_viewmodel(content, norm_path, flavor_name))
        except Exception:
            pass

    return violations

def check_cross_flavor_duplicates(repo_root: str) -> List[Tuple[str, str]]:
    """Scan flavor directories for duplicate class or file names between play and fdroid."""
    violations = []
    flavor_files: Dict[str, Dict[str, str]] = {"play": {}, "fdroid": {}, "playstore": {}}

    for root, dirs, files in os.walk(repo_root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        norm_root = os.path.normpath(root)
        flavor_match = FLAVOR_DIR_PATTERN.search(norm_root)
        if not flavor_match:
            continue
        flavor = flavor_match.group(1).lower()
        if flavor not in flavor_files:
            continue

        for f in files:
            if not f.endswith(".kt"):
                continue
            if is_allowed_flavor_file(f):
                continue
            full_path = os.path.join(norm_root, f)
            flavor_files[flavor][f] = full_path

    # Compare play/playstore with fdroid
    play_dict = {**flavor_files.get("play", {}), **flavor_files.get("playstore", {})}
    fdroid_dict = flavor_files.get("fdroid", {})

    for fname, play_path in play_dict.items():
        if fname in fdroid_dict:
            fdroid_path = fdroid_dict[fname]
            violations.append((
                "Duplicate Flavor File Collision",
                f"Duplicate Kotlin file '{fname}' detected across flavors:\n    Play:   {play_path}\n    FDroid: {fdroid_path}\nUnify this component in 'src/main' or define an abstraction/interface."
            ))

    return violations

def get_git_modified_files() -> List[str]:
    """Get list of modified or newly added files from git status."""
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False
        )
        files = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                status, path = parts
                if status != "D" and os.path.isfile(path):
                    files.append(path)
        return files
    except Exception:
        return []

def check_stdin_has_data() -> bool:
    """Non-blocking check whether stdin has data available without hanging."""
    if sys.stdin.isatty():
        return False
    if os.name == "nt":
        try:
            import msvcrt
            import ctypes
            from ctypes import wintypes
            handle = msvcrt.get_osfhandle(sys.stdin.fileno())
            file_type = ctypes.windll.kernel32.GetFileType(handle)
            if file_type == 1:  # FILE_TYPE_DISK (redirected file)
                return True
            avail = wintypes.DWORD()
            success = ctypes.windll.kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None)
            return bool(success and avail.value > 0)
        except Exception:
            return False
    else:
        try:
            import select
            r, _, _ = select.select([sys.stdin], [], [], 0)
            return bool(r)
        except Exception:
            return False

def main():
    hook_mode = "--hook" in sys.argv
    stop_mode = "--stop-check" in sys.argv
    cli_targets = [arg for arg in sys.argv[1:] if not arg.startswith("--")]

    hook_input_data: Optional[Dict[str, Any]] = None

    if hook_mode or check_stdin_has_data():
        try:
            raw = sys.stdin.read()
            if raw.strip():
                hook_input_data = json.loads(raw)
        except Exception:
            pass

    targets_to_check: List[str] = []
    direct_content_checks: List[Tuple[str, str]] = []

    if hook_input_data:
        hook_event = hook_input_data.get("hook_event_name", "")
        if hook_event in ("Stop", "SubagentStop"):
            stop_mode = True

        tool_input = hook_input_data.get("tool_input", {})
        target = (
            tool_input.get("TargetFile") or
            tool_input.get("file_path") or
            tool_input.get("path") or
            tool_input.get("file")
        )
        if target:
            targets_to_check.append(target)

        code_content = (
            tool_input.get("CodeContent") or
            tool_input.get("content") or
            tool_input.get("ReplacementContent")
        )
        if target and code_content and isinstance(code_content, str):
            direct_content_checks.append((target, code_content))

    if cli_targets:
        targets_to_check.extend(cli_targets)

    if stop_mode or (not targets_to_check and not direct_content_checks):
        git_files = get_git_modified_files()
        if git_files:
            targets_to_check.extend(git_files)
        elif not stop_mode and not targets_to_check:
            # Standalone scan default to current directory
            targets_to_check.append(".")

    targets_to_check = list(dict.fromkeys(targets_to_check))

    # Expand any directory targets to .kt files
    expanded_files: List[str] = []
    for target in targets_to_check:
        if os.path.isfile(target):
            expanded_files.append(target)
        elif os.path.isdir(target):
            for root, dirs, files in os.walk(target):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
                for f in files:
                    if f.endswith(".kt"):
                        expanded_files.append(os.path.join(root, f))

    expanded_files = list(dict.fromkeys(expanded_files))

    all_violations: List[Tuple[str, str, str]] = []

    # Check direct in-memory tool inputs
    for target, content in direct_content_checks:
        norm_path = os.path.normpath(target)
        flavor_match = FLAVOR_DIR_PATTERN.search(norm_path)
        if flavor_match:
            flavor_name = flavor_match.group(1)
            file_basename = os.path.basename(norm_path)
            if VIEWMODEL_NAME_PATTERN.search(file_basename):
                all_violations.append((
                    target,
                    "ViewModel Filename In Flavor",
                    f"File '{file_basename}' in '{flavor_name}' flavor source set matches ViewModel naming pattern. ViewModels must reside in 'app/src/main/'."
                ))
            v_list = check_content_for_flavor_viewmodel(content, target, flavor_name)
            for v_type, desc in v_list:
                all_violations.append((target, v_type, desc))

    # Check files on disk
    for f in expanded_files:
        v_list = check_file_for_flavor_viewmodel(f)
        for v_type, desc in v_list:
            all_violations.append((f, v_type, desc))

    # In stop mode, also run cross-flavor duplicate detection across workspace
    if stop_mode:
        cwd = os.getcwd()
        cross_dups = check_cross_flavor_duplicates(cwd)
        for v_type, desc in cross_dups:
            all_violations.append(("Workspace Scan", v_type, desc))

    if all_violations:
        lines = [
            "[ERROR] SINGLE-SOURCE VIEWMODEL INVARIANT VIOLATION DETECTED",
            "ViewModels must be unified in 'app/src/main' rather than duplicated inside flavor folders.",
            "Defining ViewModels in flavor source sets causes duplicate KSP symbols and architectural divergence.",
            ""
        ]
        for fpath, v_type, desc in all_violations:
            lines.append(f"  - Target: {fpath}")
            lines.append(f"    Issue: {v_type}")
            lines.append(f"    Details: {desc}")
            lines.append("")

        error_message = "\n".join(lines)

        if hook_mode:
            output = {
                "decision": "continue",
                "hookSpecificOutput": {
                    "hookEventName": "Stop" if stop_mode else "PostToolUse",
                    "additionalContext": error_message
                }
            }
            print(json.dumps(output))
            sys.exit(1 if stop_mode else 0)
        else:
            print(error_message, file=sys.stderr)
            sys.exit(1)
    else:
        if hook_mode:
            sys.exit(0)
        else:
            print(f"[OK] Single-Source ViewModel Invariant: Verified {len(expanded_files) + len(direct_content_checks)} files/entries, zero flavor ViewModel collisions found.")
            sys.exit(0)

if __name__ == "__main__":
    main()
