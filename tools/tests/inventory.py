#!/usr/bin/env python3
"""Functional tests for tools/inventory.py.

Exercises init / tables / list / show / search / sql / setting over a
temporary copy of the database (via the INVENTORY_DB environment variable),
plus the committed schema and seed counts. No secrets are printed.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SUT = Path(__file__).resolve().parents[1] / "inventory.py"  # tools/inventory.py
ROOT = Path(__file__).resolve().parents[1]                  # project root
DATA = ROOT / "data"
SCHEMA = DATA / "schema.sql"
SEED = DATA / "seed.sql"
REAL_DB = DATA / "inventory.db"


def _run(args):
    env = os.environ.copy()
    cmd = [sys.executable, str(SUT)] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, env=env)


class TestInventory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="inventory-test-")
        self.db = Path(self.tmp) / "inventory.db"
        self._old_env_db = os.environ.pop("INVENTORY_DB", None)
        os.environ["INVENTORY_DB"] = str(self.db)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        if self._old_env_db is None:
            os.environ.pop("INVENTORY_DB", None)
        else:
            os.environ["INVENTORY_DB"] = self._old_env_db

    def _counts(self, db):
        conn = sqlite3.connect(str(db))
        try:
            return {
                t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in ("machines", "services", "providers", "keys",
                          "models", "tools", "settings")
            }
        finally:
            conn.close()

    def test_init_creates_schema_and_loads_seed(self):
        result = _run(["init"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.db.exists())
        counts = self._counts(self.db)
        expected = {
            "machines": 2, "services": 5, "providers": 13, "keys": 14,
            "models": 56, "tools": 6, "settings": 3,
        }
        self.assertEqual(counts, expected)

    def test_init_is_idempotent(self):
        first = _run(["init"])
        self.assertEqual(first.returncode, 0, first.stderr)
        second = _run(["init"])
        self.assertEqual(second.returncode, 0, second.stderr)

    def test_tables(self):
        _run(["init"])
        result = _run(["tables"])
        self.assertEqual(result.returncode, 0)
        for t in ("machines", "services", "providers", "keys", "models",
                  "tools", "settings", "schema_meta"):
            self.assertIn(t, result.stdout)

    def test_list(self):
        _run(["init"])
        result = _run(["list", "machines"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("q4os", result.stdout)
        self.assertIn("win10", result.stdout)

    def test_show(self):
        _run(["init"])
        result = _run(["show", "machines", "1"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("q4os", result.stdout)
        self.assertIn("name = 'q4os'", result.stdout)

    def test_show_missing(self):
        _run(["init"])
        result = _run(["show", "machines", "999"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("not found", result.stderr)

    def test_search(self):
        _run(["init"])
        result = _run(["search", "keys", "path", "github"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("github/personal/token", result.stdout)

    def test_sql_read_only(self):
        _run(["init"])
        result = _run(["sql", "SELECT name FROM machines ORDER BY name"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("q4os", result.stdout)
        self.assertIn("win10", result.stdout)

    def test_sql_write_rejected(self):
        _run(["init"])
        result = _run(["sql", "UPDATE machines SET name='x' WHERE id=1"])
        self.assertEqual(result.returncode, 3)  # usage error

    def test_setting_read_write(self):
        _run(["init"])
        result = _run(["setting", "default_backend"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("auto", result.stdout)

        result = _run(["setting", "test_key", "test_value"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("test_value", result.stdout)

        result = _run(["setting", "test_key"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("test_value", result.stdout)

    def test_setting_missing(self):
        _run(["init"])
        result = _run(["setting", "does_not_exist"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("not found", result.stderr)


if __name__ == "__main__":
    unittest.main()
