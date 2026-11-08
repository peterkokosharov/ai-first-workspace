#!/usr/bin/env python3
"""Configure OpenCode providers for all free NVIDIA models in kb/models.xml.

Reads key ``nvidia/personal/api_key`` from data/inventory.db via tools/secret.py,
writes ~/.configtde/opencode/opencode.jsonc with one provider entry per model.

Usage:
    python3 tools/setup_nvidia.py
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KB_XML = ROOT / "kb" / "models.xml"
INVENTORY_DB = ROOT / "data" / "inventory.db"
SECRET_TOOL = ROOT / "tools" / "secret.py"
ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"

HOME = Path.home()
CONFIG_DIR = HOME / ".configtde" / "opencode"
CONFIG_FILE = CONFIG_DIR / "opencode.jsonc"


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
    """Read a secret value from the project secret tool."""
    try:
        result = subprocess.run(
            [sys.executable, str(SECRET_TOOL), "--backend", "auto", "get", key_path],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except subprocess.SubprocessError as exc:
        raise RuntimeError(f"cannot run {SECRET_TOOL}: {exc}") from exc

    if result.returncode == 1:
        raise RuntimeError(
            f"key '{key_path}' not found in secret store. "
            f"Set it first: python3 {SECRET_TOOL} --backend auto set {key_path}"
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"{SECRET_TOOL} get failed: {result.stderr.strip()}"
        )
    value = result.stdout.strip()
    if not value:
        raise RuntimeError(f"key '{key_path}' is empty in secret store")
    return value


def write_opencode_config(models: list[dict], api_key: str) -> None:
    """Write ~/.configtde/opencode/opencode.jsonc with one provider per model."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    providers: dict[str, dict] = {}
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

    config = {"providers": providers}
    CONFIG_FILE.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {CONFIG_FILE} with {len(models)} model(s)")


def main() -> int:
    models = parse_models(KB_XML)
    if not models:
        print(f"no models found in {KB_XML}")
        return 1

    try:
        api_key = get_key_from_secret("nvidia/personal/api_key")
    except RuntimeError as exc:
        print(f"error: {exc}")
        return 1

    write_opencode_config(models, api_key)
    print()
    print("Next: restart OpenCode so it picks up the new providers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())