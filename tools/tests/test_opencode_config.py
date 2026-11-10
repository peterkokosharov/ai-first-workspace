# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Tests for tools/opencode_config.py: config path per OS, backup, dry run."""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

SUT = Path(__file__).resolve().parents[1] / "opencode_config.py"
_spec = importlib.util.spec_from_file_location("opencode_config", SUT)
oc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oc)


class TestConfigPath(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_linux_default(self):
        self.assertEqual(oc.config_dir({}, "linux", self.home), self.home / ".config" / "opencode")

    def test_windows_uses_dot_config_in_profile(self):
        self.assertEqual(oc.config_dir({}, "win32", self.home), self.home / ".config" / "opencode")

    def test_xdg_config_home_wins(self):
        env = {"XDG_CONFIG_HOME": str(self.home / "x")}
        self.assertEqual(oc.config_dir(env, "linux", self.home), self.home / "x" / "opencode")

    def test_tde_folder_only_in_tde_session(self):
        (self.home / ".configtde").mkdir()
        tde = self.home / ".configtde" / "opencode"
        self.assertEqual(oc.config_dir({"TDE_FULL_SESSION": "true"}, "linux", self.home), tde)
        self.assertEqual(oc.config_dir({"XDG_CURRENT_DESKTOP": "Trinity"}, "linux", self.home), tde)
        # Mint / Cinnamon: standard folder even if a .configtde folder exists.
        self.assertEqual(oc.config_dir({"XDG_CURRENT_DESKTOP": "X-Cinnamon"}, "linux", self.home),
                         self.home / ".config" / "opencode")

    def test_config_file_prefers_existing_jsonc_and_env_override(self):
        folder = self.home / ".config" / "opencode"
        self.assertEqual(oc.config_file({}, "linux", self.home), folder / "opencode.json")
        folder.mkdir(parents=True)
        (folder / "opencode.jsonc").write_text("{}", encoding="utf-8")
        self.assertEqual(oc.config_file({}, "linux", self.home), folder / "opencode.jsonc")
        custom = str(self.home / "my.json")
        self.assertEqual(oc.config_file({"OPENCODE_CONFIG": custom}, "linux", self.home), Path(custom))


class TestWriteJson(unittest.TestCase):
    def test_backup_then_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            path.write_text('{"old": 1}\n', encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                saved = oc.write_json(path, {"new": 2})
            self.assertRegex(saved.name, r"^opencode\.json\.bak-\d{8}-\d{6}-\d{6}$")
            self.assertEqual(json.loads(saved.read_text(encoding="utf-8")), {"old": 1})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"new": 2})

    def test_backups_in_the_same_instant_never_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            path.write_text("1", encoding="utf-8")
            first = oc.backup(path, now=1000.5)
            path.write_text("2", encoding="utf-8")
            second = oc.backup(path, now=1000.5)
            self.assertNotEqual(first, second)
            self.assertEqual(first.read_text(encoding="utf-8"), "1")
            self.assertEqual(second.read_text(encoding="utf-8"), "2")
            self.assertTrue(second.name.endswith("-1"))

    def test_failed_write_keeps_old_file_and_leaves_no_temp_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            path.write_text('{"old": 1}', encoding="utf-8")
            with mock.patch.object(oc.os, "replace", side_effect=OSError(13, "denied")), \
                    redirect_stdout(io.StringIO()):
                with self.assertRaises(oc.ConfigError):
                    oc.write_json(path, {"new": 2})
            self.assertEqual(path.read_text(encoding="utf-8"), '{"old": 1}')
            self.assertEqual([f for f in Path(tmp).iterdir() if f.name.endswith(".tmp")], [])

    def test_new_file_needs_no_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "opencode.json"
            self.assertIsNone(oc.write_json(path, {"a": 1}))
            self.assertTrue(path.is_file())

    def test_dry_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "opencode.json"
            path.write_text("{}", encoding="utf-8")
            out = io.StringIO()
            with redirect_stdout(out):
                oc.write_json(path, {"a": 1}, dry_run=True)
            self.assertIn("[dry-run]", out.getvalue())
            self.assertEqual(path.read_text(encoding="utf-8"), "{}")
            self.assertEqual(list(Path(tmp).iterdir()), [path])


if __name__ == "__main__":
    unittest.main()
