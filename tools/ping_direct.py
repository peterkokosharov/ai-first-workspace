#!/usr/bin/env python3
"""Ping an LLM provider directly via its HTTP API, using a key from KWallet.

Usage:
    python3 tools/ping_direct.py gemini "hi"
    python3 tools/ping_direct.py nvidia "hi"
    python3 tools/ping_direct.py deepseek "hi"

Reads the API key from ``data/inventory.db`` via ``tools/secret.py`` (KWallet),
then sends a request to the provider's chat completions endpoint.

Standard library only: no venv, no pip.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INVENTORY_DB = DATA / "inventory.db"
SECRET_TOOL = ROOT / "tools" / "secret.py"

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_ERROR = 2

# Fallback endpoint templates used when providers.base_url is NULL in the inventory.
# ``{model}`` is substituted with the model_id from the inventory when present.
PROVIDER_ENDPOINTS = {
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
    "nvidia": "https://integrate.api.nvidia.com/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/v1/chat/completions",
    "mistral": "https://api.mistral.ai/v1/chat/completions",
}

KNOWN_PROVIDERS = sorted(PROVIDER_ENDPOINTS)


def validate_provider(provider_name: str) -> bool:
    """Return True if ``provider_name`` is a known provider, else False."""
    return provider_name in KNOWN_PROVIDERS


def get_provider_info(provider_name: str, model_slug: str | None = None) -> dict | None:
    """Look up provider, model and key from the inventory database.

    Returns a dict with ``base_url`` (may be None), ``model_id`` and ``key_path``,
    or None if the provider is not found.
    """
    if not INVENTORY_DB.is_file():
        return None
    conn = sqlite3.connect(str(INVENTORY_DB))
    conn.row_factory = sqlite3.Row
    try:
        provider = conn.execute(
            "SELECT id, name, base_url FROM providers WHERE name = ? AND status = 'active'",
            (provider_name,),
        ).fetchone()
        if not provider:
            return None
        if model_slug:
            model = conn.execute(
                "SELECT model_id FROM models WHERE provider_id = ? AND alias = ? "
                "AND status = 'active'",
                (provider["id"], model_slug),
            ).fetchone()
        else:
            model = conn.execute(
                "SELECT model_id FROM models WHERE provider_id = ? AND status = 'active' "
                "ORDER BY id LIMIT 1",
                (provider["id"],),
            ).fetchone()
        key = conn.execute(
            "SELECT path FROM keys WHERE provider_id = ? AND status = 'active' "
            "ORDER BY id LIMIT 1",
            (provider["id"],),
        ).fetchone()
        return {
            "base_url": provider["base_url"],
            "model_id": model["model_id"] if model else None,
            "key_path": key["path"] if key else None,
        }
    finally:
        conn.close()


class PingError(Exception):
    def __init__(self, message: str, exit_code: int = EXIT_ERROR):
        super().__init__(message)
        self.exit_code = exit_code


def get_key_from_kwallet(key_path: str) -> str:
    """Read a secret value from KWallet via tools/secret.py."""
    try:
        result = subprocess.run(
            [sys.executable, str(SECRET_TOOL), "--backend", "auto", "get", key_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.SubprocessError as exc:
        raise PingError(f"cannot run secret.py: {exc}") from exc

    if result.returncode == 1:
        raise PingError(
            f"key '{key_path}' not found in KWallet. "
            f"Set it first: python3 tools/secret.py --backend file set {key_path}",
            EXIT_NOT_FOUND,
        )
    if result.returncode != 0:
        raise PingError(
            f"secret.py get failed (exit {result.returncode}): {result.stderr.strip()}"
        )

    value = result.stdout.strip()
    if not value:
        raise PingError(f"key '{key_path}' is empty in KWallet")
    return value


def build_gemini_body(message: str) -> dict:
    return {
        "contents": [{"parts": [{"text": message}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 200},
    }


def build_openai_body(message: str, model: str) -> dict:
    return {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "temperature": 0.7,
        "max_tokens": 200,
    }


def ping_provider(provider: str, message: str, model_slug: str | None = None) -> int:
    if provider not in KNOWN_PROVIDERS:
        print(f"ping_direct: unknown provider '{provider}'")
        print(f"known providers: {', '.join(KNOWN_PROVIDERS)}")
        return EXIT_ERROR

    info = get_provider_info(provider, model_slug)
    if not info:
        print(f"ping_direct: provider '{provider}' not found in inventory database")
        print(f"Run: python3 tools/inventory.py init")
        return EXIT_NOT_FOUND
    if not info["key_path"]:
        print(f"ping_direct: no active key for provider '{provider}' in inventory")
        return EXIT_NOT_FOUND
    if not info["model_id"]:
        print(f"ping_direct: no active model for provider '{provider}' in inventory")
        return EXIT_NOT_FOUND

    # 1. Get key from KWallet.
    try:
        api_key = get_key_from_kwallet(info["key_path"])
    except PingError as exc:
        print(f"ping_direct: {exc}")
        return exc.exit_code

    # 2. Build request.
    endpoint = info["base_url"] or PROVIDER_ENDPOINTS[provider]
    if "{model}" in endpoint:
        endpoint = endpoint.format(model=info["model_id"])
    headers = {
        "Content-Type": "application/json",
    }

    if provider == "gemini":
        # Gemini uses key as query parameter ?key=API_KEY.
        separator = "&" if "?" in endpoint else "?"
        endpoint = f"{endpoint}{separator}key={api_key}"
        body = json.dumps(build_gemini_body(message)).encode("utf-8")
    else:
        headers["Authorization"] = f"Bearer {api_key}"
        body = json.dumps(build_openai_body(message, info["model_id"])).encode("utf-8")

    req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")

    # 3. Send.
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        print(f"ping_direct: HTTP {exc.code} from {provider}")
        try:
            err_body = exc.read().decode("utf-8")
            print(f"      body: {err_body[:300]}")
        except Exception:
            pass
        return EXIT_ERROR
    except urllib.error.URLError as exc:
        print(f"ping_direct: connection error to {provider}: {exc.reason}")
        return EXIT_ERROR
    except Exception as exc:
        print(f"ping_direct: unexpected error: {exc}")
        return EXIT_ERROR

    # 4. Parse response.
    print(f"provider: {provider}")
    print(f"endpoint: {endpoint}")
    print(f"status  : {status}")
    print(f"body    : {text[:500]}")
    print("result: OK")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ping_direct.py",
        description="Ping an LLM provider directly via HTTP using a KWallet key.",
    )
    parser.add_argument(
        "provider",
        choices=KNOWN_PROVIDERS,
        help="provider to ping (gemini, nvidia, deepseek, mistral)",
    )
    parser.add_argument(
        "model",
        nargs="?",
        default=None,
        help="model alias from inventory (optional; uses first active model if omitted)",
    )
    parser.add_argument(
        "message",
        nargs="?",
        default="hi",
        help="message to send (default: hi)",
    )
    args = parser.parse_args(argv)

    return ping_provider(args.provider, args.message, args.model)


if __name__ == "__main__":
    raise SystemExit(main())
