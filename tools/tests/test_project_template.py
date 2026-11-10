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
