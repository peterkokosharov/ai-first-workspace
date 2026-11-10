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
            "gho_" + FAKE,
            "ghs_" + FAKE,
            "ghu_" + FAKE,
            "hf_" + FAKE,
            "GOC" + "SPX-" + FAKE[:28],
            "ya" + "29." + FAKE,
            "1/" + "/0" + FAKE,
            "-----BEGIN " + "RSA PRIVATE KEY-----",
            "-----BEGIN " + "PRIVATE KEY-----",
            "-----BEGIN " + "PGP PRIVATE KEY BLOCK-----",
            "github_pat_" + FAKE,
            "AKIA" + "ABCDEFGHIJKLMNOP",
            "GEMINI_API_KEY=" + "AI" + "za" + FAKE[:35],
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
            "Gemini keys start with AIza and are 39 characters long",
            "AI" + "za" + FAKE[:20],  # too short for a Google key
            "nvapi-" + FAKE + "  # secret-scan: allow",
            "hf_" + FAKE[:10],  # too short
            "gho_" + FAKE[:10],
            "GOC" + "SPX-" + FAKE[:8],
            "ya" + "29." + FAKE[:8],
            "1/" + "/0" + FAKE[:8],
            "path/1/" + "/0" + FAKE,  # inside a longer path
            "-----BEGIN " + "CERTIFICATE-----",
            "the hf_ prefix and ya29. tokens are scanned",
        ):
            with self.subTest(text=text):
                self.assertEqual(self.hits(text), [])

    def test_reports_line_number_not_value(self):
        hits = self.hits("ok\nnvapi-" + FAKE + "\n")
        self.assertEqual(hits, [(2, "NVIDIA API key")])



SHA1 = "a" * 40
SHA2 = "b" * 40


class TestFindSecretsInDiff(unittest.TestCase):
    def test_added_line_reported_with_commit_path_and_line(self):
        diff = "\n".join([
            SHA1,
            "diff --git a/note.txt b/note.txt",
            "--- a/note.txt",
            "+++ b/note.txt",
            "@@ -3,0 +4,2 @@",
            "+fine",
            "+token nvapi-" + FAKE,
        ])
        self.assertEqual(secret_scan.find_secrets_in_diff(diff),
                         [(SHA1, "note.txt", 5, "NVIDIA API key")])

    def test_removed_and_allowed_lines_are_not_reported(self):
        diff = "\n".join([
            SHA2,
            "diff --git a/note.txt b/note.txt",
            "--- a/note.txt",
            "+++ b/note.txt",
            "@@ -1 +1 @@",
            "-token nvapi-" + FAKE,
            "+token nvapi-" + FAKE + "  # secret-scan: allow",
            "\\ No newline at end of file",
        ])
        self.assertEqual(secret_scan.find_secrets_in_diff(diff), [])

    def test_new_file_and_second_commit(self):
        diff = "\n".join([
            SHA1,
            "diff --git a/a.txt b/a.txt",
            "new file mode 100644",
            "--- /dev/null",
            "+++ b/a.txt",
            "@@ -0,0 +1 @@",
            "+clean",
            SHA2,
            "diff --git a/b.txt b/b.txt",
            "--- a/b.txt",
            "+++ b/b.txt",
            "@@ -1,0 +2 @@",
            "+ghp_" + FAKE,
        ])
        self.assertEqual(secret_scan.find_secrets_in_diff(diff),
                         [(SHA2, "b.txt", 2, "GitHub token")])

    def test_combined_merge_diff_reports_only_new_lines(self):
        diff = "\n".join([
            SHA1,
            "diff --cc m.txt",
            "--- a/m.txt",
            "+++ b/m.txt",
            "@@@ -1,1 -1,1 +1,2 @@@",
            "- old nvapi-" + FAKE,
            " +from one parent",
            "++evil nvapi-" + FAKE,
        ])
        self.assertEqual(secret_scan.find_secrets_in_diff(diff),
                         [(SHA1, "m.txt", 2, "NVIDIA API key")])

    def test_header_lines_are_not_scanned(self):
        diff = "\n".join([
            SHA1,
            "diff --git a/x b/x",
            "--- a/x",
            "+++ b/nvapi-" + FAKE,
        ])
        self.assertEqual(secret_scan.find_secrets_in_diff(diff), [])


class TestCommitsToPush(unittest.TestCase):
    def test_delete_and_malformed_lines_publish_nothing(self):
        lines = "(delete) " + "0" * 40 + " refs/heads/x " + SHA1 + "\nshort line\n"
        self.assertEqual(secret_scan.commits_to_push(lines), [])


if __name__ == "__main__":
    unittest.main()
