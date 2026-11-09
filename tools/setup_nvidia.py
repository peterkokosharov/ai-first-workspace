#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Configure OpenCode providers for all free NVIDIA models in kb/models.xml.

Reads key ``nvidia/personal/api_key`` via tools/secret.py (automatic backend:
Windows Credential Manager, KWallet, GNOME Keyring, ...) and merges one provider
entry per model into OpenCode's global config (``~/.config/opencode`` by default;
see ``opencode_config.config_file()``). Other settings in that file are kept.

Safe to re-run: the old config is backed up as ``<file>.bak-YYYYMMDD-HHMMSS``;
``--dry-run`` only prints what would change. No admin rights.

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
ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"

CONFIG_FILE = opencode_config.config_file()
CONFIG_DIR = CONFIG_FILE.parent


def parse_models(xml_path: Path) -> list[dict]:
    """Parse kb/models.xml into a list of {alias, full_name, full_alias}."""
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
        models.append(
            {
                "alias": full_alias.split("/")[-1],
                "full_alias": full_alias,
                "full_name": name_match.group(1).strip(),
            }
        )
    return models


def get_key_from_secret(key_path: str) -> str:
    """Read a secret value from the OS secret store via tools/secret.py (auto backend)."""
    try:
        return opencode_config.get_secret(key_path)
    except opencode_config.ConfigError as exc:
        raise RuntimeError(str(exc)) from exc


def write_opencode_config(models: list[dict], api_key: str, dry_run: bool = False) -> None:
    """Merge one provider per model into the OpenCode config (old file backed up)."""
    config = opencode_config.load_json(CONFIG_FILE, {})
    providers: dict[str, dict] = config.setdefault("providers", {})
    for m in models:
        providers[m["alias"]] = {
            "settings": {
                "apiKey": api_key,
                "apiBase": ENDPOINT,
            },
            "models": {
                m["alias"]: {
                    "modelID": f"nvidia/{m['alias']}",
                    "name": m["full_name"],
                }
            },
        }

    opencode_config.write_json(CONFIG_FILE, config, dry_run=dry_run)
    verb = "would write" if dry_run else "wrote"
    print(f"{verb} {CONFIG_FILE} with {len(models)} model(s)")


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
        api_key = get_key_from_secret("nvidia/personal/api_key")
    except RuntimeError as exc:
        print(f"error: {exc}")
        return 1

    try:
        write_opencode_config(models, api_key, dry_run=args.dry_run)
    except opencode_config.ConfigError as exc:
        print(f"error: {exc}")
        return 1
    print()
    print("Next: restart OpenCode so it picks up the new providers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())