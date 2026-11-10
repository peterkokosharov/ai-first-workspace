#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Functional tests for tools/inventory.py.

Exercises init / tables / list / show / search / sql / key / add-* over a
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
ROOT = Path(__file__).resolve().parents[2]                  # project root
DATA = ROOT / "data"
SCHEMA = DATA / "schema.sql"
SEED = DATA / "seed.sql"
REAL_DB = DATA / "inventory.db"
PROJECTS_DIR = ROOT / "projects"


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
                          "models", "tools", "projects")
            }
        finally:
            conn.close()

    def test_init_creates_schema_and_loads_seed(self):
        result = _run(["init"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.db.exists())
        counts = self._counts(self.db)
        expected = {
            "machines": 0, "services": 2, "providers": 8, "keys": 9,
            "models": 40, "tools": 1, "projects": 3,
        }
        self.assertEqual(counts, expected)

    def test_init_is_idempotent(self):
        first = _run(["init"])
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self._counts(self.db)
        second = _run(["init"])
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self._counts(self.db), before)

    def test_tables(self):
        _run(["init"])
        result = _run(["tables"])
        self.assertEqual(result.returncode, 0)
        for t in ("machines", "services", "providers", "keys", "models",
                  "tools", "schema_meta", "projects"):
            self.assertIn(t, result.stdout)

    def test_list(self):
        _run(["init"])
        result = _run(["list", "services"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("github", result.stdout)
        self.assertIn("gmail", result.stdout)

    def test_seed_has_no_machines(self):
        _run(["init"])
        result = _run(["list", "machines"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("table machines is empty", result.stdout)

    def test_seed_github_token_is_managed_by_git(self):
        _run(["init"])
        result = _run(["key", "github"])
        self.assertIn("personal/my-project/github_token", result.stdout)
        self.assertIn("managed by git credential helper, not secret.py", result.stdout)

    def test_seed_has_no_settings_table(self):
        _run(["init"])
        self.assertNotIn("settings", _run(["tables"]).stdout.split())

    def test_seed_projects(self):
        _run(["init"])
        result = _run(["list", "projects"])
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("example-project", "second-project", "third-project"):
            self.assertIn(name, result.stdout)
        self.assertIn("consulting", result.stdout)

    def test_seed_projects_live_under_projects_folder(self):
        _run(["init"])
        conn = sqlite3.connect(str(self.db))
        try:
            rows = conn.execute("SELECT name, path FROM projects").fetchall()
        finally:
            conn.close()
        self.assertTrue(rows)
        for name, path in rows:
            self.assertEqual(path, f"projects/{name}")

    def test_add_project(self):
        _run(["init"])
        result = _run(["add-project", "acme", "--title", "Acme Ltd",
                       "--kind", "manufacturing", "--notes", "pilot"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._project_row("acme"),
            ("projects/acme", 0, "active", "Acme Ltd", "manufacturing", "pilot"),
        )

    def test_add_project_repo_state_follows_the_folder(self):
        _run(["init"])
        result = _run(["add-project", "no_folder_yet"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._project_row("no_folder_yet")[1], 0)  # no .git: no claim
        module = self._module()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "projects" / "with_repo" / ".git").mkdir(parents=True)
            module.ROOT = Path(tmp)
            self.assertEqual(module._project_repo_state("with_repo"), 1)  # a real repo
            self.assertEqual(module._project_repo_state("never_created"), 0)

    def test_add_project_repo_flags_override_detection(self):
        _run(["init"])
        self.assertEqual(_run(["add-project", "forced", "--repo"]).returncode, 0)
        self.assertEqual(self._project_row("forced")[1], 1)
        self.assertEqual(_run(["add-project", "denied", "--no-repo"]).returncode, 0)
        self.assertEqual(self._project_row("denied")[1], 0)

    def test_add_project_no_repo_and_planned(self):
        _run(["init"])
        result = _run(["add-project", "scratch", "--no-repo", "--status", "planned"])
        self.assertEqual(result.returncode, 0, result.stderr)
        row = self._project_row("scratch")
        self.assertEqual(row[1], 0)
        self.assertEqual(row[2], "planned")

    def test_add_project_custom_path_must_stay_under_projects(self):
        _run(["init"])
        result = _run(["add-project", "paperwork", "--path", "docs/paperwork"])
        self.assertEqual(result.returncode, 3)
        self.assertIn("projects/", result.stderr)
        result = _run(["add-project", "paperwork", "--path", "projects/paperwork"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._project_row("paperwork")[0], "projects/paperwork")

    def test_add_project_path_cannot_escape_projects(self):
        _run(["init"])
        for bad in ("projects/../escape", "projects/../../etc", "projects/x/..",
                    "projects/..", "projects//x", "projects/./x",
                    "projects\\..\\escape", "projects/", "Projects/x", "projects/x/../y",
                    "projects/x.", "projects/x ", "projects/x/"):
            result = _run(["add-project", "probe", "--path", bad])
            self.assertEqual(result.returncode, 3, bad)
        self.assertIsNone(self._project_row("probe"))

    def test_add_project_path_is_exactly_projects_name(self):
        _run(["init"])
        for name, path in (("foo", "projects/bar"),
                           ("foo", "projects/foo/bar"),
                           ("foo", "projects/a/b")):
            result = _run(["add-project", name, "--path", path])
            self.assertEqual(result.returncode, 3, path)
        self.assertIsNone(self._project_row("foo"))

    def test_add_project_rejects_bad_names(self):
        _run(["init"])
        for bad in ("Upper", "two words", "../etc", "a/b", "", " con", "con", "com1",
                    "con.txt", "com1.bak", "aux.ini", "-x", ".x", "x."):
            result = _run(["add-project", bad])
            self.assertEqual(result.returncode, 3, bad)

    def test_add_project_duplicate_is_refused(self):
        _run(["init"])
        result = _run(["add-project", "example-project"])
        self.assertEqual(result.returncode, 3)
        self.assertIn("example-project", result.stderr)

    def test_add_project_creates_no_folder(self):
        _run(["init"])
        if not PROJECTS_DIR.is_dir():
            self.skipTest("no projects/ folder in this checkout")
        before = sorted(p.name for p in PROJECTS_DIR.iterdir())
        result = _run(["add-project", "probe_only_db"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sorted(p.name for p in PROJECTS_DIR.iterdir()), before)

    def test_add_project_without_database_creates_nothing(self):
        result = _run(["add-project", "x"])
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.db.exists())

    def test_init_adds_projects_to_an_older_database(self):
        conn = sqlite3.connect(str(self.db))
        try:
            conn.executescript(
                "CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"
                "CREATE TABLE services ("
                " id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, kind TEXT,"
                " account TEXT, status TEXT NOT NULL DEFAULT 'active', notes TEXT);"
                "INSERT INTO schema_meta VALUES ('schema_version', '3');"
                "INSERT INTO services (id, name, kind) VALUES (42, 'legacy', 'test');"
            )
            conn.commit()
        finally:
            conn.close()
        result = _run(["init"])
        self.assertEqual(result.returncode, 0, result.stderr)
        conn = sqlite3.connect(str(self.db))
        try:
            tables = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            legacy = conn.execute("SELECT name FROM services WHERE id = 42").fetchone()
            version = conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()
            projects = conn.execute("SELECT count(*) FROM projects").fetchone()[0]
        finally:
            conn.close()
        self.assertIn("projects", tables)
        self.assertEqual(legacy, ("legacy",))
        self.assertEqual(version, ("4",))
        self.assertEqual(projects, 3)

    def _module(self):
        """Import tools/inventory.py in-process, for the pure helpers."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("inventory_sut", SUT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _project_row(self, name):
        """(path, repo, status, title, kind, notes) for one project, or None."""
        conn = sqlite3.connect(str(self.db))
        try:
            return conn.execute(
                "SELECT path, repo, status, title, kind, notes FROM projects WHERE name = ?",
                (name,),
            ).fetchone()
        finally:
            conn.close()

    def test_show(self):
        _run(["init"])
        result = _run(["show", "services", "1"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("name = 'github'", result.stdout)

    def test_show_missing(self):
        _run(["init"])
        result = _run(["show", "machines", "999"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("not found", result.stderr)

    def test_search(self):
        _run(["init"])
        result = _run(["search", "keys", "path", "github"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("personal/my-project/github_token", result.stdout)

    def test_sql_read_only(self):
        _run(["init"])
        result = _run(["sql", "SELECT name FROM services ORDER BY name"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("github", result.stdout)
        self.assertIn("gmail", result.stdout)

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
        self.assertIn("personal/my-project/github_token", result.stdout)
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
        result = _run(["add-key", "personal/my-project/github_token", "--service", "github"])
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


if __name__ == "__main__":
    unittest.main()
