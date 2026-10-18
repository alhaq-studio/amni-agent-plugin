#!/usr/bin/env python3
"""
Verify Android 15+ 16 KB Page Memory Alignment in CMake and Gradle build files.
"""

import sys
import os
import re

CMAKE_ALIGN_PATTERN = re.compile(r"-Wl,-z,max-page-size=16384")
GRADLE_PACKAGING_PATTERN = re.compile(r"useLegacyPackaging\s*=\s*false")

def verify_project_alignment(root_dir: str):
    issues = []
    cmake_found = False

    for root, _, files in os.walk(root_dir):
        for f in files:
            path = os.path.join(root, f)
            if f == "CMakeLists.txt":
                cmake_found = True
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                    if not CMAKE_ALIGN_PATTERN.search(content):
                        issues.append(f"[FAIL] CMakeLists.txt missing 16 KB page alignment: {path}")
            elif f == "build.gradle.kts" and "app" in root:
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
                    if "jniLibs" in content and not GRADLE_PACKAGING_PATTERN.search(content):
                        issues.append(f"[FAIL] build.gradle.kts missing useLegacyPackaging = false: {path}")

    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        sys.exit(1)
    else:
        status = "16 KB page alignment verified" if cmake_found else "No CMake native builds detected (pure JVM)"
        print(f"[OK] Android 15+ Memory Alignment: {status}.")
        sys.exit(0)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    verify_project_alignment(target)

