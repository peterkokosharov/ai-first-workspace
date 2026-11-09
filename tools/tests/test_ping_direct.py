#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Functional tests for tools/ping_direct.py.

Tests provider validation, endpoint selection and inventory look-up using a
temporary SQLite database. No real network calls or KWallet access are made.
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SUT = Path(__file__).resolve().parents[1] / "ping_direct.py"  # tools/ping_direct.py


def _load_sut():
    spec = importlib.util.spec_from_file_location("ping_direct_sut", SUT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pd = _load_sut()


class TestProviderValidation(unittest.TestCase):
    """Provider name validation against KNOWN_PROVIDERS."""

    def test_known_providers_are_valid(self):
        for provider in pd.KNOWN_PROVIDERS:
            self.assertTrue(pd.validate_provider(provider))

    def test_unknown_provider_is_invalid(self):
        self.assertFalse(pd.validate_provider("not_a_provider"))
        self.assertFalse(pd.validate_provider(""))
        self.assertFalse(pd.validate_provider(None))


class TestGetProviderInfo(unittest.TestCase):
    """Provider info lookup from a temporary inventory database."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ping_direct_test_")
        self.db_path = Path(self.tmp) / "inventory.db"
        self._old_db = pd.INVENTORY_DB
        pd.INVENTORY_DB = self.db_path
        self._init_db()

    def tearDown(self):
        pd.INVENTORY_DB = self._old_db
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS providers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                base_url TEXT,
                status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY,
                provider_id INTEGER NOT NULL REFERENCES providers(id),
                model_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            );
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY,
                provider_id INTEGER NOT NULL REFERENCES providers(id),
                path TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            );
        """)
        conn.executescript("""
            INSERT INTO providers (id, name, base_url, status) VALUES
                (1, 'gemini', NULL, 'active'),
                (2, 'nvidia', NULL, 'active');
            INSERT INTO models (id, provider_id, model_id, status) VALUES
                (1, 1, 'gemini/gemini-3.5-flash-lite', 'active'),
                (2, 2, 'nvidia/nemotron-3-ultra-550b-a55b', 'active');
            INSERT INTO keys (id, provider_id, path, status) VALUES
                (1, 1, 'gemini/personal/api_key', 'active'),
                (2, 2, 'nvidia/personal/api_key', 'active');
        """)
        conn.commit()
        conn.close()

    def test_get_provider_info_with_base_url(self):
        info = pd.get_provider_info("gemini")
        self.assertIsNotNone(info)
        self.assertIsNone(info["base_url"])
        self.assertEqual(info["model_id"], "gemini/gemini-3.5-flash-lite")
        self.assertEqual(info["key_path"], "gemini/personal/api_key")

    def test_get_provider_info_with_custom_base_url(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("UPDATE providers SET base_url = 'https://custom.endpoint/v1' WHERE name = 'gemini'")
        conn.commit()
        conn.close()

        info = pd.get_provider_info("gemini")
        self.assertEqual(info["base_url"], "https://custom.endpoint/v1")

    def test_get_provider_info_unknown_provider(self):
        self.assertIsNone(pd.get_provider_info("nonexistent"))

    def test_get_provider_info_no_db(self):
        pd.INVENTORY_DB = Path("/nonexistent/path/inventory.db")
        try:
            self.assertIsNone(pd.get_provider_info("gemini"))
        finally:
            pd.INVENTORY_DB = self.db_path


class TestValidateProvider(unittest.TestCase):
    """Provider validation edge cases."""

    def test_empty_provider(self):
        self.assertFalse(pd.validate_provider(""))

    def test_none_provider(self):
        self.assertFalse(pd.validate_provider(None))

    def test_whitespace_provider(self):
        self.assertFalse(pd.validate_provider("  "))



class TestInventoryDbEnv(unittest.TestCase):
    def test_inventory_db_env_is_honoured(self):
        target = str(Path(tempfile.gettempdir()) / "elsewhere" / "inventory.db")
        with mock.patch.dict(os.environ, {"INVENTORY_DB": target}):
            module = _load_sut()
        self.assertEqual(module.INVENTORY_DB, Path(target))

    def test_default_is_data_folder(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("INVENTORY_DB", None)
            module = _load_sut()
        self.assertEqual(module.INVENTORY_DB, SUT.parents[1] / "data" / "inventory.db")


if __name__ == "__main__":
    unittest.main()
