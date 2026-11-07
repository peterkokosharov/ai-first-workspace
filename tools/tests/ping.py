#!/usr/bin/env python3
"""Functional tests for tools/ping.py.

Tests model look-up from temporary inventory DB, OpenCode tier check,
and JSON-lines response parsing. No real network calls or OpenCode CLI
are made; subprocess calls are mocked.
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SUT = Path(__file__).resolve().parents[1] / "ping.py"  # tools/ping.py


def _load_sut():
    spec = importlib.util.spec_from_file_location("ping_sut", SUT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ping = _load_sut()


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestLookupModel(unittest.TestCase):
    """Model look-up from temporary inventory database."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ping_test_")
        self.db_path = Path(self.tmp) / "inventory.db"
        self._old_db = ping.INVENTORY_DB
        ping.INVENTORY_DB = self.db_path
        self._init_db()

    def tearDown(self):
        ping.INVENTORY_DB = self._old_db
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL DEFAULT 'llm',
                status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY,
                provider_id INTEGER NOT NULL REFERENCES providers(id),
                path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY,
                alias TEXT NOT NULL UNIQUE,
                model_id TEXT NOT NULL,
                provider_id INTEGER NOT NULL REFERENCES providers(id),
                key_id INTEGER REFERENCES keys(id),
                status TEXT NOT NULL DEFAULT 'active',
                notes TEXT
            );
        """)
        conn.executescript("""
            INSERT INTO providers (id, name, kind, status) VALUES
                (1, 'gemini', 'llm', 'active');
            INSERT INTO keys (id, provider_id, path, status) VALUES
                (1, 1, 'gemini/personal/api_key', 'active');
            INSERT INTO models (id, alias, model_id, provider_id, key_id, status) VALUES
                (1, 'gemini-flash-lite', 'gemini/gemini-3.5-flash-lite', 1, 1, 'active');
        """)
        conn.commit()
        conn.close()

    def test_lookup_model_found(self):
        model = ping.lookup_model("gemini-flash-lite")
        self.assertIsNotNone(model)
        self.assertEqual(model["alias"], "gemini-flash-lite")
        self.assertEqual(model["model_id"], "gemini/gemini-3.5-flash-lite")
        self.assertEqual(model["provider_name"], "gemini")

    def test_lookup_model_not_found(self):
        model = ping.lookup_model("nonexistent-model")
        self.assertIsNone(model)

    def test_lookup_model_no_db(self):
        ping.INVENTORY_DB = Path("/nonexistent/path/inventory.db")
        try:
            with self.assertRaises(ping.PingError) as ctx:
                ping.lookup_model("gemini-flash-lite")
            self.assertEqual(ctx.exception.exit_code, ping.EXIT_NOT_FOUND)
        finally:
            ping.INVENTORY_DB = self.db_path


class TestParseResponse(unittest.TestCase):
    """JSON-lines response parsing from opencode run output."""

    def test_parse_text_response(self):
        stdout = '{"type": "text", "part": {"text": "Hello!"}}\n'
        got_text, text, err = ping.parse_response(stdout)
        self.assertTrue(got_text)
        self.assertEqual(text, "Hello!")
        self.assertIsNone(err)

    def test_parse_error_response(self):
        stdout = '{"type": "error", "error": {"data": {"message": "Model not found"}}}\n'
        got_text, text, err = ping.parse_response(stdout)
        self.assertFalse(got_text)
        self.assertIsNone(text)
        self.assertEqual(err, "Model not found")

    def test_parse_mixed_lines(self):
        stdout = (
            '{"type": "progress", "data": {"message": "loading..."}}\n'
            '{"type": "text", "part": {"text": "Response text"}}\n'
        )
        got_text, text, err = ping.parse_response(stdout)
        self.assertTrue(got_text)
        self.assertEqual(text, "Response text")

    def test_parse_empty_output(self):
        got_text, text, err = ping.parse_response("")
        self.assertFalse(got_text)
        self.assertIsNone(text)
        self.assertIsNone(err)

    def test_parse_invalid_json_lines(self):
        stdout = "not json\n{'bad': json}\n"
        got_text, text, err = ping.parse_response(stdout)
        self.assertFalse(got_text)
        self.assertIsNone(text)
        self.assertIsNone(err)


class TestCheckTier(unittest.TestCase):
    """OpenCode tier check with mocked subprocess."""

    def test_model_in_catalog(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = FakeCompletedProcess(
                returncode=0,
                stdout="gemini/gemini-3.5-flash-lite\ngemini/gemini-3.8-flash\n",
            )
            tier_ok, msg = ping.check_tier("gemini/gemini-3.5-flash-lite", "gemini")
            self.assertTrue(tier_ok)
            self.assertIn("available in OpenCode catalog", msg)

    def test_model_not_in_catalog(self):
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = FakeCompletedProcess(
                returncode=0,
                stdout="other/model\nanother/model\n",
            )
            tier_ok, msg = ping.check_tier("gemini/gemini-3.5-flash-lite", "gemini")
            self.assertFalse(tier_ok)
            self.assertIn("not listed", msg)

    def test_opencode_not_found(self):
        with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
            tier_ok, msg = ping.check_tier("gemini/gemini-3.5-flash-lite", "gemini")
            self.assertFalse(tier_ok)
            self.assertIn("skipped", msg)


if __name__ == "__main__":
    unittest.main()
