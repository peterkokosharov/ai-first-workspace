#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Functional tests for tools/autodiscovery.py.

Checks OS, RAM, processor, Python version, git, bash, and inventory db state.
No secrets are printed. Self-contained: the CLI runs against a temporary inventory
database (created with ``inventory.py init`` via ``INVENTORY_DB``), never the real
``data/inventory.db``, and with ``--no-secret-probe`` so the OS secret store is not
touched.
"""

from __future__ import annotations

import importlib.util
import io
import ctypes
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SUT = Path(__file__).resolve().parents[1] / "autodiscovery.py"  # tools/autodiscovery.py


def _load_sut():
    spec = importlib.util.spec_from_file_location("autodiscovery", SUT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ad = _load_sut()


INVENTORY_TOOL = SUT.parent / "inventory.py"
_TMP: tempfile.TemporaryDirectory | None = None
_ENV: dict[str, str] = {}


def setUpModule():
    """Create a throw-away inventory DB with the project's own init code."""
    global _TMP, _ENV
    _TMP = tempfile.TemporaryDirectory(prefix="autodiscovery-test-")
    _ENV = dict(os.environ, INVENTORY_DB=str(Path(_TMP.name) / "inventory.db"))
    result = subprocess.run([sys.executable, "-I", str(INVENTORY_TOOL), "init"],
                            capture_output=True, text=True, timeout=60, env=_ENV)
    if result.returncode != 0:
        raise unittest.SkipTest(f"inventory.py init failed in a temp dir: {result.stderr}")


def tearDownModule():
    if _TMP is not None:
        _TMP.cleanup()


def _run(args=None):
    cmd = [sys.executable, "-I", str(SUT), "--no-secret-probe"] + (args or [])
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=_ENV)


class TestAutodiscoveryFunctions(unittest.TestCase):
    def test_os_string(self):
        text = ad.check_os()
        self.assertIsInstance(text, str)
        self.assertTrue(len(text) > 0)

    def test_processor_string(self):
        text = ad.check_processor()
        self.assertIsInstance(text, str)
        self.assertTrue(len(text) > 0)

    def test_ram_string(self):
        text = ad.check_ram()
        self.assertIsInstance(text, str)
        self.assertTrue(len(text) > 0)

    def test_python_string(self):
        text = ad.check_python()
        self.assertIsInstance(text, str)
        self.assertRegex(text, r"\d+\.\d+\.\d+")

    def test_git_bool(self):
        self.assertIsInstance(ad.check_git(), bool)

    def test_bash_bool(self):
        self.assertIsInstance(ad.check_bash(), bool)


class TestWindowsRam(unittest.TestCase):
    """GlobalMemoryStatusEx with a fake kernel32 (runs on every OS)."""

    def test_struct_size_matches_win32(self):
        self.assertEqual(ctypes.sizeof(ad.MEMORYSTATUSEX), 64)

    def test_reads_total_phys(self):
        def fake_call(ref):
            mem = ctypes.cast(ref, ctypes.POINTER(ad.MEMORYSTATUSEX)).contents
            self.assertEqual(mem.dwLength, 64)
            mem.ullTotalPhys = 8 * 1024 ** 3
            return 1

        kernel32 = mock.Mock()
        kernel32.GlobalMemoryStatusEx.side_effect = fake_call
        self.assertEqual(ad._windows_ram_mb(kernel32), 8192)

    def test_failed_call_returns_none(self):
        kernel32 = mock.Mock()
        kernel32.GlobalMemoryStatusEx.return_value = 0
        self.assertIsNone(ad._windows_ram_mb(kernel32))

    @unittest.skipUnless(sys.platform == "win32", "real Windows API only on Windows")
    def test_real_windows_ram_is_positive(self):
        self.assertGreater(ad._windows_ram_mb(), 0)


class TestCLIOutput(unittest.TestCase):
    def test_runs_and_prints_header(self):
        result = _run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("=== Portable workspace auto-discovery ===", result.stdout)
        self.assertIn("OS:", result.stdout)
        self.assertIn("Processor:", result.stdout)
        self.assertIn("RAM:", result.stdout)
        self.assertIn("Python:", result.stdout)
        self.assertIn("git:", result.stdout)
        self.assertIn("bash:", result.stdout)

    def test_reports_minimum(self):
        result = _run()
        self.assertIn("Minimum met", result.stdout)

    def test_secret_probe_skipped(self):
        result = _run()
        self.assertIn("secret store:        not checked", result.stdout)

    def test_probe_write_flag_exists(self):
        result = subprocess.run([sys.executable, "-I", str(SUT), "--help"],
                                capture_output=True, text=True, timeout=30, env=_ENV)
        self.assertIn("--probe-write", result.stdout)
        self.assertIn("--no-secret-probe", result.stdout)

    def test_reports_secret_and_inventory_present(self):
        result = _run()
        self.assertIn("tools/secret.py:     present", result.stdout)
        self.assertIn("tools/inventory.py:  present", result.stdout)

    def test_reports_inventory_exists(self):
        result = _run()
        self.assertIn("data/inventory.db:   exists", result.stdout)

    def test_prints_optional_notes(self):
        result = _run()
        self.assertIn("GitHub token and email are OPTIONAL", result.stdout)
        self.assertIn("auto' never falls back to plaintext", result.stdout)


