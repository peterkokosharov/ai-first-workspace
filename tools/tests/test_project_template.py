# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Tests for the glue in templates/project/tools/ (the real core.find search order)."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "templates" / "project" / "tools"


def load_core():
    spec = importlib.util.spec_from_file_location("template_core", TEMPLATE / "core.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fake_core(path: Path, agents: bool = False) -> Path:
    (path / "tools").mkdir(parents=True, exist_ok=True)
    (path / "tools" / "secret.py").write_text("MARK = 'fake'\n", encoding="utf-8")
    if agents:
        (path / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
    return path


class TestFind(unittest.TestCase):
    def setUp(self):
        self.core = load_core()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.project = self.base / "ws" / "projects" / "demo"
        (self.project / "tools").mkdir(parents=True)
        # the project's own glue and rules must never count as a core
        (self.project / "AGENTS.md").write_text("# project\n", encoding="utf-8")
        (self.project / "tools" / "secret.py").write_text("# glue\n", encoding="utf-8")

    def test_nothing_found(self):
        self.assertIsNone(self.core.find(self.project, {}))

    def test_parent(self):
        ws = fake_core(self.base / "ws", agents=True)
        found = self.core.find(self.project, {})
        self.assertEqual((found.path, found.origin), (ws, "parent"))

    def test_parent_needs_agents_md(self):
        fake_core(self.base / "ws")
        self.assertIsNone(self.core.find(self.project, {}))

    def test_settings_beats_parent(self):
        fake_core(self.base / "ws", agents=True)
        other = fake_core(self.base / "other")
        (self.project / "settings.json").write_text('{"core": "../../../other"}\n',
                                                    encoding="utf-8")
        found = self.core.find(self.project, {})
        self.assertEqual((found.path, found.origin), (other, "settings"))

    def test_env_beats_settings(self):
        fake_core(self.base / "ws", agents=True)
        fake_core(self.base / "other")
        env_core = fake_core(self.base / "envcore")
        (self.project / "settings.json").write_text('{"core": "../../../other"}\n',
                                                    encoding="utf-8")
        found = self.core.find(self.project, {"CORE": str(env_core)})
        self.assertEqual((found.path, found.origin), (env_core, "CORE"))

    def test_vendor_beats_env(self):
        env_core = fake_core(self.base / "envcore")
        vendor = fake_core(self.project / "vendor")
        found = self.core.find(self.project, {"CORE": str(env_core)})
        self.assertEqual((found.path, found.origin), (vendor, "vendor"))

    def test_a_bad_candidate_falls_through(self):
        ws = fake_core(self.base / "ws", agents=True)
        (self.project / "settings.json").write_text('{"core": "nowhere"}\n', encoding="utf-8")
        found = self.core.find(self.project, {"CORE": str(self.base / "missing")})
        self.assertEqual((found.path, found.origin), (ws, "parent"))


def make_dir_link(link: Path, target: Path) -> bool:
    """A real directory link (junction on Windows, symlink elsewhere); False if impossible."""
    try:
        if os.name == "nt":
            import _winapi
            _winapi.CreateJunction(str(target), str(link))
        else:
            os.symlink(target, link, target_is_directory=True)
        return True
    except (OSError, ImportError, AttributeError):
        pass
    if os.name == "nt":
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                              capture_output=True)
        return done.returncode == 0
    return False


def remove_link(link: Path) -> None:
    """Remove the link itself; never rmtree (that could delete the target's files)."""
    if os.name == "nt":
        os.rmdir(link)
    else:
        os.unlink(link)


class TestLinkedProject(unittest.TestCase):
    """core/projects/X is a real link to a repo kept elsewhere."""

    def setUp(self):
        self.core = load_core()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        self.ws = fake_core(base / "core", agents=True)
        (self.ws / "projects").mkdir()
        self.repo = base / "repos" / "X"
        (self.repo / "tools").mkdir(parents=True)
        (self.repo / "AGENTS.md").write_text("# project\n", encoding="utf-8")
        (self.repo / "tools" / "secret.py").write_text("# glue\n", encoding="utf-8")
        self.link = self.ws / "projects" / "X"
        if not make_dir_link(self.link, self.repo):
            self.skipTest("cannot create a junction or symlink on this machine")
        self.addCleanup(self._unlink)

    def _unlink(self):
        if os.path.lexists(self.link):
            remove_link(self.link)
        self.assertTrue((self.repo / "AGENTS.md").is_file())  # the target survives

    def test_from_the_link_the_core_is_found_by_parent(self):
        found = self.core.find(self.link, {})
        self.assertEqual((found.path, found.origin), (self.ws, "parent"))

    def test_from_the_real_path_nothing_is_found(self):
        self.assertIsNone(self.core.find(self.repo, {}))

    def test_from_the_real_path_core_env_is_used(self):
        found = self.core.find(self.repo, {"CORE": str(self.ws)})
        self.assertEqual((found.path, found.origin), (self.ws, "CORE"))

    def test_from_the_real_path_settings_core_is_used(self):
        (self.repo / "settings.json").write_text(
            '{"core": %s}' % __import__("json").dumps(str(self.ws)), encoding="utf-8")
        found = self.core.find(self.repo, {})
        self.assertEqual((found.path, found.origin), (self.ws, "settings"))

    def test_install_from_the_link_uses_the_unresolved_path(self):
        saved = (list(sys.path), sys.modules.get("secret"))
        self.addCleanup(lambda: (sys.path.__setitem__(slice(None), saved[0]),
                                 sys.modules.pop("secret", None),
                                 saved[1] and sys.modules.__setitem__("secret", saved[1])))
        found = self.core.install(self.link)
        self.assertEqual((found.path, found.origin), (self.ws, "parent"))

    def test_relative_launch_with_pwd_keeps_the_link(self):
        # POSIX getcwd() is physical; $PWD still names the link. On Windows no PWD logic is needed.
        code = ("import importlib.util as u, pathlib; "
                "s = u.spec_from_file_location('c', %r); m = u.module_from_spec(s); "
                "s.loader.exec_module(m); f = m.find(pathlib.Path('.'), {'PWD': %r}); "
                "print(f.origin, f.path)") % (str(TEMPLATE / "core.py"), str(self.link))
        done = subprocess.run([sys.executable, "-I", "-c", code], cwd=self.link,
                              env=dict(os.environ, PWD=str(self.link)),
                              capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout.split(" ", 1)[0], "parent")
        self.assertEqual(Path(done.stdout.split(" ", 1)[1].strip()), self.ws)

    def test_a_plain_folder_inside_the_core_is_found_by_parent(self):
        plain = self.ws / "projects" / "plain"
        plain.mkdir()
        found = self.core.find(plain, {})
        self.assertEqual((found.path, found.origin), (self.ws, "parent"))

    def test_parent_real_when_only_the_resolved_path_leads_to_a_core(self):
        # the lexical path has no core above it; the real one does
        base = Path(self._tmp.name).resolve() / "elsewhere"
        base.mkdir()
        outer = base / "link"
        inner = self.ws / "projects" / "real"
        inner.mkdir()
        if not make_dir_link(outer, inner):
            self.skipTest("cannot create a second link")
        self.addCleanup(remove_link, outer)
        found = self.core.find(outer, {})
        self.assertEqual((found.path, found.origin), (self.ws, "parent-real"))


class TestInstall(unittest.TestCase):
    def test_a_project_from_the_template_reaches_the_real_core(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            shutil.copytree(TEMPLATE, project / "tools")
            env = {k: v for k, v in os.environ.items() if k != "CORE"}
            env["CORE"] = str(ROOT)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            code = ("import tools, secret, sys; "
                    "print(hasattr(secret, 'make_backend'), 'secret' in sys.modules)")
            run = subprocess.run([sys.executable, "-c", code], cwd=project, env=env,
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout.strip(), "True True")

    def test_no_core_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "demo"
            shutil.copytree(TEMPLATE, project / "tools")
            env = {k: v for k, v in os.environ.items() if k != "CORE"}
            run = subprocess.run([sys.executable, "-c", "import tools"], cwd=project,
                                 env=env, capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("no core found", run.stderr)


if __name__ == "__main__":
    unittest.main()
