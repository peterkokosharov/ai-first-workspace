#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Google APIs from the command line, standard library only.

One OAuth client and one refresh token give access to every Google API.  Each
API is described by a machine-readable *discovery document* published by
Google, so this tool needs no per-service code: it downloads the document,
resolves the method, and sends the request.

Credentials live only in the OS secret store, through ``tools/secret.py``:

    google/personal/oauth_client_id
    google/personal/oauth_client_secret
    google/personal/refresh_token
    google/personal/scopes

Nothing secret is written to disk, a log, or the inventory database.  Only the
discovery documents are cached, under ``.tmp/google/`` (gitignored).

Usage:
    python3 tools/google_api.py auth [--scopes S1,S2]   # consent, stores the token
    python3 tools/google_api.py status                  # who am I, does the token work
    python3 tools/google_api.py scopes                  # scopes granted to the token
    python3 tools/google_api.py logout                  # forget the refresh token
    python3 tools/google_api.py apis [SEARCH]           # list Google APIs
    python3 tools/google_api.py call API VERSION METHOD [options]

Examples:
    python3 tools/google_api.py call gmail v1 users.getProfile --param userId=me
    python3 tools/google_api.py call calendar v3 events.list \
        --param calendarId=primary --param maxResults=5
    python3 tools/google_api.py call drive v3 files.list \
        --param q="name contains 'invoice'"
    python3 tools/google_api.py call gmail v1 users.messages.send --body @mail.json
        # (needs: auth --scopes ...,https://www.googleapis.com/auth/gmail.send)

Notes:
    * ``--param`` fills the ``{name}`` / ``{+name}`` parts of the method path; every other
      ``--param`` becomes a query parameter.
    * ``--body`` takes inline JSON or ``@file.json`` and is the JSON request body.
    * Media upload (files) is not part of the generic call; not supported by this tool.
    * A refresh token from an OAuth app still in "Testing" expires after 7 days;
      publish the app to make it permanent.

Exit codes: 0 ok, 1 not configured, 2 network/API error, 3 usage error.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

EXIT_OK = 0
EXIT_NOT_CONFIGURED = 1
EXIT_API = 2
EXIT_USAGE = 3

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".tmp" / "google"
TOOLS_DIR = Path(__file__).resolve().parent

DISCOVERY_INDEX = "https://www.googleapis.com/discovery/v1/apis"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

KEY_CLIENT_ID = "google/personal/oauth_client_id"
KEY_CLIENT_SECRET = "google/personal/oauth_client_secret"
KEY_REFRESH = "google/personal/refresh_token"
KEY_SCOPES = "google/personal/scopes"

# Read-only by default; widen only with ``auth --scopes``.
DEFAULT_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
]

CACHE_TTL = 7 * 24 * 3600  # discovery documents change rarely


class GoogleError(Exception):
    exit_code = EXIT_API


class NotConfigured(GoogleError):
    exit_code = EXIT_NOT_CONFIGURED


class UsageError(GoogleError):
    exit_code = EXIT_USAGE


# --------------------------------------------------------------------------------------
# secret store
# --------------------------------------------------------------------------------------

def secret_backend(name: str = "auto"):
    """Open the native secret store through tools/secret.py."""
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import secret  # noqa: E402  (tools/secret.py, standard library only)

    try:
        return secret.make_backend(name)
    except secret.BackendError as exc:
        raise NotConfigured(str(exc)) from None


def read_secret(backend, key: str, *, required: bool = True) -> str | None:
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import secret  # noqa: E402

    try:
        return backend.get(secret.validate_path(key))
    except secret.NotFoundError:
        if required:
            raise NotConfigured(
                f"{key} is not in the secret store; run: "
                f"python3 tools/secret.py set {key}"
            ) from None
        return None


# --------------------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------------------

def _error_detail(raw: bytes) -> str:
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except (ValueError, UnicodeDecodeError):
        return raw.decode("utf-8", "replace").strip()[:400]
    if not isinstance(data, dict):
        return str(data)[:400]
    err = data.get("error")
    if isinstance(err, dict):
        message = err.get("message") or ""
        errors = err.get("errors")
        first = errors[0] if isinstance(errors, list) and errors else None
        reason = ""
        if isinstance(first, dict):
            reason = first.get("reason") or ""
        return f"{message} {reason}".strip()
    if err:
        return str(err)
    return str(data)[:400]


