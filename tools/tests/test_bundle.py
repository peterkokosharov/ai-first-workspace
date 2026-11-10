# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Tests for tools/bundle.py.  A fake core and a fake project; nothing is run live."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from tools import bundle


def write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=T", "-c", "user.email=t@example.com",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


def commit_all(repo: Path, message: str = "m") -> None:
    git(repo, "add", "-f", "-A")
    git(repo, "commit", "-q", "-m", message)


def make_core(root: Path) -> None:
    write(root / "AGENTS.md", "# rules\n")
    write(root / "tools" / "secret.py", "MARK = 'core'\n")
    write(root / "tools" / "bundle.py", "# placeholder\n")
    write(root / "lib" / "kikolib" / "__init__.py", "")
    write(root / "data" / "inventory.db", "sqlite")
    write(root / "data" / "schema.sql", "-- schema\n")
    write(root / "settings.json", '{"git": {"token_key": "personal/x/github_token"}}\n')
    write(root / "settings.json.bak-20260101-000000-000000", "{}\n")
    write(root / "out" / "report.md", "private\n")
    write(root / "tools" / "__pycache__" / "x.pyc", "cache")
    write(root / "projects" / "other" / "AGENTS.md", "other project\n")
    # the core is copied from `git ls-files`: track everything, then add untracked files
    git(root, "init", "-q")
    commit_all(root)
    write(root / ".env", "TOKEN=local\n")
    write(root / "scratch.db", "sqlite")
    write(root / ".venv" / "pyvenv.cfg", "home = x\n")


def make_project(root: Path, name: str = "demo") -> None:
    project = root / "projects" / name
    write(project / "AGENTS.md", "# project rules\n")
    write(project / ".git" / "HEAD", "ref: refs/heads/main\n")
    write(project / "__pycache__" / "x.pyc", "cache")
    write(project / "settings.json", '{"core": "../.."}\n')
    write(project / "tools" / "__init__.py", "")
    write(project / "tools" / "core.py",
          "class Found:\n    origin = 'parent'\n\n\n"
          "def find(root, environ=None):\n    return Found()\n")
    write(project / "tools" / "tests" / "__init__.py", "")
    write(project / "tools" / "tests" / "test_ok.py",
          "import unittest\n\n\nclass T(unittest.TestCase):\n"
          "    def test_ok(self):\n        self.assertTrue(True)\n")


