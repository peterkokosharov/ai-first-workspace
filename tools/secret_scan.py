#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Block commits that contain API keys or tokens (standard library only).

Usage:
    python3 tools/secret_scan.py            # scan files staged for commit
    python3 tools/secret_scan.py --all      # scan every tracked file
    python3 tools/secret_scan.py FILE ...   # scan the given files

Exit code 0 = clean, 1 = possible secret found (the value is never printed).

Enable it as the git pre-commit and pre-push hooks once per clone:
    git config core.hooksPath .githooks
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Each rule matches a real-looking value, not the bare prefix, so docs that
# mention "nvapi-" or "$NVIDIA_API_KEY" stay allowed.
RULES: list[tuple[str, re.Pattern[str]]] = [
    ("NVIDIA API key", re.compile(r"nvapi-[A-Za-z0-9_-]{20,}")),
    ("OpenAI-style key", re.compile(r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}")),
    ("GitHub token", re.compile(r"\bghp_[A-Za-z0-9]{30,}")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google / Gemini API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])")),
    # api_key: <literal> / api_key = "<literal>" with 16+ key-like characters.
    # Values that start with $, <, {, or a name followed by ( or [ are skipped.
    ("api_key literal", re.compile(
        r"""api_key\s*[:=]\s*["']?(?![$<{])[A-Za-z0-9_\-]{16,}["']?(?![\w(\[.])""",
        re.IGNORECASE)),
]

ALLOW_MARK = "secret-scan: allow"


def find_secrets(text: str) -> list[tuple[int, str]]:
    """Return (line number, rule name) for each suspicious line."""
    hits: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARK in line:
            continue
        for name, pattern in RULES:
            if pattern.search(line):
                hits.append((number, name))
                break
    return hits


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def _staged_files() -> list[tuple[str, str]]:
    names = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    result = []
    for name in names.decode("utf-8", "replace").split("\0"):
        if name:
            blob = _git("show", f":{name}")
            result.append((name, blob.decode("utf-8", "replace")))
    return result


def _tracked_files() -> list[tuple[str, str]]:
    names = _git("ls-files", "-z").decode("utf-8", "replace").split("\0")
    return [(n, Path(n).read_text("utf-8", "replace")) for n in names if n and Path(n).is_file()]


def main(argv: list[str]) -> int:
    if argv == ["--all"]:
        files = _tracked_files()
    elif argv:
        files = [(a, Path(a).read_text("utf-8", "replace")) for a in argv]
    else:
        files = _staged_files()
    found = 0
    for name, text in files:
        if "\0" in text[:8000]:
            continue  # binary
        for number, rule in find_secrets(text):
            print(f"{name}:{number}: possible {rule} (value hidden)", file=sys.stderr)
            found += 1
    if found:
        print(f"secret-scan: {found} possible secret(s). Move them to the secret store "
              f"(tools/secret.py). False positive? Add '{ALLOW_MARK}' to that line.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
