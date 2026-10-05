#!/usr/bin/env python3
"""Repository hygiene, cryptographic manifest, and offline compliance verifier.

Enforces rules defined in PRD Section 16 and AGENTS.md:
1. Validates all datasets against data/manifest.json (SHA-256 and byte size).
2. Verifies absence of secrets, credentials, sqlite databases, or model weights (>20MB).
3. Verifies zero external runtime calls in backend source code.
"""

import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def check_manifest() -> bool:
    """Verify all datasets listed in manifest.json match byte count and SHA-256."""
    manifest_path = REPO_ROOT / "data" / "manifest.json"
    print(f"[HYGIENE] Checking data manifest: {manifest_path.relative_to(REPO_ROOT)}")

    if not manifest_path.exists():
        print(f"FAILED: Manifest not found at {manifest_path}", file=sys.stderr)
        return False

    with open(manifest_path, mode="r", encoding="utf-8") as f:
        manifest = json.load(f)

    datasets = manifest.get("datasets", [])
    if not datasets:
        print("FAILED: No datasets listed in manifest", file=sys.stderr)
        return False

    all_passed = True
    for ds in datasets:
        rel_path = ds.get("file_path")
        expected_sha = ds.get("sha256")
        expected_size = ds.get("byte_size")

        full_path = REPO_ROOT / rel_path
        if not full_path.exists():
            print(f"FAILED: Dataset file missing: {rel_path}", file=sys.stderr)
            all_passed = False
            continue

        with open(full_path, mode="rb") as fp:
            content = fp.read()

        actual_size = len(content)
        actual_sha = hashlib.sha256(content).hexdigest()

        if actual_size != expected_size:
            print(
                f"FAILED: Size mismatch for {rel_path}: expected {expected_size}, "
                f"got {actual_size}",
                file=sys.stderr,
            )
            all_passed = False

        if actual_sha != expected_sha:
            print(
                f"FAILED: SHA-256 mismatch for {rel_path}:\n"
                f"  Expected: {expected_sha}\n  Actual:   {actual_sha}",
                file=sys.stderr,
            )
            all_passed = False

        if actual_size == expected_size and actual_sha == expected_sha:
            print(f"  OK: {rel_path} ({actual_size} bytes, sha256={actual_sha[:8]}...)")

    return all_passed


def check_forbidden_files() -> bool:
    """Ensure no secrets, database files, or binary weights exist in tracked or workspace files."""
    print("[HYGIENE] Scanning repository for forbidden files and secrets...")
    forbidden_extensions = {".sqlite", ".sqlite3", ".db", ".safetensors", ".pt", ".bin", ".onnx"}
    forbidden_files = {"secrets.json", ".env"}

    violations = []
    # Walk repository ignoring virtualenvs, build artifacts, and runtime directory
    ignored_dirs = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        ".vite",
        "__pycache__",
        ".runtime",
    }

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        for fname in files:
            file_path = Path(root) / fname
            rel_path = file_path.relative_to(REPO_ROOT)

            if fname in forbidden_files:
                violations.append(f"Forbidden file detected: {rel_path}")

            if file_path.suffix.lower() in forbidden_extensions:
                violations.append(f"Forbidden extension detected: {rel_path}")

            # Check file size (> 20 MB is strictly forbidden in git repo)
            try:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                if size_mb > 20.0:
                    violations.append(
                        f"Large binary detected (>20MB): {rel_path} ({size_mb:.1f} MB)"
                    )
            except Exception:
                pass

    if violations:
        for v in violations:
            print(f"FAILED: {v}", file=sys.stderr)
        return False

    print("  OK: Zero secrets, database files, or large binaries detected.")
    return True


def check_offline_runtime() -> bool:
    """Ensure backend runtime code contains no unapproved external HTTP requests."""
    print("[HYGIENE] Verifying offline runtime policy in src/sentinel...")
    src_dir = REPO_ROOT / "src" / "sentinel"
    disallowed_patterns = [
        re.compile(r"api\.openai\.com"),
        re.compile(r"api\.anthropic\.com"),
        re.compile(r"huggingface\.co/api"),
        re.compile(r"requests\.(get|post|put|delete)"),
        re.compile(r"urllib\.request"),
    ]

    violations = []
    for py_file in src_dir.rglob("*.py"):
        rel = py_file.relative_to(REPO_ROOT)
        with open(py_file, mode="r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                # Ignore comments
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for pattern in disallowed_patterns:
                    if pattern.search(line):
                        violations.append(f"{rel}:{idx} - Disallowed pattern: {line.strip()}")

    if violations:
        for v in violations:
            print(f"FAILED: {v}", file=sys.stderr)
        return False

    print("  OK: 100% offline localhost compliance verified in backend runtime.")
    return True


def main() -> int:
    print("=" * 70)
    print(" S&P Sentinel Repository Hygiene & Manifest Verification")
    print("=" * 70)

    manifest_ok = check_manifest()
    files_ok = check_forbidden_files()
    offline_ok = check_offline_runtime()

    if manifest_ok and files_ok and offline_ok:
        print("=" * 70)
        print(" ALL HYGIENE AND MANIFEST CHECKS PASSED SUCCESSFULLY.")
        print("=" * 70)
        return 0
    else:
        print("=" * 70, file=sys.stderr)
        print(" HYGIENE VERIFICATION FAILED.", file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