def http_request(method: str, url: str, *, data=None, headers=None, timeout: int = 120,
                 retries: int = 3) -> tuple[dict | None, bytes]:
    """Send a request; retry 429/5xx with backoff; parse JSON when possible."""
    body = None
    all_headers = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        all_headers["Content-Type"] = "application/json; charset=utf-8"

    last_error = None
    for attempt in range(retries):
        request = urllib.request.Request(url, data=body, method=method, headers=all_headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read()
                parsed = _parse_json(raw)
                return parsed, raw
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            detail = _error_detail(raw)
            if exc.code in (429, 500, 502, 503, 504) and attempt + 1 < retries:
                time.sleep(2 ** attempt)
                last_error = f"HTTP {exc.code}: {detail}"
                continue
            raise GoogleError(f"{method} {_short(url)} -> HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)
                last_error = str(exc.reason)
                continue
            raise GoogleError(f"{method} {_short(url)} -> {exc.reason}") from None
    raise GoogleError(f"request failed after {retries} attempts: {last_error}")


def _parse_json(raw: bytes):
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return None


def _short(url: str) -> str:
    """A URL safe to print: no query values that may hold personal data."""
    parts = urllib.parse.urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}{parts.path}"


# --------------------------------------------------------------------------------------
# OAuth
# --------------------------------------------------------------------------------------

def pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    return verifier, challenge


def build_auth_url(client_id: str, redirect_uri: str, scopes: list[str], state: str,
                   code_challenge: str, login_hint: str | None = None) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    if login_hint:
        params["login_hint"] = login_hint
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


class _CallbackHandler(BaseHTTPRequestHandler):
    captured: dict = {}

    def do_GET(self):  # noqa: N802 - http.server API
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
        self.captured.update({k: v[0] for k, v in query.items()})
        ok = "code" in query
        message = (
            b"<h2>Authorization received</h2><p>You can close this tab.</p>"
            if ok
            else b"<h2>Authorization failed</h2><p>See the terminal.</p>"
        )
        self.send_response(200 if ok else 400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(message)))
        self.end_headers()
        self.wfile.write(message)

    def log_message(self, *_args):  # keep the terminal clean
        return


def wait_for_code(port: int, timeout: int) -> dict:
    _CallbackHandler.captured = {}
    server = HTTPServer(("127.0.0.1", port), _CallbackHandler)
    server.timeout = 1
    deadline = time.time() + timeout
    try:
        while time.time() < deadline and not _CallbackHandler.captured:
            server.handle_request()
    finally:
        server.server_close()
    if not _CallbackHandler.captured:
        raise NotConfigured(f"no consent within {timeout}s")
    return dict(_CallbackHandler.captured)


def token_request(payload: dict) -> dict:
    parsed, _ = http_request("POST", TOKEN_URL, data=payload)
    if not isinstance(parsed, dict):
        raise GoogleError("token endpoint returned no JSON")
    if "error" in parsed:
        description = parsed.get("error_description") or parsed["error"]
        raise NotConfigured(f"token error: {description}")
    return parsed


def refresh_access_token(client_id: str, client_secret: str, refresh_token: str) -> dict:
    return token_request({
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })


def access_token(backend) -> str:
    client_id = read_secret(backend, KEY_CLIENT_ID)
    client_secret = read_secret(backend, KEY_CLIENT_SECRET)
    refresh_token = read_secret(backend, KEY_REFRESH)
    tokens = refresh_access_token(client_id, client_secret, refresh_token)
    token = tokens.get("access_token")
    if not token:
        raise GoogleError("no access_token in the refresh response")
    return token


def whoami(token: str) -> dict:
    parsed, _ = http_request("GET", USERINFO_URL, headers={"Authorization": f"Bearer {token}"})
    return parsed if isinstance(parsed, dict) else {}


# --------------------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------------------

