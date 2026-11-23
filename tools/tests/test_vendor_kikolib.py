# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""lib/kikolib must be the unmodified, pinned kikolib release (checked against its SHA256SUMS)."""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

PINNED_VERSION = "0.2.0"
LIB = Path(__file__).resolve().parents[2] / "lib"
COPY = LIB / "kikolib"


def _manifest() -> dict[str, str]:
    result: dict[str, str] = {}
    for line in (COPY / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split(None, 1)
            result[name.strip().lstrip("*")] = digest
    return result


def _files() -> set[str]:
    return {p.name for p in COPY.iterdir()
            if p.is_file() and p.name != "SHA256SUMS" and p.suffix != ".pyc"}


class VendoredKikolibTest(unittest.TestCase):
    def test_every_file_matches_manifest(self) -> None:
        for name, digest in _manifest().items():
            actual = hashlib.sha256((COPY / name).read_bytes()).hexdigest()
            self.assertEqual(digest, actual, f"{name} differs from the pinned release")

    def test_no_extra_or_missing_files(self) -> None:
        self.assertEqual(set(_manifest()), _files())

    def test_version_is_pinned(self) -> None:
        sys.path.insert(0, str(LIB))
        try:
            import kikolib
        finally:
            sys.path.remove(str(LIB))
        self.assertEqual(PINNED_VERSION, kikolib.__version__)


if __name__ == "__main__":
    unittest.main()
