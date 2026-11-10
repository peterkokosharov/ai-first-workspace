#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Tests for tools/google_api.py.

No network, no browser and no OS secret store: the backend is a small fake and
every HTTP helper is mocked. Token strings are built by concatenation.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1]
SUT = TOOLS / "google_api.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
g = _load("google_api_sut", SUT)
import secret  # noqa: E402  (tools/secret.py, the module google_api imports)


class FakeBackend:
    def __init__(self, values=None, delete_error=None):
        self.values = dict(values or {})
        self.delete_error = delete_error
        self.stored = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, path):
        if path not in self.values:
            raise secret.NotFoundError(path)
        return self.values[path]

    def set(self, path, value):
        self.stored[path] = value

    def delete(self, path):
        if self.delete_error:
            raise self.delete_error
        if path not in self.values:
            raise secret.NotFoundError(path)
        del self.values[path]


DOC = {
    "baseUrl": "https://example.test/v1/",
    "resources": {
        "items": {
            "methods": {
                "get": {"httpMethod": "GET", "path": "items/{id}"},
                "create": {"httpMethod": "POST", "path": "items"},
                "export": {"httpMethod": "GET", "path": "{+name}:export"},
            },
            "resources": {
                "parts": {"methods": {"list": {"httpMethod": "GET", "path": "parts"}}},
            },
        }
    },
}


class BuildRequestTests(unittest.TestCase):
    def test_path_param_is_escaped(self):
        method, url, payload = g.build_request(DOC, "items.get", {"id": "a/b c"}, None)
        self.assertEqual(method, "GET")
        self.assertEqual(url, "https://example.test/v1/items/a%2Fb%20c")
        self.assertIsNone(payload)

    def test_reserved_path_param_keeps_slash(self):
        _, url, _ = g.build_request(DOC, "items.export", {"name": "files/x y"}, None)
        self.assertEqual(url, "https://example.test/v1/files/x%20y:export")

    def test_other_params_go_to_query(self):
        _, url, _ = g.build_request(DOC, "items.get", {"id": "1", "q": "a b", "n": "5"}, None)
        self.assertTrue(url.startswith("https://example.test/v1/items/1?"))
        self.assertIn("q=a+b", url)
        self.assertIn("n=5", url)

    def test_body_only_for_write_methods(self):
        _, url, payload = g.build_request(DOC, "items.create", {"k": "v"}, {"title": "t"})
        self.assertEqual(payload, {"title": "t"})
        self.assertTrue(url.endswith("items?k=v"))
        _, _, payload = g.build_request(DOC, "items.get", {"id": "1"}, {"title": "t"})
        self.assertIsNone(payload)

    def test_root_url_fallback(self):
        doc = {"rootUrl": "https://r.test/", "servicePath": "api/",
               "methods": {"ping": {"httpMethod": "GET", "path": "ping"}}}
        _, url, _ = g.build_request(doc, "ping", {}, None)
        self.assertEqual(url, "https://r.test/api/ping")


class ResolveMethodTests(unittest.TestCase):
    def test_nested(self):
        spec, name = g.resolve_method(DOC, "items.parts.list")
        self.assertEqual(spec["path"], "parts")
        self.assertEqual(name, "items.parts.list")

    def test_missing(self):
        for bad in ("items.nope", "nope", "items.get.extra", "items"):
            with self.assertRaises(g.UsageError):
                g.resolve_method(DOC, bad)


class ErrorDetailTests(unittest.TestCase):
    def test_normal_body(self):
        raw = b'{"error": {"message": "Not found", "errors": [{"reason": "notFound"}]}}'
        self.assertEqual(g._error_detail(raw), "Not found notFound")

    def test_string_error(self):
        self.assertEqual(g._error_detail(b'{"error": "invalid_grant"}'), "invalid_grant")

    def test_malformed_body(self):
        self.assertEqual(g._error_detail(b"  <html>bad gateway</html> "),
                         "<html>bad gateway</html>")
        self.assertEqual(len(g._error_detail(b"x" * 1000)), 400)

    def test_non_dict_json_and_odd_errors(self):
        self.assertEqual(g._error_detail(b"[1, 2]"), "[1, 2]")
        self.assertEqual(g._error_detail(b'{"error": {"message": "m", "errors": []}}'), "m")
        self.assertEqual(g._error_detail(b'{"error": {"errors": ["x"]}}'), "")


class AuthTests(unittest.TestCase):
    CREDS = {g.KEY_CLIENT_ID: "id", g.KEY_CLIENT_SECRET: "sec"}

    def _args(self):
        return argparse.Namespace(scopes=None, port=0, timeout=1, login_hint=None,
                                  no_browser=True)

    def test_wrong_state_rejected(self):
        backend = FakeBackend(self.CREDS)
        token_request = mock.Mock()
        with mock.patch.object(g, "wait_for_code",
                               return_value={"code": "c", "state": "wrong"}), \
                mock.patch.object(g, "token_request", token_request), \
                redirect_stdout(io.StringIO()):
            with self.assertRaises(g.UsageError) as ctx:
                g.cmd_auth(self._args(), backend)
        self.assertIn("state mismatch", str(ctx.exception))
        token_request.assert_not_called()
        self.assertEqual(backend.stored, {})

    def test_consent_error_is_not_configured(self):
        backend = FakeBackend(self.CREDS)
        with mock.patch.object(g, "wait_for_code", return_value={"error": "access_denied"}), \
                redirect_stdout(io.StringIO()):
            with self.assertRaises(g.NotConfigured):
                g.cmd_auth(self._args(), backend)

    def test_missing_refresh_token_is_not_configured(self):
        backend = FakeBackend(self.CREDS)
        seen = {}
        real = g.secrets.token_urlsafe

        def spy(n=None):
            seen["state"] = real(n)
            return seen["state"]

        def callback(port, timeout):
            return {"code": "c", "state": seen["state"]}

        with mock.patch.object(g.secrets, "token_urlsafe", spy), \
                mock.patch.object(g, "wait_for_code", callback), \
                mock.patch.object(g, "token_request", return_value={"access_token": "a"}), \
                redirect_stdout(io.StringIO()):
            with self.assertRaises(g.NotConfigured):
                g.cmd_auth(self._args(), backend)

    def test_default_scopes_are_read_only(self):
        base = "https://www.googleapis.com/auth/"
        for wide in ("gmail.modify", "drive", "calendar", "tasks"):
            self.assertNotIn(base + wide, g.DEFAULT_SCOPES)