def _cache_path(name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / name


def _cached_json(name: str, url: str, ttl: int = CACHE_TTL) -> dict:
    path = _cache_path(name)
    if path.is_file() and time.time() - path.stat().st_mtime < ttl:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            pass
    parsed, raw = http_request("GET", url)
    if not isinstance(parsed, dict):
        raise GoogleError(f"discovery document is not JSON: {url}")
    path.write_text(json.dumps(parsed, ensure_ascii=False), encoding="utf-8")
    return parsed


def discovery_index(force: bool = False) -> list[dict]:
    path = _cache_path("apis.json")
    if force and path.is_file():
        path.unlink()
    data = _cached_json("apis.json", DISCOVERY_INDEX)
    return data.get("items", [])


def discovery_document(api: str, version: str) -> dict:
    safe = f"{api}-{version}.json".replace("/", "_")
    url = f"https://www.googleapis.com/discovery/v1/apis/{api}/{version}/rest"
    return _cached_json(safe, url)


def resolve_method(document: dict, method: str) -> tuple[dict, str]:
    """Find ``events.list`` or ``users.messages.get`` in a discovery document."""
    node: dict = document
    parts = method.split(".")
    for index, part in enumerate(parts):
        resources = node.get("resources", {})
        if part in resources:
            node = resources[part]
            continue
        methods = node.get("methods", {})
        if part in methods and index == len(parts) - 1:
            return methods[part], ".".join(parts)
        raise UsageError(f"method not found in this API: {method}")
    raise UsageError(f"method not found in this API: {method}")


def build_request(document: dict, method: str, params: dict, body: dict | None):
    """Return (http_method, url, body) for a discovery method."""
    spec, _ = resolve_method(document, method)
    http_method = spec.get("httpMethod", "GET")
    path = spec.get("path", "")

    query = {}
    for name, value in params.items():
        text = str(value)
        if "{+" + name + "}" in path:
            path = path.replace("{+" + name + "}", urllib.parse.quote(text, safe="/"))
        elif "{" + name + "}" in path:
            path = path.replace("{" + name + "}", urllib.parse.quote(text, safe=""))
        else:
            query[name] = value

    missing = re.search(r"\{\+?([^}]+)\}", path)
    if missing:
        raise UsageError(f"missing path parameter: {missing.group(1)}")

    payload = body if http_method in ("POST", "PUT", "PATCH") else None

    base = document.get("baseUrl")
    if not base:
        base = document.get("rootUrl", "") + document.get("servicePath", "")
    url = base.rstrip("/") + "/" + path.lstrip("/")
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    return http_method, url, payload


# --------------------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------------------

def cmd_auth(args, backend) -> int:
    client_id = read_secret(backend, KEY_CLIENT_ID)
    client_secret = read_secret(backend, KEY_CLIENT_SECRET)

    scopes = [s.strip() for s in (args.scopes or "").split(",") if s.strip()]
    if not scopes:
        stored = read_secret(backend, KEY_SCOPES, required=False)
        scopes = stored.split() if stored else list(DEFAULT_SCOPES)

    server = HTTPServer(("127.0.0.1", args.port), _CallbackHandler)
    port = server.server_address[1]
    server.server_close()
    redirect_uri = f"http://127.0.0.1:{port}/"

    verifier, challenge = pkce_pair()
    state = secrets.token_urlsafe(16)
    url = build_auth_url(client_id, redirect_uri, scopes, state, challenge, args.login_hint)

    print(f"Scopes:  {len(scopes)}")
    for scope in scopes:
        print(f"  - {scope}")
    print(f"\nOpen this URL and grant access:\n\n{url}\n")
    if not args.no_browser:
        webbrowser.open(url)

    print(f"Waiting up to {args.timeout}s for the browser to come back to {redirect_uri} ...")
    captured = wait_for_code(port, args.timeout)
    if captured.get("error"):
        raise NotConfigured(f"consent failed: {captured['error']}")
    if captured.get("state") != state:
        raise UsageError("state mismatch in the OAuth callback")
    code = captured.get("code")
    if not code:
        raise GoogleError("no authorization code in the callback")

    tokens = token_request({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "code_verifier": verifier,
        "grant_type": "authorization_code",
        "redirect_uri": redirect_uri,
    })
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise NotConfigured(
            "Google returned no refresh_token; revoke the old grant at "
            "myaccount.google.com/permissions and run auth again"
        )

    backend.set(KEY_REFRESH, refresh_token)
    backend.set(KEY_SCOPES, " ".join(sorted(set(scopes))))

    granted = tokens.get("scope", "")
    print(f"\nrefresh_token stored as {KEY_REFRESH}")
    print(f"granted scopes: {len(granted.split())}")

    token = tokens.get("access_token")
    if token:
        info = whoami(token)
        if info.get("email"):
            print(f"account: {info['email']}")
    return EXIT_OK


def cmd_status(args, backend) -> int:
    print("client_id:     ", "set" if read_secret(backend, KEY_CLIENT_ID, required=False) else "MISSING")
    print("client_secret: ", "set" if read_secret(backend, KEY_CLIENT_SECRET, required=False) else "MISSING")
    print("refresh_token: ", "set" if read_secret(backend, KEY_REFRESH, required=False) else "MISSING")
    scopes = read_secret(backend, KEY_SCOPES, required=False)
    print("scopes:        ", len(scopes.split()) if scopes else 0)
    if not args.offline:
        token = access_token(backend)
        info = whoami(token)
        print("token:          ok")
        print("account:       ", info.get("email", "?"))
    return EXIT_OK


def cmd_scopes(args, backend) -> int:
    stored = read_secret(backend, KEY_SCOPES, required=False)
    if not stored:
        print("no scopes stored (run auth)")
        return EXIT_NOT_CONFIGURED
    for scope in stored.split():
        print(scope)
    return EXIT_OK


def cmd_logout(args, backend) -> int:
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    import secret  # noqa: E402

    failed = []
    for key in (KEY_REFRESH, KEY_SCOPES):
        try:
            backend.delete(secret.validate_path(key))
            print(f"deleted {key}")
        except secret.NotFoundError:
            print(f"already absent {key}")
        except secret.BackendError as exc:
            failed.append(f"{key} ({exc})")
    if failed:
        raise GoogleError(
            "cannot delete " + ", ".join(failed) + "; remove by hand in the secret store"
        )
    return EXIT_OK


def cmd_apis(args, backend) -> int:
    items = discovery_index(force=args.refresh)
    needle = (args.search or "").lower()
    rows = [
        item for item in items
        if not needle
        or needle in item.get("name", "").lower()
        or needle in (item.get("title") or "").lower()
    ]
    rows.sort(key=lambda i: (i.get("name", ""), i.get("version", "")))
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return EXIT_OK
    print(f"{len(rows)} APIs" + (f" matching '{args.search}'" if needle else f" (of {len(items)})"))
    for item in rows[: args.limit]:
        print(f"  {item.get('name', '?'):<28} {item.get('version', ''):<6} {item.get('title', '')}")
    if len(rows) > args.limit:
        print(f"  ... and {len(rows) - args.limit} more (use --limit)")
    return EXIT_OK


def _load_body(value: str | None) -> dict | None:
    if not value:
        return None
    if value.startswith("@"):
        try:
            text = Path(value[1:]).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise UsageError(f"cannot read --body file {value[1:]}: {exc}") from None
    else:
        text = value
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise UsageError(f"--body is not valid JSON: {exc}") from None
    if not isinstance(data, dict):
        raise UsageError("--body must be a JSON object")
    return data


def cmd_call(args, backend) -> int:
    document = discovery_document(args.api, args.version)
    params = {}
    for pair in args.param or []:
        if "=" not in pair:
            raise UsageError(f"--param needs key=value, got: {pair}")
        key, value = pair.split("=", 1)
        params[key] = value

    http_method, url, payload = build_request(document, args.method, params, _load_body(args.body))
    token = access_token(backend)
    parsed, raw = http_request(http_method, url, data=payload,
                               headers={"Authorization": f"Bearer {token}"})

    text = json.dumps(parsed, ensure_ascii=False, indent=2) if parsed is not None else raw.decode(
        "utf-8", "replace"
    )
    if args.out:
        try:
            Path(args.out).write_text(text, encoding="utf-8")
        except OSError as exc:
            raise GoogleError(f"cannot write {args.out}: {exc}") from None
        print(f"written {args.out} ({len(text)} bytes)")
    else:
        print(text)
    return EXIT_OK


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="google_api.py",
        description="Google APIs from the command line (standard library only).",
    )
    parser.add_argument(
        "--backend", default=os.environ.get("SECRET_BACKEND", "auto"),
        help="secret store backend: auto (default), wcm, keychain, secret-tool, memory",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_auth = sub.add_parser("auth", help="run the OAuth consent flow and store the refresh token")
    p_auth.add_argument("--scopes", help="comma-separated scopes (default: read-only mail, calendar, drive, tasks)")
    p_auth.add_argument("--port", type=int, default=0, help="loopback port (0 = any free port)")
    p_auth.add_argument("--timeout", type=int, default=300, help="seconds to wait for consent")
    p_auth.add_argument("--login-hint", help="pre-select an account in the browser")
    p_auth.add_argument("--no-browser", action="store_true", help="only print the URL")
    p_auth.set_defaults(func=cmd_auth)

    p_status = sub.add_parser("status", help="show whether the credentials work")
    p_status.add_argument("--offline", action="store_true", help="do not contact Google")
    p_status.set_defaults(func=cmd_status)

    p_scopes = sub.add_parser("scopes", help="print the stored scopes")
    p_scopes.set_defaults(func=cmd_scopes)

    p_logout = sub.add_parser("logout", help="delete the stored refresh token and scopes")
    p_logout.set_defaults(func=cmd_logout)

    p_apis = sub.add_parser("apis", help="list or search the Google API catalog")
    p_apis.add_argument("search", nargs="?", help="substring of the API name or title")
    p_apis.add_argument("--limit", type=int, default=40)
    p_apis.add_argument("--json", action="store_true")
    p_apis.add_argument("--refresh", action="store_true", help="re-download the catalog")
    p_apis.set_defaults(func=cmd_apis)

    p_call = sub.add_parser("call", help="call any Google API method")
    p_call.add_argument("api", help="API name, e.g. gmail")
    p_call.add_argument("version", help="API version, e.g. v1")
    p_call.add_argument("method", help="method id, e.g. users.messages.list")
    p_call.add_argument("--param", action="append", metavar="KEY=VALUE",
                        help="query parameter (repeatable)")
    p_call.add_argument("--body", help="JSON body, or @file.json")
    p_call.add_argument("--out", help="write the response to a file")
    p_call.set_defaults(func=cmd_call)

    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass

    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        backend = secret_backend(args.backend)
        with backend:
            return args.func(args, backend)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return EXIT_API
    except GoogleError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
