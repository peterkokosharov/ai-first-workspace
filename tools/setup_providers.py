#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Configure OpenCode providers using keys from the OS secret store.

Reads the API key for a provider from ``data/inventory.db`` key paths via
``tools/secret.py`` (automatic backend: Windows Credential Manager, KWallet, GNOME
Keyring, ...), then adds/updates that provider in OpenCode's global config file
(see ``opencode_config.config_file()``: ``~/.config/opencode`` by default).

Safe to re-run: the old config is backed up as ``<file>.bak-YYYYMMDD-HHMMSS`` before
it is overwritten; ``--dry-run`` only prints what would change. No admin rights.

Standard library only: no venv, no pip.

Usage:
    python3 tools/setup_providers.py gemini --dry-run
    python3 tools/setup_providers.py gemini
    python3 tools/setup_providers.py nvidia
    python3 tools/setup_providers.py deepseek

Exit codes: 0 ok, 1 not found, 2 error.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
import opencode_config  # noqa: E402  (shared helpers next to this file)
DATA = ROOT / "data"
INVENTORY_DB = DATA / "inventory.db"
SECRET_TOOL = ROOT / "tools" / "secret.py"

# OpenCode config location for this OS (TDE folder only inside a TDE session).
CONFIG_FILE = opencode_config.config_file()
CONFIG_DIR = CONFIG_FILE.parent

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_ERROR = 2

# Map provider name -> key path in the inventory / OS secret store.
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


def get_key_from_secret(key_path: str) -> str:
    """Read a secret value from the OS secret store via tools/secret.py (auto backend)."""
    try:
        return opencode_config.get_secret(key_path)
    except opencode_config.ConfigError as exc:
        raise SetupError(str(exc), exc.exit_code) from exc


get_key_from_kwallet = get_key_from_secret  # old name, kept for compatibility


def load_config() -> dict:
    """Load the existing OpenCode config or return a minimal one."""
    try:
        return opencode_config.load_json(CONFIG_FILE, {"$schema": "https://opencode.ai/config.json"})
    except opencode_config.ConfigError as exc:
        raise SetupError(str(exc)) from exc


def save_config(config: dict, dry_run: bool = False) -> None:
    """Write the config back; the old file is backed up first."""
    try:
        opencode_config.write_json(CONFIG_FILE, config, dry_run=dry_run)
    except opencode_config.ConfigError as exc:
        raise SetupError(str(exc)) from exc


def configure_provider(provider: str, dry_run: bool = False) -> int:
    if provider not in KEY_PATHS:
        print(f"setup_providers: unknown provider '{provider}'")
        print(f"known providers: {', '.join(sorted(KEY_PATHS))}")
        return EXIT_ERROR

    key_path = KEY_PATHS[provider]

    # 1. Get the key from the OS secret store.
    try:
        api_key = get_key_from_secret(key_path)
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
        save_config(config, dry_run=dry_run)
    except SetupError as exc:
        print(f"setup_providers: {exc}")
        return exc.exit_code

    if dry_run:
        print(f"setup_providers: [dry-run] would configure '{provider}' in {CONFIG_FILE}")
        return EXIT_OK
    print(f"setup_providers: configured '{provider}' provider in {CONFIG_FILE}")
    print(f"  key path : {key_path} (value not shown)")
    print()
    print("Next: restart OpenCode (or run /reload in the TUI), then:")
    print(f"  opencode run -m {provider}/<model> 'hi'")
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="setup_providers.py",
        description="Configure OpenCode providers with keys from the OS secret store.",
    )
    parser.add_argument(
        "provider",
        choices=sorted(KEY_PATHS),
        help="provider to configure (gemini, nvidia, deepseek, groq, openrouter, mistral)",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would change; write nothing")
    args = parser.parse_args(argv)

    return configure_provider(args.provider, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