class ExitCodeTests(unittest.TestCase):
    def _main(self, argv, backend):
        err = io.StringIO()
        with mock.patch.object(g, "secret_backend", return_value=backend), \
                redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = g.main(argv)
        return code, err.getvalue()

    def test_no_consent_exits_1_with_plain_message(self):
        backend = FakeBackend({g.KEY_CLIENT_ID: "i", g.KEY_CLIENT_SECRET: "s"})
        with mock.patch.object(g.HTTPServer, "__init__", return_value=None), \
                mock.patch.object(g.HTTPServer, "server_address", ("127.0.0.1", 1),
                                  create=True), \
                mock.patch.object(g.HTTPServer, "server_close"), \
                mock.patch.object(g, "wait_for_code",
                                  side_effect=g.NotConfigured("no consent within 1s")):
            code, err = self._main(["auth", "--no-browser", "--timeout", "1"], backend)
        self.assertEqual(code, g.EXIT_NOT_CONFIGURED)
        self.assertEqual(err.strip(), "error: no consent within 1s")

    def test_wait_for_code_timeout(self):
        with mock.patch.object(g, "HTTPServer") as server:
            with self.assertRaises(g.NotConfigured) as ctx:
                g.wait_for_code(0, 0)
        self.assertEqual(ctx.exception.exit_code, 1)
        server.return_value.server_close.assert_called_once()

    def test_token_error_exits_1(self):
        with mock.patch.object(g, "http_request", return_value=({"error": "bad"}, b"")):
            with self.assertRaises(g.NotConfigured) as ctx:
                g.token_request({})
        self.assertEqual(ctx.exception.exit_code, g.EXIT_NOT_CONFIGURED)

    def test_class_exit_codes(self):
        self.assertEqual(g.GoogleError("x").exit_code, g.EXIT_API)
        self.assertEqual(g.NotConfigured("x").exit_code, g.EXIT_NOT_CONFIGURED)
        self.assertEqual(g.UsageError("x").exit_code, g.EXIT_USAGE)

    def test_missing_secret_exits_1_without_tuple(self):
        with mock.patch.object(g, "discovery_document", return_value=DOC):
            code, err = self._main(["call", "api", "v1", "items.get"], FakeBackend())
        self.assertEqual(code, g.EXIT_NOT_CONFIGURED)
        self.assertNotIn("('", err)


class OsErrorTests(unittest.TestCase):
    def test_body_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(g.UsageError) as ctx:
                g._load_body("@" + str(Path(tmp) / "nope.json"))
        self.assertIn("cannot read --body file", str(ctx.exception))

    def test_body_inline_and_invalid(self):
        self.assertEqual(g._load_body('{"a": 1}'), {"a": 1})
        with self.assertRaises(g.UsageError):
            g._load_body("[1]")
        with self.assertRaises(g.UsageError):
            g._load_body("{oops")

    def test_out_file_unwritable(self):
        backend = FakeBackend()
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp) / "missing-dir" / "out.json")
            err = io.StringIO()
            with mock.patch.object(g, "secret_backend", return_value=backend), \
                    mock.patch.object(g, "discovery_document", return_value=DOC), \
                    mock.patch.object(g, "access_token", return_value="t" + "k"), \
                    mock.patch.object(g, "http_request", return_value=({"ok": 1}, b"{}")), \
                    redirect_stdout(io.StringIO()), redirect_stderr(err):
                code = g.main(["call", "api", "v1", "items.get", "--param", "id=1",
                               "--out", out])
        self.assertEqual(code, g.EXIT_API)
        self.assertIn("cannot write", err.getvalue())


class LogoutTests(unittest.TestCase):
    def test_logout_deletes(self):
        backend = FakeBackend({g.KEY_REFRESH: "r", g.KEY_SCOPES: "s"})
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(g.cmd_logout(argparse.Namespace(), backend), g.EXIT_OK)
        self.assertIn("deleted", out.getvalue())

    def test_logout_already_absent(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(g.cmd_logout(argparse.Namespace(), FakeBackend()), g.EXIT_OK)
        self.assertIn("already absent", out.getvalue())

    def test_logout_delete_unsupported(self):
        backend = FakeBackend(delete_error=secret.BackendError("cannot delete entries"))
        with self.assertRaises(g.GoogleError) as ctx:
            g.cmd_logout(argparse.Namespace(), backend)
        self.assertIn("by hand", str(ctx.exception))
        self.assertEqual(ctx.exception.exit_code, g.EXIT_API)


if __name__ == "__main__":
    unittest.main()
