#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Block commits that contain API keys or tokens (standard library only).

Usage:
    python3 tools/secret_scan.py            # scan files staged for commit
    python3 tools/secret_scan.py --all      # scan every tracked file
    python3 tools/secret_scan.py FILE ...   # scan the given files
    python3 tools/secret_scan.py --push     # pre-push: read git's ref lines on stdin,
                                            # scan the lines added by every pushed commit

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
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google / Gemini API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])")),
    ("Google OAuth client secret", re.compile(r"\bGOCSPX-[A-Za-z0-9_-]{20,}")),
    ("Google OAuth access token", re.compile(r"\bya29\.[A-Za-z0-9_-]{30,}")),
    ("Google OAuth refresh token", re.compile(r"(?<![A-Za-z0-9/])1//0[A-Za-z0-9_-]{30,}")),
    ("Private key block", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")),
    ("Hugging Face token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    # api_key: <literal> / api_key = "<literal>" with 16+ key-like characters.
    # Values that start with $, <, {, or a name followed by ( or [ are skipped.
    ("api_key literal", re.compile(
        r"""api_key\s*[:=]\s*["']?(?![$<{])[A-Za-z0-9_\-]{16,}["']?(?![\w(\[.])""",
        re.IGNORECASE)),
]

ALLOW_MARK = "secret-scan: allow"


def _line_rule(line: str) -> str | None:
    """Return the name of the first rule that matches ``line``, or None."""
    if ALLOW_MARK in line:
        return None
    for name, pattern in RULES:
        if pattern.search(line):
            return name
    return None


def find_secrets(text: str) -> list[tuple[int, str]]:
    """Return (line number, rule name) for each suspicious line."""
    hits: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        rule = _line_rule(line)
        if rule:
            hits.append((number, rule))
    return hits


_SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_HUNK = re.compile(r"^(@{2,}) .*?\+(\d+)(?:,\d+)? \1")


def find_secrets_in_diff(diff: str) -> list[tuple[str, str, int, str]]:
    """Scan the added lines of a patch from ``git diff-tree --stdin -p --cc``.

    Returns (commit, path, line number, rule name) for each suspicious added line.
    A line is "added" when its prefix column(s) hold a '+' and no '-'.
    """
    hits: list[tuple[str, str, int, str]] = []
    commit, path, number, columns, in_hunk = "", "", 0, 1, False
    for line in diff.splitlines():
        if _SHA.match(line):
            commit, path, in_hunk = line, "", False
        elif line.startswith("diff "):
            path, in_hunk = "", False
        elif line.startswith("@@"):
            match = _HUNK.match(line)
            in_hunk = bool(match)
            if match:
                columns, number = len(match.group(1)) - 1, int(match.group(2))
        elif not in_hunk:
            if line.startswith("+++ "):
                name = line[4:].strip().strip('"')
                path = name[2:] if name.startswith("b/") else name
        elif line.startswith("\\"):
            continue  # "\ No newline at end of file"
        else:
            prefix, content = line[:columns], line[columns:]
            if "-" in prefix:
                continue  # removed line: not in the pushed result
            if "+" in prefix:
                rule = _line_rule(content)
                if rule:
                    hits.append((commit, path, number, rule))
            number += 1
    return hits


def _git(*args: str) -> bytes:
    return subprocess.run(["git", *args], check=True, capture_output=True).stdout


def _is_zero(sha: str) -> bool:
    return set(sha) == {"0"}


def _has_commit(sha: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                          capture_output=True).returncode == 0


def commits_to_push(ref_lines: str) -> list[str]:
    """List the commits a push would publish, from git's pre-push stdin.

    Each line is ``<local ref> <local sha> <remote ref> <remote sha>``. A delete
    (zero local sha) publishes nothing. An existing remote ref: remote..local.
    A new ref (or a remote sha unknown here): every commit not on any remote.
    """
    seen: set[str] = set()
    result: list[str] = []
    for line in ref_lines.splitlines():
        parts = line.split()
        if len(parts) != 4 or _is_zero(parts[1]):
            continue
        local, remote = parts[1], parts[3]
        if not _is_zero(remote) and _has_commit(remote):
            revs = _git("rev-list", local, f"^{remote}")
        else:
            revs = _git("rev-list", local, "--not", "--remotes")
        for sha in revs.decode("ascii", "replace").split():
            if sha not in seen:
                seen.add(sha)
                result.append(sha)
    return result


def scan_push(ref_lines: str) -> int:
    """Pre-push check: exit code 1 if any pushed commit adds a suspicious line."""
    try:
        commits = commits_to_push(ref_lines)
        diff = subprocess.run(
            ["git", "diff-tree", "--stdin", "-p", "--cc", "-U0", "--root", "--no-color",
             "--no-ext-diff", "--no-textconv"],
            input=("\n".join(commits) + "\n").encode("ascii"), check=True,
            capture_output=True).stdout if commits else b""
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"secret-scan: cannot list the pushed commits ({exc}); push blocked.",
              file=sys.stderr)
        return 1
    hits = find_secrets_in_diff(diff.decode("utf-8", "replace"))
    for commit, path, number, rule in hits:
        print(f"{commit[:12]} {path}:{number}: possible {rule} (value hidden)", file=sys.stderr)
    if hits:
        print(f"secret-scan: {len(hits)} possible secret(s) in commits about to be pushed. "
              "A new commit that removes a key does not help: the old commit would still "
              "be published. Stop: the history must be cleaned first (only on the user's "
              "order) and the key must be replaced. A false positive is also already "
              f"in those commits: '{ALLOW_MARK}' added later does not change them; ask "
              "the user.", file=sys.stderr)
        return 1
    return 0


def _staged_files() -> list[tuple[str, str]]:
    names = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z")
    result = []
    for name in names.decode("utf-8", "replace").split("\0"):
        if name:
            blob = _git("show", f":{name}")
            result.append((name, blob.decode("utf-8", "replace")))
    return result


def _tracked_files() -> list[tuple[str, str]]:
    root = Path(_git("rev-parse", "--show-toplevel").decode("utf-8", "replace").strip())
    names = _git("-C", str(root), "ls-files", "-z").decode("utf-8", "replace").split("\0")
    return [(n, (root / n).read_text("utf-8", "replace")) for n in names
            if n and (root / n).is_file() and not (root / n).is_symlink()]


def main(argv: list[str]) -> int:
    if argv == ["--push"]:
        return scan_push(sys.stdin.read())
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