class TestSettings(unittest.TestCase):
    def test_load_settings_returns_dict(self):
        settings = ad.load_settings()
        self.assertIsInstance(settings, dict)

    def test_load_settings_has_runtime_keys(self):
        settings = ad.load_settings()
        self.assertIsInstance(settings, dict)
        self.assertIn("opencode", settings)
        self.assertIn("merman", settings)
        self.assertIn("git", settings)
        self.assertIn("bash", settings)
        self.assertIn("python", settings)
        self.assertIn("node", settings)

    def test_check_opencode_bool(self):
        self.assertIsInstance(ad.check_opencode(), bool)

    def test_check_merman_bool(self):
        self.assertIsInstance(ad.check_merman(), bool)


class TestCLIRuntimeOutput(unittest.TestCase):
    def test_cli_reports_opencode(self):
        result = _run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("opencode:", result.stdout)

    def test_cli_reports_merman(self):
        result = _run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("merman:", result.stdout)

    def test_cli_reports_node(self):
        result = _run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("node:", result.stdout)

    def test_cli_reports_python_path(self):
        result = _run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("Python:", result.stdout)

    def test_cli_reports_docker(self):
        result = _run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("docker:", result.stdout)

    def test_cli_reports_npm(self):
        result = _run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("npm:", result.stdout)

    def test_cli_reports_docker_compose(self):
        result = _run()
        self.assertEqual(result.returncode, 0)
        self.assertIn("docker-compose:", result.stdout)


class TestSettingsRuntimeKeys(unittest.TestCase):
    def test_load_settings_has_all_keys(self):
        settings = ad.load_settings()
        expected = {"opencode", "merman", "git", "bash", "python", "node",
                    "docker", "npm", "docker-compose"}
        self.assertTrue(expected.issubset(set(settings.keys())),
                        f"missing keys: {expected - set(settings.keys())}")


class TestInventoryDbMissing(unittest.TestCase):
    def test_db_missing(self):
        tmp = tempfile.mkdtemp(prefix="autodiscovery-test-")
        db_path = Path(tmp) / "inventory.db"
        with mock.patch.object(ad, "INVENTORY_DB", db_path):
            exists, has_tables = ad.check_inventory_db()
        self.assertFalse(exists)
        self.assertFalse(has_tables)


class TestInventoryDbEmpty(unittest.TestCase):
    def test_db_exists_but_no_tables(self):
        tmp = tempfile.mkdtemp(prefix="autodiscovery-test-")
        db_path = Path(tmp) / "inventory.db"
        conn = sqlite3.connect(str(db_path))
        conn.close()
        with mock.patch.object(ad, "INVENTORY_DB", db_path):
            exists, has_tables = ad.check_inventory_db()
        self.assertTrue(exists)
        self.assertFalse(has_tables)


class TestSecretStoreCheck(unittest.TestCase):
    """check_secret_store with a fake runner: the real secret store is never touched."""

    def fake(self, stdout="", code=0):
        calls = []

        def run(cmd, **kwargs):
            calls.append(cmd)
            return mock.Mock(returncode=code, stdout=stdout)

        return run, calls

    def test_default_is_read_only_setup(self):
        run, calls = self.fake("native stores (priority order):\n  yes wcm  x\n"
                               "auto would use: wcm\n")
        self.assertEqual(ad.check_secret_store(run=run), (True, "wcm"))
        self.assertEqual(calls[0][-1], "setup")
        self.assertNotIn("probe", calls[0])

    def test_default_reports_no_store(self):
        run, _ = self.fake("auto would use: none\n")
        self.assertFalse(ad.check_secret_store(run=run)[0])

    def test_probe_only_with_write(self):
        run, calls = self.fake("ok: wcm (write, read and delete)\n")
        self.assertEqual(ad.check_secret_store(write=True, run=run), (True, "probe ok"))
        self.assertEqual(calls[0][-1], "probe")

    def test_failure(self):
        run, _ = self.fake("", code=3)
        self.assertEqual(ad.check_secret_store(run=run), (False, ""))

    def test_main_default_uses_read_only_check(self):
        with mock.patch.object(ad, "check_secret_store", return_value=(True, "wcm")) as check, \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            ad.main([])
        check.assert_called_once_with()
        self.assertIn("available: wcm (read-only check)", out.getvalue())

    def test_main_probe_write(self):
        with mock.patch.object(ad, "check_secret_store", return_value=(True, "probe ok")) as check, \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            ad.main(["--probe-write"])
        check.assert_called_once_with(write=True)

    def test_main_no_secret_probe_skips(self):
        with mock.patch.object(ad, "check_secret_store") as check, \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            ad.main(["--no-secret-probe", "--probe-write"])
        check.assert_not_called()


if __name__ == "__main__":
    unittest.main()
