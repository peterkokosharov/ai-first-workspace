#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Configure OpenCode for all free NVIDIA models in the model list (models.xml).

The folder is ``paths.kb`` from settings.json (empty = ``kb/`` next to this file).

Writes ONE provider ``nvidia`` with all models into OpenCode's global config
(``~/.config/opencode`` by default; see ``opencode_config.config_file()``), in the
``providers`` schema of https://opencode.ai/config.json. Other settings in that file
are kept.

The API key is NOT written to the config. The entry only names the variable
``NVIDIA_API_KEY``; start opencode with ``tools/run_opencode.py``, which reads the key
from the OS secret store and sets that variable for the opencode process only.
Entries that older versions of this tool wrote (one ``providers.<model-alias>`` per
model, with the real key in ``settings.apiKey``) are removed once the NVIDIA key is in
the OS store; until then they are kept and the tool prints the ``secret.py set``
command to run. Literal keys of other providers are only reported (``--redact-foreign``
replaces them with a placeholder). Locations are listed, never a value.

Safe to re-run: the old config is copied unchanged to
``<file>.bak-YYYYMMDD-HHMMSS-ffffff`` (mode 600 on POSIX; delete it once its keys are in
the OS store); ``--dry-run`` only prints what would change. No admin rights.

Usage:
    python3 tools/setup_nvidia.py --dry-run
    python3 tools/setup_nvidia.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
import opencode_config  # noqa: E402  (shared helpers next to this file)
import workspace_settings  # noqa: E402
KB_XML = workspace_settings.kb_dir() / "models.xml"
INVENTORY_DB = Path(os.environ.get("INVENTORY_DB", str(ROOT / "data" / "inventory.db")))
SECRET_TOOL = ROOT / "tools" / "secret.py"
PROVIDER_ID = "nvidia"
#: Full endpoint for direct HTTP calls (ping tools); opencode gets the base URL
#: from ``opencode_config.PROVIDERS["nvidia"]["base_url"]``.
ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
KEY_PATH = opencode_config.PROVIDERS[PROVIDER_ID]["key_path"]

CONFIG_FILE = opencode_config.config_file()
CONFIG_DIR = CONFIG_FILE.parent


def parse_models(xml_path: Path) -> list[dict]:
    """Parse models.xml into a list of {alias, full_alias, full_name, api_id}.

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


def update_config(config: dict, models: list[dict], notes: list[str] | None = None,
                  stored=(), redact_foreign: bool = False,
                  warnings: list[str] | None = None) -> dict:
    """Merge the NVIDIA provider with ``models`` into ``config`` (no key); return config.

    First removes what older versions of this tool wrote: one ``providers.<alias>``
    entry per model with the real key in ``settings.apiKey``, but only for keys whose
    path is in ``stored`` (see ``opencode_config.clean_legacy``). What was removed is
    appended to ``notes``, what was kept to ``warnings`` (locations only).
    """
    cleaned = opencode_config.clean_legacy(config, [m["alias"] for m in models], stored,
                                           redact_foreign, warnings)
    if notes is not None:
        notes.extend(cleaned)
    opencode_config.merge_provider(config, PROVIDER_ID, build_models(models))
    return config


def write_opencode_config(models: list[dict], dry_run: bool = False, stored=(),
                          redact_foreign: bool = False) -> None:
    """Merge the NVIDIA provider into the OpenCode config (old file backed up).

    ``stored``: key paths already in the OS store; only their literal copies are removed.
    """
    opencode_config.warn_plaintext_keys(CONFIG_FILE)
    notes: list[str] = []
    warnings: list[str] = []
    config = update_config(opencode_config.load_json(CONFIG_FILE, {}), models, notes,
                           stored, redact_foreign, warnings)
    opencode_config.write_json(CONFIG_FILE, config, dry_run=dry_run)
    opencode_config.report_cleaned(notes, dry_run=dry_run, warnings=warnings)
    verb = "would write" if dry_run else "wrote"
    print(f"{verb} {CONFIG_FILE} with {len(models)} model(s) under providers.{PROVIDER_ID}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="setup_nvidia.py", description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print what would change; write nothing")
    parser.add_argument("--redact-foreign", action="store_true",
                        help="also replace literal keys of providers these tools do not "
                             "manage with a placeholder (default: only warn)")
    args = parser.parse_args(argv)
    models = parse_models(KB_XML)
    if not models:
        print(f"no models found in {KB_XML}")
        return 1

    # Before cleaning: which keys are already in the OS store (names only, no value read)?
    # A literal key whose path is not there is kept in the config, never dropped.
    stored = opencode_config.stored_key_paths()
    if stored is None:
        print("note: cannot list the OS secret store; plaintext keys in the config are kept.")
        stored = set()
    if KEY_PATH not in stored:
        print(f"note: the NVIDIA key ({KEY_PATH}) is not in the OS secret store; the launcher "
              f"needs it. Store it first: {opencode_config.set_command(KEY_PATH)}")

    try:
        write_opencode_config(models, dry_run=args.dry_run, stored=stored,
                              redact_foreign=args.redact_foreign)
    except opencode_config.ConfigError as exc:
        print(f"error: {exc}")
        return 1
    print()
    print("Next: start opencode with the launcher; it passes the key from the OS secret")
    print("store to the opencode process only:  python3 tools/run_opencode.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
