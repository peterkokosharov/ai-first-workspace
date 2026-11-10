# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Tests for the git hooks in .githooks/ (fake keys are built at run time)."""

from __future__ import annotations

import os
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


ZERO = "0" * 40
GIT_ENV = {"GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid"}


@unittest.skipUnless(SH and GIT, "needs sh and git")
class TestPrePush(unittest.TestCase):
    """The hook scans the commits a push publishes, not the working tree.

    Pushes go to a bare repository in a temp folder (no network).
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name)
        self.repo, self.bare = base / "work", base / "remote.git"
        self.env = {**os.environ, **GIT_ENV}
        subprocess.run([GIT, "init", "-q", "--bare", str(self.bare)], check=True)
        subprocess.run([GIT, "init", "-q", "-b", "main", str(self.repo)], check=True)
        self.git("config", "core.autocrlf", "false")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.hooksPath", ".githooks")
        self.git("remote", "add", "origin", str(self.bare))
        (self.repo / ".githooks").mkdir()
        (self.repo / "tools").mkdir()
        shutil.copy(ROOT / ".githooks" / "pre-push", self.repo / ".githooks" / "pre-push")
        shutil.copy(ROOT / "tools" / "secret_scan.py", self.repo / "tools" / "secret_scan.py")
        self.commit("note.txt", "nothing secret here\n")
        probe = self.hook(f"refs/heads/main {self.head()} refs/heads/main {ZERO}\n")
        if "Python 3.10+ not found" in probe.stderr:
            self.skipTest("hook found no Python")

    def git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run([GIT, "-C", str(self.repo), *args], env=self.env, check=check,
                              capture_output=True, text=True)

    def commit(self, name: str, content: str) -> None:
        (self.repo / name).write_text(content, encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-q", "-m", f"change {name}")

    def head(self) -> str:
        return self.git("rev-parse", "HEAD").stdout.strip()

    def hook(self, stdin: str) -> subprocess.CompletedProcess:
        return subprocess.run([SH, ".githooks/pre-push", "origin", str(self.bare)],
                              cwd=self.repo, env=self.env, input=stdin,
                              capture_output=True, text=True)

    def push(self, *refs: str) -> subprocess.CompletedProcess:
        return self.git("push", "-q", "origin", *refs, check=False)

    def remote_has(self, ref: str) -> bool:
        return subprocess.run([GIT, "--git-dir", str(self.bare), "rev-parse", "--verify",
                               "-q", ref], capture_output=True).returncode == 0

    def test_clean_push_passes(self):
        result = self.push("main")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.remote_has("refs/heads/main"))

    def test_key_added_then_removed_still_blocks_and_value_is_hidden(self):
        self.commit("note.txt", "token nvapi-" + FAKE + "\n")
        self.commit("note.txt", "nothing secret here\n")
        self.assertNotIn(FAKE, (self.repo / "note.txt").read_text(encoding="utf-8"))
        result = self.push("main")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("note.txt:1", result.stderr)
        self.assertIn("history must be cleaned", result.stderr)
        self.assertNotIn(FAKE, result.stderr + result.stdout)
        self.assertFalse(self.remote_has("refs/heads/main"))

    def test_key_in_older_commit_of_existing_branch_blocks(self):
        self.assertEqual(self.push("main").returncode, 0)
        old = self.head()
        self.commit("other.txt", "token nvapi-" + FAKE + "\n")
        self.commit("other.txt", "clean\n")
        result = self.hook(f"refs/heads/main {self.head()} refs/heads/main {old}\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("other.txt:1", result.stderr)
        self.assertNotIn(FAKE, result.stderr)

    def test_branch_delete_is_allowed(self):
        self.commit("note.txt", "token nvapi-" + FAKE + "\n")
        keyed = self.head()
        result = self.hook(f"(delete) {ZERO} refs/heads/old {keyed}\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.git("checkout", "-q", "-b", "gone")
        self.git("reset", "-q", "--hard", "HEAD~1")
        self.assertEqual(self.push("gone").returncode, 0)
        result = self.push(":gone")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.remote_has("refs/heads/gone"))

    def test_new_branch_scans_only_commits_not_on_a_remote(self):
        # A key already published (pushed without the hook) must not block a new
        # branch built on top of it; a key in the new branch's own commits must.
        self.commit("note.txt", "token nvapi-" + FAKE + "\n")
        self.assertEqual(self.git("push", "-q", "--no-verify", "origin", "main",
                                  check=False).returncode, 0)
        self.git("checkout", "-q", "-b", "feature")
        self.commit("feature.txt", "clean work\n")
        result = self.push("feature")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.git("checkout", "-q", "-b", "feature2")
        self.commit("new.txt", "token nvapi-" + FAKE + "\n")
        result = self.push("feature2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("new.txt:1", result.stderr)
        self.assertNotIn("note.txt", result.stderr)
        self.assertFalse(self.remote_has("refs/heads/feature2"))


@unittest.skipUnless(GIT, "needs git")
class TestGitignore(unittest.TestCase):
    """The repo .gitignore keeps local backups out of git (checked in a temp repo)."""

    def test_settings_backup_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run([GIT, "init", "-q", tmp], check=True)
            shutil.copy(ROOT / ".gitignore", Path(tmp) / ".gitignore")
            for name, ignored in (("settings.json.bak-20260101-000000-000000", True),
                                  ("settings.json", True),
                                  ("settings.json.example", False)):
                with self.subTest(name=name):
                    result = subprocess.run([GIT, "-C", tmp, "check-ignore", "-q", name],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0 if ignored else 1, result.stderr)


if __name__ == "__main__":
    unittest.main()
