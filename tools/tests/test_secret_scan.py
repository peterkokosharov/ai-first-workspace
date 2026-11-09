# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Tests for tools/secret_scan.py (fake keys are built at run time)."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SUT = Path(__file__).resolve().parents[1] / "secret_scan.py"
_spec = importlib.util.spec_from_file_location("secret_scan", SUT)
secret_scan = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(secret_scan)

FAKE = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


class TestFindSecrets(unittest.TestCase):
    def hits(self, text: str) -> list:
        return secret_scan.find_secrets(text)

    def test_blocks_real_looking_keys(self):
        for text in (
            "nvapi-" + FAKE,
            "token sk-" + FAKE,
            "ghp_" + FAKE,
            "github_pat_" + FAKE,
            "AKIA" + "ABCDEFGHIJKLMNOP",
            "litellm_api_key: " + FAKE,
            'api_key = "' + FAKE + '"',
        ):
            with self.subTest(text=text[:12]):
                self.assertEqual(len(self.hits(text)), 1)

    def test_allows_placeholders_and_code(self):
        for text in (
            'api_key: "$NVIDIA_API_KEY"',
            "api_key: <NVIDIA_API_KEY from your secret store>",
            'api_key = get_key_from_secret("nvidia/personal/api_key")',
            'api_key = os.environ["NVIDIA_API_KEY"]',
            "keys start with nvapi- and are stored in KWallet",
            "desk-top risk-free",
            "nvapi-" + FAKE + "  # secret-scan: allow",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.hits(text), [])

    def test_reports_line_number_not_value(self):
        hits = self.hits("ok\nnvapi-" + FAKE + "\n")
        self.assertEqual(hits, [(2, "NVIDIA API key")])


if __name__ == "__main__":
    unittest.main()
