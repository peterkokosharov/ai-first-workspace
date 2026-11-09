# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Tests for the git hooks in .githooks/ (fake keys are built at run time)."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ("pre-commit", "pre-push")
SH = shutil.which("sh") or shutil.which("bash")
GIT = shutil.which("git")
FAKE = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


@unittest.skipUnless(SH, "no POSIX shell")
class TestHookSyntax(unittest.TestCase):
    def test_hooks_parse(self):
        for name in HOOKS:
            with self.subTest(hook=name):
                path = ROOT / ".githooks" / name
                result = subprocess.run([SH, "-n", str(path)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_hooks_have_lf_endings(self):
        for name in HOOKS:
            with self.subTest(hook=name):
                self.assertNotIn(b"\r\n", (ROOT / ".githooks" / name).read_bytes())


@unittest.skipUnless(SH and GIT, "needs sh and git")
class TestPrePush(unittest.TestCase):
    def run_hook(self, content: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run([GIT, "init", "-q", str(repo)], check=True)
            (repo / ".githooks").mkdir()
            (repo / "tools").mkdir()
            shutil.copy(ROOT / ".githooks" / "pre-push", repo / ".githooks" / "pre-push")
            shutil.copy(ROOT / "tools" / "secret_scan.py", repo / "tools" / "secret_scan.py")
            (repo / "note.txt").write_text(content, encoding="utf-8")
            subprocess.run([GIT, "-C", str(repo), "-c", "core.autocrlf=false", "add", "."],
                           check=True)
            return subprocess.run([SH, ".githooks/pre-push", "origin", "url"], cwd=repo,
                                  input="", capture_output=True, text=True)

    def test_clean_tree_passes(self):
        result = self.run_hook("nothing secret here\n")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_key_blocks_push_and_value_is_hidden(self):
        result = self.run_hook("token nvapi-" + FAKE + "\n")
        if "Python 3.10+ not found" in result.stderr:
            self.skipTest("hook found no Python")
        self.assertEqual(result.returncode, 1)
        self.assertIn("note.txt:1", result.stderr)
        self.assertNotIn(FAKE, result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
