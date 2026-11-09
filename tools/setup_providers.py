#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Configure OpenCode providers whose keys live in the OS secret store.

Adds/updates one provider in OpenCode's global config file (see
``opencode_config.config_file()``: ``~/.config/opencode`` by default), in the
``providers`` schema of https://opencode.ai/config.json: an OpenAI-compatible entry
with ``settings.baseURL`` and ``env: ["<PROVIDER>_API_KEY"]``.

The API key is NOT written to the config. Start opencode with
``tools/run_opencode.py``: it reads the keys through ``tools/secret.py`` (Windows
Credential Manager, KWallet, GNOME Keyring, ...) and sets the variables for the
opencode process only. Plaintext keys that older versions wrote into the config are
removed on the next run once that key is in the OS store (otherwise kept, with the
``secret.py set`` command to run); keys of other providers are only reported unless
``--redact-foreign`` is given. The tool lists where (never a value).

Safe to re-run: the old config is copied unchanged to
``<file>.bak-YYYYMMDD-HHMMSS-ffffff`` (mode 600 on POSIX; delete it once its keys are in
the OS store); ``--dry-run`` only prints what would change. No admin rights.

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
KEY_PATHS = {pid: spec["key_path"] for pid, spec in opencode_config.PROVIDERS.items()}

# Default models per provider: alias -> {modelID (as the provider's API expects), name}.
DEFAULT_MODELS: dict[str, dict[str, dict]] = {
    "gemini": {
        "gemini-3.5-flash-lite": {"modelID": "gemini-3.5-flash-lite", "name": "Gemini 3.5 Flash Lite"},
        "gemini-3.8-flash": {"modelID": "gemini-3.8-flash", "name": "Gemini 3.8 Flash"},
    },
    "nvidia": {
        "nemotron-3-ultra": {"modelID": "nvidia/nemotron-3-ultra-550b-a55b",
                             "name": "Nemotron 3 Ultra 550B"},
    },
    "deepseek": {
        "deepseek-chat": {"modelID": "deepseek-chat", "name": "DeepSeek Chat"},
    },
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


def update_config(config: dict, provider: str, notes: list[str] | None = None,
                  stored=(), redact_foreign: bool = False,
                  warnings: list[str] | None = None) -> dict:
    """Add/update ``provider`` in ``config`` (no key, only the variable name).

    First removes what older versions of the setup tools wrote (a literal
    ``settings.apiKey`` in a managed provider entry, old per-model NVIDIA entries), but
    only for keys whose path is in ``stored``; see ``opencode_config.clean_legacy``. A
    native provider (no base URL, e.g. openrouter) is only cleaned, not written.
    Changes are appended to ``notes``, kept keys to ``warnings`` (locations only).
    """
    cleaned = opencode_config.clean_legacy(config, (), stored, redact_foreign, warnings)
    if notes is not None:
        notes.extend(cleaned)
    if opencode_config.PROVIDERS[provider]["base_url"] is not None:
        opencode_config.merge_provider(config, provider, DEFAULT_MODELS.get(provider, {}))
    return config


def configure_provider(provider: str, dry_run: bool = False,
                       redact_foreign: bool = False) -> int:
    if provider not in KEY_PATHS:
        print(f"setup_providers: unknown provider '{provider}'")
        print(f"known providers: {', '.join(sorted(KEY_PATHS))}")
        return EXIT_ERROR

    key_path = KEY_PATHS[provider]
    spec = opencode_config.PROVIDERS[provider]

    # 1. The key must exist in the OS secret store (the launcher reads it later).
    try:
        get_key_from_secret(key_path)
    except SetupError as exc:
        print(f"setup_providers: {exc}")
        return exc.exit_code

    # 2. Before cleaning: which other keys are in the store (names only)? A literal
    #    key whose path is not there is kept in the config, never dropped.
    stored = opencode_config.stored_key_paths()
    if stored is None:
        print("setup_providers: note: cannot list the OS secret store; other plaintext "
              "keys in the config are kept.")
        stored = set()
    stored.add(key_path)

    opencode_config.warn_plaintext_keys(CONFIG_FILE)
    native = spec["base_url"] is None

    # 3. Load, clean legacy keys, update, save (old file backed up).
    notes: list[str] = []
    warnings: list[str] = []
    try:
        config = update_config(load_config(), provider, notes, stored, redact_foreign, warnings)
        if not native or notes:
            save_config(config, dry_run=dry_run)
    except SetupError as exc:
        print(f"setup_providers: {exc}")
        return exc.exit_code
    opencode_config.report_cleaned(notes, dry_run=dry_run, warnings=warnings)

    if native:
        print(f"setup_providers: '{provider}' is built into opencode; no provider entry written.")
        print(f"  Start opencode with tools/run_opencode.py; it sets {spec['env']}.")
        return EXIT_OK

    if dry_run:
        print(f"setup_providers: [dry-run] would configure '{provider}' in {CONFIG_FILE}")
        return EXIT_OK
    print(f"setup_providers: configured '{provider}' provider in {CONFIG_FILE}")
    print(f"  key path : {key_path} (value not shown, not written to the config)")
    print(f"  variable : {spec['env']} (set by tools/run_opencode.py for opencode only)")
    print()
    print("Next: start opencode with the launcher, then pick the model:")
    print(f"  python3 tools/run_opencode.py run -m {provider}/<model> 'hi'")
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
    parser.add_argument("--redact-foreign", action="store_true",
                        help="also replace literal keys of providers these tools do not "
                             "manage with a placeholder (default: only warn)")
    args = parser.parse_args(argv)

    return configure_provider(args.provider, dry_run=args.dry_run,
                              redact_foreign=args.redact_foreign)


if __name__ == "__main__":
    raise SystemExit(main())