class TestBuild(unittest.TestCase):
    def test_copies_core_and_project_without_local_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            make_project(root)
            target, result = bundle.build(root, "demo", Path(tmp) / "bundles",
                                          run_tests=False)
            self.assertIsNone(result)
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / "tools" / "secret.py").is_file())
            self.assertTrue((target / "projects" / "demo" / "AGENTS.md").is_file())
            self.assertTrue((target / "projects" / "demo" / ".git" / "HEAD").is_file())
            self.assertFalse((target / "data" / "inventory.db").exists())
            self.assertFalse((target / "settings.json").exists())
            self.assertFalse((target / "projects" / "demo" / "settings.json").exists())
            self.assertFalse((target / ".git").exists())
            self.assertFalse((target / "out").exists())
            self.assertFalse((target / "projects" / "other").exists())
            self.assertFalse(list(target.rglob("*.pyc")))
            self.assertFalse(list(target.rglob("settings.json.bak-*")))
            # the recipient's `git add -A` must see the project
            self.assertNotIn("/projects", (target / ".gitignore").read_text(encoding="utf-8"))

    def test_refuses_to_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            make_project(root)
            out = Path(tmp) / "bundles"
            bundle.build(root, "demo", out, run_tests=False)
            with self.assertRaises(FileExistsError):
                bundle.build(root, "demo", out, run_tests=False)
            bundle.build(root, "demo", out, force=True, run_tests=False)

    def test_unknown_project_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            with self.assertRaises(FileNotFoundError):
                bundle.build(root, "nope", Path(tmp) / "bundles", run_tests=False)

    def test_a_name_is_one_folder_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            with self.assertRaises(ValueError):
                bundle.build(root, "../demo", Path(tmp) / "bundles", run_tests=False)
            with self.assertRaises(ValueError):
                bundle.build(root, "a/b", Path(tmp) / "bundles", run_tests=False)

    def test_refuses_a_target_inside_the_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            make_project(root)
            with self.assertRaises(ValueError):
                bundle.build(root, "demo", root, run_tests=False)
            with self.assertRaises(ValueError):
                bundle.build(root, "demo", root / "projects", run_tests=False)
            # out/ is the one place inside the workspace a bundle may live
            bundle.build(root, "demo", root / "out" / "bundles", run_tests=False)

    def test_runs_the_projects_tests_in_the_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            make_project(root)
            _target, result = bundle.build(root, "demo", Path(tmp) / "bundles")
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_refuses_a_project_that_reaches_another_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            make_project(root)
            write(root / "projects" / "demo" / "tools" / "core.py",
                  "class Found:\n    origin = 'CORE'\n\n\n"
                  "def find(root, environ=None):\n    return Found()\n")
            with self.assertRaises(ValueError):
                bundle.build(root, "demo", Path(tmp) / "bundles", run_tests=False)


    def test_untracked_files_are_not_bundled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            make_project(root)
            target, _ = bundle.build(root, "demo", Path(tmp) / "bundles", run_tests=False)
            self.assertTrue((target / "tools" / "secret.py").is_file())
            self.assertFalse((target / ".env").exists())
            self.assertFalse((target / "scratch.db").exists())
            self.assertFalse((target / ".venv").exists())

    def test_refuses_a_target_that_contains_the_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            # out/<name> == the workspace itself: --force would delete it
            root = Path(tmp) / "demo"
            make_core(root)
            make_project(root)
            with self.assertRaises(ValueError):
                bundle.build(root, "demo", Path(tmp), force=True, run_tests=False)
            with self.assertRaises(ValueError):
                bundle.build(root, "demo", root, force=True, run_tests=False)
            with self.assertRaises(ValueError):
                bundle._check_out(root, Path(tmp))  # the workspace lies inside it
            with self.assertRaises(ValueError):
                bundle._check_out(root, root / "projects" / "demo")
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / "projects" / "demo" / "AGENTS.md").is_file())


class TestCheck(unittest.TestCase):
    def test_a_clean_bundle_has_no_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "b"
            write(target / "AGENTS.md")
            self.assertEqual(bundle.check(target), [])

    def test_local_files_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "b"
            write(target / "data" / "inventory.db")
            write(target / "settings.json")
            write(target / "projects" / "demo" / "settings.json")
            write(target / ".git" / "HEAD")
            problems = bundle.check(target)
            self.assertEqual(len(problems), 4)

    def test_a_secret_in_the_bundled_core_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "b"
            write(target / "tools" / "x.py", "key = '" + "ghp" + "_" + "A1b2C3d4E5" * 4 + "'\n")
            problems = bundle.check(target)
            self.assertEqual(len(problems), 1)
            self.assertIn("tools/x.py:1", problems[0])
            self.assertNotIn("A1b2C3d4E5", problems[0])

    def test_a_secret_in_the_project_history_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            make_project(root)
            project = root / "projects" / "demo"
            git(project, "init", "-q")
            commit_all(project, "first")
            write(project / "old.txt", "hf" + "_" + "A1b2C3d4E5" * 4 + "\n")
            commit_all(project, "oops")
            (project / "old.txt").unlink()
            commit_all(project, "remove it")  # the working tree is clean, the history is not
            target, _ = bundle.build(root, "demo", Path(tmp) / "bundles", run_tests=False)
            problems = bundle.check(target)
            self.assertEqual(len(problems), 1, problems)
            self.assertIn("history", problems[0])
            self.assertIn("old.txt", problems[0])
            self.assertNotIn("A1b2C3d4E5", problems[0])

    def test_a_clean_project_history_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "workspace"
            make_core(root)
            make_project(root)
            project = root / "projects" / "demo"
            git(project, "init", "-q")
            commit_all(project, "first")
            target, _ = bundle.build(root, "demo", Path(tmp) / "bundles", run_tests=False)
            self.assertEqual(bundle.check(target), [])


if __name__ == "__main__":
    unittest.main()
