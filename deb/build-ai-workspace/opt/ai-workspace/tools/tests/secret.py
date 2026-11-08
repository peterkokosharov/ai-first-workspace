#!/usr/bin/env python3
"""Functional tests for tools/secret.py.

Loads tools/secret.py under the module name ``secret_tool`` so there is no
collision with this file's own name ``secret.py``.  All backends are exercised
functionally: memory, file, mocked WCM and mocked DCOP.  A live DCOP write /
read / delete runs only when ``SECRET_LIVE_TESTS=1`` and the wallet is open.

Run:
    python3 -m unittest discover -s tools/tests -t . -v
    SECRET_LIVE_TESTS=1 python3 -m unittest discover -s tools/tests -t . -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------- load the SUT

SUT = Path(__file__).resolve().parents[1] / "secret.py"  # tools/secret.py


def _load_sut():
    spec = importlib.util.spec_from_file_location("secret_tool", SUT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


secret_tool = _load_sut()
Backend = secret_tool.Backend
MemoryBackend = secret_tool.MemoryBackend
FileBackend = secret_tool.FileBackend
parse_export = secret_tool.parse_export
format_export = secret_tool.format_export
validate_path = secret_tool.validate_path
validate_value = secret_tool.validate_value
atomic_write_text = secret_tool.atomic_write_text
WcmBackend = secret_tool.WcmBackend
DcopBackend = secret_tool.DcopBackend
KWalletBackend = secret_tool.KWalletBackend
SecretError = secret_tool.SecretError
NotFoundError = secret_tool.NotFoundError
BackendError = secret_tool.BackendError
ExportFormatError = secret_tool.ExportFormatError

SECRET_LIVE = os.environ.get("SECRET_LIVE_TESTS") == "1"


# ---------------------------------------------------------------- path / value validation


class TestValidatePath(unittest.TestCase):
    def test_valid_paths(self):
        for path in ("a/b", "a/b/c", "a1/b_2/c-3", "github/personal/token"):
            self.assertEqual(validate_path(path), path)

    def test_invalid_paths(self):
        bad = (
            "", "/a/b", "a/b/", "a//b", "a/../b", "a b/c", "a\\b/c",
            "A/b", "a/B", "a/.b", "a/-b", "a/_b",
        )
        for path in bad:
            with self.subTest(path=path):
                with self.assertRaises(secret_tool.UsageError):
                    validate_path(path)


class TestValidateValue(unittest.TestCase):
    def test_valid_values(self):
        for value in ("abc", "secret-123", "x y z", "token!"):
            self.assertEqual(validate_value(value), value)

    def test_invalid_values(self):
        for value in ("", "a\nb", "a\rb", "a\0b"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(secret_tool.UsageError):
                    validate_value(value)


# ------------------------------------------------------------------- export format


class TestExportFormat(unittest.TestCase):
    def test_roundtrip(self):
        entries = {"a/b": "v1", "c/d/e": "v2"}
        text = format_export(entries)
        self.assertEqual(parse_export(text), entries)

    def test_comments_and_blanks(self):
        text = "# comment\n\na/b | v1\n"
        self.assertEqual(parse_export(text), {"a/b": "v1"})

    def test_split_on_first_pipe(self):
        self.assertEqual(parse_export("a/b | v | with | pipes\n"), {"a/b": "v | with | pipes"})

    def test_missing_separator(self):
        with self.assertRaises(ExportFormatError):
            parse_export("a/b v1\n")

    def test_duplicate_key(self):
        with self.assertRaises(ExportFormatError):
            parse_export("a/b | v1\na/b | v2\n")

    def test_invalid_key_in_export(self):
        with self.assertRaises(ExportFormatError):
            parse_export("A/b | v1\n")


# ---------------------------------------------------------------- memory backend


class TestMemoryBackend(unittest.TestCase):
    def test_set_get_delete_list(self):
        be = MemoryBackend({"a/b": "v1"})
        self.assertEqual(be.get("a/b"), "v1")
        self.assertEqual(sorted(be.names()), ["a/b"])
        be.set("c/d", "v2")
        self.assertEqual(be.get("c/d"), "v2")
        self.assertEqual(sorted(be.names()), ["a/b", "c/d"])
        be.delete("a/b")
        with self.assertRaises(NotFoundError):
            be.get("a/b")
        self.assertEqual(be.names(), ["c/d"])

    def test_delete_missing(self):
        be = MemoryBackend()
        with self.assertRaises(NotFoundError):
            be.delete("a/b")

    def test_get_missing(self):
        be = MemoryBackend()
        with self.assertRaises(NotFoundError):
            be.get("a/b")


# ------------------------------------------------------------------- file backend


class TestFileBackend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="secret-test-")
        self.path = Path(self.tmp) / "SECRETS"
        self.be = FileBackend(self.path)

    def test_set_get_delete_list(self):
        self.be.set("a/b", "v1")
        self.assertEqual(self.be.get("a/b"), "v1")
        self.assertEqual(self.be.names(), ["a/b"])
        self.be.set("c/d", "v2")
        self.assertEqual(sorted(self.be.names()), ["a/b", "c/d"])
        self.be.delete("a/b")
        self.assertEqual(self.be.names(), ["c/d"])

    def test_atomic_and_mode(self):
        self.be.set("a/b", "v1")
        st = self.path.stat()
        self.assertEqual(stat.S_IMODE(st.st_mode), 0o600)
        content = self.path.read_text(encoding="utf-8")
        self.assertIn("a/b | v1", content)

    def test_get_missing(self):
        with self.assertRaises(NotFoundError):
            self.be.get("a/b")


# ------------------------------------------------------------------- mocked WCM


class TestWcmMocked(unittest.TestCase):
    def test_probe_wcm_not_linux(self):
        ok, reason = WcmBackend.probe()
        self.assertEqual(ok, (sys.platform == "win32"))
        self.assertIn("Windows", reason)

    def test_wcm_get_set_delete_mocked(self):
        store = mock.MagicMock()
        store.get.return_value = "secret-value"
        store.set.return_value = True
        store.delete.return_value = True

        with mock.patch.object(WcmBackend, "_store", return_value=store):
            be = WcmBackend()
            self.assertEqual(be.get("a/b"), "secret-value")
            be.set("a/b", "new-value")
            store.set.assert_called_once_with("a/b", "new-value")
            be.delete("a/b")
            store.delete.assert_called_once_with("a/b")

    def test_wcm_get_not_found(self):
        store = mock.MagicMock()
        store.get.return_value = None
        with mock.patch.object(WcmBackend, "_store", return_value=store):
            be = WcmBackend()
            with self.assertRaises(NotFoundError):
                be.get("a/b")


# ------------------------------------------------------------------- mocked DCOP


class FakeCompletedProcess:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestDcopMocked(unittest.TestCase):
    def _patch_run(self, responses):
        """responses: list of (returncode, stdout) in call order."""
        iterator = iter(responses)

        def fake_run(args, stdin=None, capture_output=True, text=True, timeout=None):
            rc, out = next(iterator)
            return FakeCompletedProcess(rc, out)

        return mock.patch("tools.secret.kkeystore._run", side_effect=fake_run)

    def test_dcop_probe_finds_binary(self):
        with mock.patch.object(secret_tool, "_find_dcop", return_value="/opt/trinity/bin/dcop"), \
             mock.patch("tools.secret.kkeystore._run",
                        return_value=FakeCompletedProcess(0, "bool isEnabled()\n")):
            ok, reason = DcopBackend.probe()
            self.assertTrue(ok)

    def test_dcop_write_read_delete(self):
        # open -> handle; writePassword -> 0; readPassword -> value; removeEntry -> 0; close
        responses = [
            (0, "1730075659\n"),   # set: open
            (0, "0\n"),            # set: writePassword -> 0
            (0, "close ok\n"),     # set: close
            (0, "1730075659\n"),   # get: open
            (0, "secret-value\n"), # get: readPassword -> value
            (0, "close ok\n"),     # get: close
            (0, "1730075659\n"),   # delete: open
            (0, "0\n"),            # delete: removeEntry -> 0
            (0, "close ok\n"),     # delete: close
            (0, "1730075659\n"),   # final get: open
            (0, "-1\n"),           # final get: readPassword -> -1 (not found)
            (0, "close ok\n"),     # final get: close
        ]
        with mock.patch.object(secret_tool, "_find_dcop", return_value="/opt/trinity/bin/dcop"), \
             self._patch_run(responses):
            be = DcopBackend()
            be.set("a/b", "secret-value")
            self.assertEqual(be.get("a/b"), "secret-value")
            be.delete("a/b")
            with self.assertRaises(NotFoundError):
                be.get("a/b")

    def test_dcop_get_not_found(self):
        responses = [
            (0, "1730075659\n"),   # open
            (0, "-1\n"),           # readPassword -> not found
            (0, "close ok\n"),     # close
        ]
        with mock.patch.object(secret_tool, "_find_dcop", return_value="/opt/trinity/bin/dcop"), \
             self._patch_run(responses):
            be = DcopBackend()
            with self.assertRaises(NotFoundError):
                be.get("a/b")

    def test_dcop_list(self):
        responses = [
            (0, "1730075659\n"),   # open
            (0, '"a/b" "c/d"\n'),  # entryList
            (0, "close ok\n"),     # close
        ]
        with mock.patch.object(secret_tool, "_find_dcop", return_value="/opt/trinity/bin/dcop"), \
             self._patch_run(responses):
            be = DcopBackend()
            self.assertEqual(be.names(), ["a/b", "c/d"])


# ------------------------------------------------------------------- CLI via subprocess


class TestCLI(unittest.TestCase):
    def _run(self, args, input_text=None):
        cmd = [sys.executable, str(SUT)] + args
        return subprocess.run(cmd, input=input_text, capture_output=True, text=True, timeout=20)

    def test_setup_runs(self):
        result = self._run(["setup"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("platform:", result.stdout)

    def test_probe_file(self):
        result = self._run(["--backend", "file", "probe"])
        self.assertEqual(result.returncode, 0)
        self.assertIn("ok: file", result.stdout)

    def test_file_set_get_del_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            fpath = Path(tmp) / "s"
            # set via stdin
            result = self._run(["--backend", "file", "--file", str(fpath),
                                "set", "a/b"], input_text="v1\n")
            self.assertEqual(result.returncode, 0)
            # get
            result = self._run(["--backend", "file", "--file", str(fpath), "get", "a/b"])
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "v1")
            # list
            result = self._run(["--backend", "file", "--file", str(fpath), "list"])
            self.assertEqual(result.returncode, 0)
            self.assertIn("a/b", result.stdout)
            # delete
            result = self._run(["--backend", "file", "--file", str(fpath), "del", "a/b"])
            self.assertEqual(result.returncode, 0)
            result = self._run(["--backend", "file", "--file", str(fpath), "get", "a/b"])
            self.assertEqual(result.returncode, 1)

    def test_export_import_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            fpath = Path(tmp) / "s"
            ipath = Path(tmp) / "import"
            self._run(["--backend", "file", "--file", str(fpath), "set", "a/b"], input_text="v1\n")
            self._run(["--backend", "file", "--file", str(fpath), "set", "c/d"], input_text="v2\n")
            # export to file
            result = self._run(["--backend", "file", "--file", str(fpath), "export", "--out", str(ipath)])
            self.assertEqual(result.returncode, 0)
            # import into a fresh file
            fpath2 = Path(tmp) / "s2"
            result = self._run(["--backend", "file", "--file", str(fpath2), "import", "--in", str(ipath)])
            self.assertEqual(result.returncode, 0)
            result = self._run(["--backend", "file", "--file", str(fpath2), "get", "a/b"])
            self.assertEqual(result.stdout.strip(), "v1")
            result = self._run(["--backend", "file", "--file", str(fpath2), "get", "c/d"])
            self.assertEqual(result.stdout.strip(), "v2")

    def test_export_json_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            fpath = Path(tmp) / "s"
            self._run(["--backend", "file", "--file", str(fpath), "set", "a/b"], input_text="v1\n")
            result = self._run(["--backend", "file", "--file", str(fpath), "list", "--json"])
            data = json.loads(result.stdout)
            self.assertIn("a/b", data)

    def test_run_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            fpath = Path(tmp) / "s"
            self._run(["--backend", "file", "--file", str(fpath), "set", "env/foo/key"], input_text="MYVAL\n")
            result = self._run(["--backend", "file", "--file", str(fpath), "run", "env/foo/key",
                                "--", "sh", "-c", "echo $ENV_FOO_KEY"])
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "MYVAL")

    def test_auto_uses_available_store(self):
        # On linux with the TDE wallet open, auto should pick dcop and probe ok.
        result = self._run(["probe"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok: dcop", result.stdout)

    def test_file_backend_cli_is_explicit(self):
        # --backend file must be explicit; auto never silently uses plaintext.
        result = self._run(["--backend", "file", "probe"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("ok: file", result.stdout)


# ------------------------------------------------------------------- live DCOP


@unittest.skipUnless(SECRET_LIVE, "live DCOP test needs SECRET_LIVE_TESTS=1")
class TestDcopLive(unittest.TestCase):
    def setUp(self):
        self.be = DcopBackend()
        self.path = f"live-test/{os.getpid()}/value"

    def test_write_read_delete(self):
        value = f"live-{os.getpid()}"
        self.be.set(self.path, value)
        try:
            self.assertEqual(self.be.get(self.path), value)
        finally:
            try:
                self.be.delete(self.path)
            except SecretError:
                pass
        with self.assertRaises(NotFoundError):
            self.be.get(self.path)


# ------------------------------------------------------------------- KWallet (read/write only)


class TestKWalletProbe(unittest.TestCase):
    def test_probe_shape(self):
        ok, reason = KWalletBackend.probe()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(reason, str)


if __name__ == "__main__":
    unittest.main()
