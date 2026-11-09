#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
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

    def _service_count(self):
        conn = sqlite3.connect(str(self.db))
        try:
            return conn.execute("SELECT count(*) FROM services").fetchone()[0]
        finally:
            conn.close()

    def test_sql_with_delete_fails_and_rows_survive(self):
        _run(["init"])
        before = self._service_count()
        result = _run(["sql", "WITH x AS (SELECT 1) DELETE FROM services"])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._service_count(), before)

    def test_sql_plain_writes_fail_and_rows_survive(self):
        _run(["init"])
        before = self._service_count()
        for statement in ("DELETE FROM services",
                          "UPDATE services SET name = 'x' WHERE id = 1",
                          "INSERT INTO services (name) VALUES ('evil')"):
            result = _run(["sql", statement])
            self.assertNotEqual(result.returncode, 0, statement)
        self.assertEqual(self._service_count(), before)
        result = _run(["sql", "SELECT name FROM services WHERE id = 1"])
        self.assertIn("github", result.stdout)

    def test_sql_missing_db_is_an_error_and_creates_nothing(self):
        result = _run(["sql", "SELECT 1"])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.db.exists())

    def test_key_for_service(self):
        _run(["init"])
        result = _run(["key", "github"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("github/personal/token", result.stdout)
        self.assertIn("service github", result.stdout)

    def test_key_for_provider_is_case_insensitive(self):
        _run(["init"])
        result = _run(["key", "NVIDIA"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nvidia/personal/api_key", result.stdout)
        self.assertIn("provider nvidia", result.stdout)

    def test_key_unknown_name(self):
        _run(["init"])
        result = _run(["key", "nosuchservice"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("add-key", result.stderr)

    def test_add_service_and_key_then_look_up(self):
        _run(["init"])
        result = _run(["add-service", "mymail", "mail", "--account", "personal"])
        self.assertEqual(result.returncode, 0, result.stderr)
        result = _run(["add-key", "mymail/personal/app_password", "--service", "mymail"])
        self.assertEqual(result.returncode, 0, result.stderr)
        result = _run(["key", "mymail"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mymail/personal/app_password", result.stdout)
        conn = sqlite3.connect(str(self.db))
        try:
            row = conn.execute("SELECT kind, provider_id FROM keys "
                               "WHERE path = 'mymail/personal/app_password'").fetchone()
        finally:
            conn.close()
        self.assertEqual(row, ("app_password", None))

    def test_add_key_for_provider(self):
        _run(["init"])
        result = _run(["add-key", "nvidia/work/api_key", "--provider", "nvidia",
                       "--status", "planned"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("nvidia/work/api_key", _run(["key", "nvidia"]).stdout)

    def test_add_service_twice_is_refused(self):
        _run(["init"])
        result = _run(["add-service", "github", "code hosting"])
        self.assertEqual(result.returncode, 3)

    def test_add_key_rejects_bad_paths(self):
        _run(["init"])
        for bad in ("UPPER/case", "single", "a//b", "a/../b", "a/b c", "a/b/"):
            result = _run(["add-key", bad, "--service", "github"])
            self.assertEqual(result.returncode, 3, bad)
        # a leading "/" (passed in-process: Git Bash on Windows rewrites "/x" arguments)
        import importlib.util
        spec = importlib.util.spec_from_file_location("inventory_sut", SUT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with self.assertRaises(module.UsageError):
            module._validate_key_path("/github/token")

    def test_add_key_needs_exactly_one_owner(self):
        _run(["init"])
        self.assertEqual(_run(["add-key", "a/b"]).returncode, 3)
        self.assertEqual(_run(["add-key", "a/b", "--service", "github",
                               "--provider", "nvidia"]).returncode, 3)

    def test_add_key_unknown_owner(self):
        _run(["init"])
        result = _run(["add-key", "x/personal/token", "--service", "nosuch"])
        self.assertEqual(result.returncode, 1)

    def test_add_key_duplicate_is_refused(self):
        _run(["init"])
        result = _run(["add-key", "github/personal/token", "--service", "github"])
        self.assertEqual(result.returncode, 3)

    def test_add_without_database_creates_nothing(self):
        result = _run(["add-service", "x", "mail"])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.db.exists())

    def test_list_table_is_one_line_per_row(self):
        _run(["init"])
        result = _run(["list", "services", "--table"])
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.strip().splitlines()
        self.assertTrue(lines[0].startswith("id | name"))
        self.assertEqual(len(lines), 2 + self._service_count())
        self.assertNotIn(" = ", result.stdout)

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
