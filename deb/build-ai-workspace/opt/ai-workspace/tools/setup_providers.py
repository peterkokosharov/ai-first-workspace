#!/usr/bin/env python3
"""Configure OpenCode providers using keys from KWallet.

Reads the API key for a provider from ``data/inventory.db`` key paths via
``tools/secret.py``, then adds/updates that provider in OpenCode's global
config file ``~/.configtde/opencode/opencode.jsonc``.

Standard library only: no venv, no pip.

Usage:
    python3 tools/setup_providers.py gemini
    python3 tools/setup_providers.py nvidia
    python3 tools/setup_providers.py deepseek

Exit codes: 0 ok, 1 not found, 2 error.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INVENTORY_DB = DATA / "inventory.db"
SECRET_TOOL = ROOT / "tools" / "secret.py"

# OpenCode config location on this Q4OS system.
CONFIG_DIR = Path.home() / ".configtde" / "opencode"
CONFIG_FILE = CONFIG_DIR / "opencode.jsonc"

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_ERROR = 2

# Map provider name -> key path in inventory / KWallet.
KEY_PATHS = {
    "gemini": "gemini/personal/api_key",
    "nvidia": "nvidia/personal/api_key",
    "deepseek": "deepseek/personal/api_key",
    "groq": "groq/personal/api_key",
    "openrouter": "openrouter/personal/api_key",
    "mistral": "mistral/personal/api_key",
}


class SetupError(Exception):
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
        raise SetupError(f"cannot run secret.py: {exc}") from exc

    if result.returncode == 1:
        raise SetupError(
            f"key '{key_path}' not found in KWallet. "
            f"Set it first: python3 tools/secret.py --backend file set {key_path}",
            EXIT_NOT_FOUND,
        )
    if result.returncode != 0:
        raise SetupError(
            f"secret.py get failed (exit {result.returncode}): {result.stderr.strip()}"
        )

    value = result.stdout.strip()
    if not value:
        raise SetupError(f"key '{key_path}' is empty in KWallet")
    return value


def load_config() -> dict:
    """Load existing opencode.jsonc or return a minimal config."""
    if not CONFIG_FILE.is_file():
        return {"$schema": "https://opencode.ai/config.json"}
    try:
        text = CONFIG_FILE.read_text(encoding="utf-8")
    except OSError as exc:
        raise SetupError(f"cannot read {CONFIG_FILE}: {exc.strerror}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SetupError(f"cannot parse {CONFIG_FILE}: {exc}") from exc


def save_config(config: dict) -> None:
    """Write config back to opencode.jsonc."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        CONFIG_FILE.write_text(
            json.dumps(config, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise SetupError(f"cannot write {CONFIG_FILE}: {exc.strerror}") from exc


def configure_provider(provider: str) -> int:
    if provider not in KEY_PATHS:
        print(f"setup_providers: unknown provider '{provider}'")
        print(f"known providers: {', '.join(sorted(KEY_PATHS))}")
        return EXIT_ERROR

    key_path = KEY_PATHS[provider]

    # 1. Get the key from KWallet.
    try:
        api_key = get_key_from_kwallet(key_path)
    except SetupError as exc:
        print(f"setup_providers: {exc}")
        return exc.exit_code

    # 2. Load config.
    config = load_config()

    # 3. Add/update provider settings.
    providers = config.setdefault("providers", {})
    provider_cfg = providers.setdefault(provider, {})
    settings = provider_cfg.setdefault("settings", {})
    settings["apiKey"] = api_key

    # 4. Add known model aliases for this provider.
    models = provider_cfg.setdefault("models", {})
    if provider == "gemini":
        models.setdefault("gemini-3.5-flash-lite", {
            "modelID": "gemini/gemini-3.5-flash-lite",
            "name": "Gemini 3.5 Flash Lite",
        })
        models.setdefault("gemini-3.8-flash", {
            "modelID": "gemini/gemini-3.8-flash",
            "name": "Gemini 3.8 Flash",
        })
    elif provider == "nvidia":
        models.setdefault("nemotron-3-ultra", {
            "modelID": "nvidia/nemotron-3-ultra-550b-a55b",
            "name": "Nemotron 3 Ultra 550B",
        })
    elif provider == "deepseek":
        models.setdefault("deepseek-chat", {
            "modelID": "deepseek/deepseek-chat",
            "name": "DeepSeek Chat",
        })

    # 5. Save.
    try:
        save_config(config)
    except SetupError as exc:
        print(f"setup_providers: {exc}")
        return exc.exit_code

    print(f"setup_providers: configured '{provider}' provider in {CONFIG_FILE}")
    print(f"  key path : {key_path}")
    print(f"  apiKey   : {api_key[:4]}...{api_key[-4:]} (length {len(api_key)})")
    print()
    print("Next: restart OpenCode (or run /reload in the TUI), then:")
    print(f"  opencode run -m {provider}/<model> 'hi'")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="setup_providers.py",
        description="Configure OpenCode providers with keys from KWallet.",
    )
    parser.add_argument(
        "provider",
        choices=sorted(KEY_PATHS),
        help="provider to configure (gemini, nvidia, deepseek, groq, openrouter, mistral)",
    )
    args = parser.parse_args(argv)

    return configure_provider(args.provider)


if __name__ == "__main__":
    raise SystemExit(main())
