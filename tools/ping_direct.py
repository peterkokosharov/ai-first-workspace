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

# Provider -> (key_path, endpoint, model_field, body_builder)
PROVIDERS = {
    "gemini": {
        "key_path": "gemini/personal/api_key",
        "endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
        "method": "POST",
    },
    "nvidia": {
        "key_path": "nvidia/personal/api_key",
        "endpoint": "https://integrate.api.nvidia.com/v1/chat/completions",
        "method": "POST",
    },
    "deepseek": {
        "key_path": "deepseek/personal/api_key",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "method": "POST",
    },
    "mistral": {
        "key_path": "mistral/personal/api_key",
        "endpoint": "https://api.mistral.ai/v1/chat/completions",
        "method": "POST",
    },
}


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


def ping_provider(provider: str, message: str) -> int:
    if provider not in PROVIDERS:
        print(f"ping_direct: unknown provider '{provider}'")
        print(f"known providers: {', '.join(sorted(PROVIDERS))}")
        return EXIT_ERROR

    cfg = PROVIDERS[provider]

    # 1. Get key from KWallet.
    try:
        api_key = get_key_from_kwallet(cfg["key_path"])
    except PingError as exc:
        print(f"ping_direct: {exc}")
        return exc.exit_code

    # 2. Build request.
    endpoint = cfg["endpoint"]
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
        model = "deepseek-chat"
        if provider == "nvidia":
            model = "gemini/gemini-3.5-flash-lite"
        elif provider == "mistral":
            model = "mistral-small-latest"
        body = json.dumps(build_openai_body(message, model)).encode("utf-8")

    req = urllib.request.Request(endpoint, data=body, headers=headers, method=cfg["method"])

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
        choices=sorted(PROVIDERS),
        help="provider to ping (gemini, nvidia, deepseek)",
    )
    parser.add_argument(
        "message",
        nargs="?",
        default="hi",
        help="message to send (default: hi)",
    )
    args = parser.parse_args(argv)

    return ping_provider(args.provider, args.message)


if __name__ == "__main__":
    raise SystemExit(main())
