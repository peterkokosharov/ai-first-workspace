#!/usr/bin/env python3
"""Functional tests for tools/autodiscovery.py.

Checks OS, RAM, processor, Python version, git, bash, and inventory db state.
No secrets are printed.
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SUT = Path(__file__).resolve().parents[1] / "autodiscovery.py"  # tools/autodiscovery.py
ROOT = Path(__file__).resolve().parents[1]                      # project root
DATA = ROOT / "data"
INVENTORY_DB = DATA / "inventory.db"


def _load_sut():
    spec = importlib.util.spec_from_file_location("autodiscovery", SUT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ad = _load_sut()


def _run(args=None):
    cmd = [sys.executable, str(SUT)] + (args or [])
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


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
        ad.INVENTORY_DB = db_path
        exists, has_tables = ad.check_inventory_db()
        self.assertFalse(exists)
        self.assertFalse(has_tables)


class TestInventoryDbEmpty(unittest.TestCase):
    def test_db_exists_but_no_tables(self):
        tmp = tempfile.mkdtemp(prefix="autodiscovery-test-")
        db_path = Path(tmp) / "inventory.db"
        conn = sqlite3.connect(str(db_path))
        conn.close()
        ad.INVENTORY_DB = db_path
        exists, has_tables = ad.check_inventory_db()
        self.assertTrue(exists)
        self.assertFalse(has_tables)


if __name__ == "__main__":
    unittest.main()
