#!/usr/bin/env python3
"""
Amni Ecosystem Zero-Emoji Policy Enforcer.
Deterministic hook script to detect and prevent UTF-8 emojis or pictographs
across code, markdown, configurations, logs, and documentation.
"""

import sys
import os
import json
import subprocess
from typing import List, Tuple, Dict, Any, Optional

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico",
    ".onnx", ".tflite", ".bin", ".model", ".so", ".dll", ".dylib",
    ".jar", ".aar", ".aab", ".apk", ".zip", ".tar", ".gz",
    ".keystore", ".jks", ".p12", ".class", ".pyc",
    ".ttf", ".otf", ".woff", ".woff2", ".mp3", ".wav", ".ogg", ".flac", ".m4a", ".mp4"
}

IGNORED_DIRS = {
    ".git", ".gradle", ".idea", "build", "node_modules",
    "__pycache__", ".kotlin", ".gradle_home", ".cxx", "sentencepiece"
}

def is_emoji_codepoint(code: int) -> bool:
    """Return True if Unicode code point is within emoji or pictograph ranges."""
    return (
        (0x1F600 <= code <= 0x1F64F) or  # Emoticons
        (0x1F300 <= code <= 0x1F5FF) or  # Misc Symbols and Pictographs
        (0x1F680 <= code <= 0x1F6FF) or  # Transport and Map
        (0x1F700 <= code <= 0x1F77F) or  # Alchemical Symbols
        (0x1F780 <= code <= 0x1F7FF) or  # Geometric Shapes Extended
        (0x1F800 <= code <= 0x1F8FF) or  # Supplemental Arrows-C
        (0x1F900 <= code <= 0x1F9FF) or  # Supplemental Symbols and Pictographs
        (0x1FA00 <= code <= 0x1FA6F) or  # Chess Symbols, etc.
        (0x1FA70 <= code <= 0x1FAFF) or  # Symbols and Pictographs Extended-A
        (0x1F000 <= code <= 0x1F02F) or  # Mahjong Tiles
        (0x1F0A0 <= code <= 0x1F0FF) or  # Playing Cards
        (0x1F100 <= code <= 0x1F2FF) or  # Enclosed Alphanumeric / Ideographic Supplements
        (0x2300 <= code <= 0x23FF) or    # Misc Technical (e.g. watches, hourglass, media buttons)
        (0x2600 <= code <= 0x26FF) or    # Misc symbols (e.g. warning, lightning, coffee)
        (0x2700 <= code <= 0x27BF) or    # Dingbats (e.g. checkmarks, crosses, scissors)
        (0x2B00 <= code <= 0x2BFF) or    # Misc Symbols and Arrows (e.g. stars, squares, circles)
        (0xFE00 <= code <= 0xFE0F) or    # Variation Selectors
        (code == 0x200D) or              # Zero Width Joiner
        (code == 0x20E3)                 # Combining Enclosing Keycap
    )

def check_text(content: str, source_name: str) -> List[Tuple[int, str, str, str]]:
    """Scan string content line by line for emojis."""
    violations = []
    lines = content.splitlines()
    for line_idx, line in enumerate(lines, 1):
        for char in line:
            cp = ord(char)
            if is_emoji_codepoint(cp):
                violations.append((
                    line_idx,
                    char,
                    f"U+{cp:04X}",
                    line.strip()
                ))
    return violations

def check_single_file(file_path: str) -> List[Tuple[str, int, str, str, str]]:
    """Scan a single file on disk for emoji violations."""
    if not os.path.isfile(file_path):
        return []

    cleaned_path = file_path.rstrip("~").lower()
    _, ext = os.path.splitext(cleaned_path)
    if ext in BINARY_EXTENSIONS:
        return []

    norm_path = os.path.normpath(file_path)
    if norm_path.endswith("check_no_emojis.py"):
        return []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return []

    raw_violations = check_text(content, file_path)
    return [(file_path, line, char, ucode, snippet) for line, char, ucode, snippet in raw_violations]

def scan_target(target_path: str) -> List[Tuple[str, int, str, str, str]]:
    """Scan target path (file or directory recursively) for emoji violations."""
    if os.path.isfile(target_path):
        return check_single_file(target_path)
    elif os.path.isdir(target_path):
        violations = []
        for root, dirs, files in os.walk(target_path):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for f in files:
                fpath = os.path.join(root, f)
                violations.extend(check_single_file(fpath))
        return violations
    return []

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

    if hook_mode or (not cli_targets and check_stdin_has_data()):
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
        if code_content and isinstance(code_content, str):
            direct_content_checks.append((target or "in-memory-edit", code_content))

    if cli_targets:
        targets_to_check.extend(cli_targets)

    if stop_mode or (not targets_to_check and not direct_content_checks):
        git_files = get_git_modified_files()
        if git_files:
            targets_to_check.extend(git_files)
        elif not stop_mode and not targets_to_check:
            # Standalone execution in non-git directory defaults to scanning current directory
            targets_to_check.append(".")

    # Deduplicate targets
    targets_to_check = list(dict.fromkeys(targets_to_check))

    all_violations: List[Tuple[str, int, str, str, str]] = []

    # Check direct in-memory content from tool use
    for source_name, content in direct_content_checks:
        raw_v = check_text(content, source_name)
        for line, char, ucode, snippet in raw_v:
            all_violations.append((source_name, line, char, ucode, snippet))

    # Check files or directories on disk
    scanned_file_count = len(direct_content_checks)
    for target in targets_to_check:
        if os.path.isfile(target):
            scanned_file_count += 1
            all_violations.extend(check_single_file(target))
        elif os.path.isdir(target):
            for root, dirs, files in os.walk(target):
                dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
                for f in files:
                    fpath = os.path.join(root, f)
                    _, ext = os.path.splitext(f.lower())
                    if ext not in BINARY_EXTENSIONS:
                        scanned_file_count += 1
                        all_violations.extend(check_single_file(fpath))

    if all_violations:
        lines = [
            "[ERROR] STRICT UNIVERSAL ZERO EMOJI POLICY VIOLATION DETECTED",
            "Emojis and emoji-based unicode characters are strictly forbidden across code, markdown, comments, logs, and configs.",
            "Use plain-text tags ([OK], [INFO], [FAIL], [WARNING], [ERROR]) or standard vector icons.",
            ""
        ]
        for fpath, line, char, ucode, snippet in all_violations:
            lines.append(f"  - File: {fpath}:{line}")
            lines.append(f"    CodePoint: {ucode} ({repr(char)})")
            lines.append(f"    Snippet: {snippet}")
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
            print(f"[OK] Zero Emoji Policy: Verified {scanned_file_count} files/entries, zero emojis found.")
            sys.exit(0)

if __name__ == "__main__":
    main()
