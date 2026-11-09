#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Configure OpenCode for all free NVIDIA models in kb/models.xml.

Writes ONE provider ``nvidia`` with all models into OpenCode's global config
(``~/.config/opencode`` by default; see ``opencode_config.config_file()``), in the
``providers`` schema of https://opencode.ai/config.json. Other settings in that file
are kept.

The API key is NOT written to the config. The entry only names the variable
``NVIDIA_API_KEY``; start opencode with ``tools/run_opencode.py``, which reads the key
from the OS secret store and sets that variable for the opencode process only.
An old config that still holds a plaintext key gets a warning (value never shown).

Safe to re-run: the old config is backed up as ``<file>.bak-YYYYMMDD-HHMMSS`` (literal
keys redacted in the copy); ``--dry-run`` only prints what would change. No admin rights.

Usage:
    python3 tools/setup_nvidia.py --dry-run
    python3 tools/setup_nvidia.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
import opencode_config  # noqa: E402  (shared helpers next to this file)
KB_XML = ROOT / "kb" / "models.xml"
INVENTORY_DB = ROOT / "data" / "inventory.db"
SECRET_TOOL = ROOT / "tools" / "secret.py"
PROVIDER_ID = "nvidia"
#: Full endpoint for direct HTTP calls (ping tools); opencode gets the base URL
#: from ``opencode_config.PROVIDERS["nvidia"]["base_url"]``.
ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
KEY_PATH = opencode_config.PROVIDERS[PROVIDER_ID]["key_path"]

CONFIG_FILE = opencode_config.config_file()
CONFIG_DIR = CONFIG_FILE.parent


def parse_models(xml_path: Path) -> list[dict]:
    """Parse kb/models.xml into a list of {alias, full_alias, full_name, api_id}.

    ``api_id`` is the model id the NVIDIA API expects (``"model": "vendor/name"`` in
    the sample code of each entry); without sample code it falls back to
    ``nvidia/<alias>``.
    """
    text = xml_path.read_text(encoding="utf-8")
    models: list[dict] = []
    for block in re.finditer(
        r'<model id="([^"]+)">(.*?)</model>', text, re.DOTALL
    ):
        full_alias = block.group(1)
        inner = block.group(2)
        name_match = re.search(r"<name>([^<]+)</name>", inner)
        if not name_match:
            continue
        alias = full_alias.split("/")[-1]
        long_name = re.search(r"<full-model-name>([^<]+)</full-model-name>", inner)
        api_match = re.search(r'"model"\s*:\s*"([^"]+)"', inner)
        models.append(
            {
                "alias": alias,
                "full_alias": full_alias,
                "full_name": (long_name or name_match).group(1).strip(),
                "api_id": api_match.group(1) if api_match else f"nvidia/{alias}",
            }
        )
    return models


def build_models(models: list[dict]) -> dict[str, dict]:
    """Model entries for the ``providers.nvidia.models`` map (schema: modelID, name)."""
    return {m["alias"]: {"modelID": m["api_id"], "name": m["full_name"]} for m in models}


def get_key_from_secret(key_path: str) -> str:
    """Read a secret value from the OS secret store via tools/secret.py (auto backend)."""
    try:
        return opencode_config.get_secret(key_path)
    except opencode_config.ConfigError as exc:
        raise RuntimeError(str(exc)) from exc


def update_config(config: dict, models: list[dict]) -> dict:
    """Merge the NVIDIA provider with ``models`` into ``config`` (no key); return config."""
    opencode_config.merge_provider(config, PROVIDER_ID, build_models(models))
    return config


def write_opencode_config(models: list[dict], dry_run: bool = False) -> None:
    """Merge the NVIDIA provider into the OpenCode config (old file backed up)."""
    opencode_config.warn_plaintext_keys(CONFIG_FILE)
    config = update_config(opencode_config.load_json(CONFIG_FILE, {}), models)
    opencode_config.write_json(CONFIG_FILE, config, dry_run=dry_run)
    verb = "would write" if dry_run else "wrote"
    print(f"{verb} {CONFIG_FILE} with {len(models)} model(s) under providers.{PROVIDER_ID}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="setup_nvidia.py", description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print what would change; write nothing")
    args = parser.parse_args(argv)
    models = parse_models(KB_XML)
    if not models:
        print(f"no models found in {KB_XML}")
        return 1

    try:
        write_opencode_config(models, dry_run=args.dry_run)
    except opencode_config.ConfigError as exc:
        print(f"error: {exc}")
        return 1

    # The key is not needed for the config; only check that the launcher will find it.
    try:
        get_key_from_secret(KEY_PATH)
    except RuntimeError as exc:
        print(f"note: {exc}")
    print()
    print("Next: start opencode with the launcher; it passes the key from the OS secret")
    print("store to the opencode process only:  python3 tools/run_opencode.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
