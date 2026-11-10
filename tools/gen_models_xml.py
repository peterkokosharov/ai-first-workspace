#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Generate models.xml from free_endpoints_index.md in the model list folder.

The folder is ``paths.kb`` from settings.json; it must be set (the core has no ``kb/``).

Each <model> element contains:
  id        - model alias
  full-model-name
  url       - chat completions endpoint
  python-code - ready-to-run Python snippet (requests)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
import workspace_settings  # noqa: E402  (shared helper next to this file)

KB = workspace_settings.kb_dir()  # None when paths.kb is not set
INDEX = None if KB is None else KB / "free_endpoints_index.md"
OUT = None if KB is None else KB / "models.xml"

ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"


def parse_index(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    models: list[dict[str, str]] = []
    # Table rows: | N | alias | name | endpoint | tags | source |
    for line in text.splitlines():
        # Row format: | N | alias | full-name | vendor | endpoint | tags | source |
        m = re.match(
            r"\|\s*\d+\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*[^|]*?\s*\|\s*([^|]+?)\s*\|",
            line,
        )
        if not m:
            continue
        full_alias = m.group(1).strip()
        name = m.group(2).strip()
        endpoint = m.group(3).strip()
        # Only keep real HTTP(S) endpoints; skip "None", tags text, explore/discover, etc.
        if not endpoint.startswith("http"):
            continue
        if full_alias == "explore/discover":
            continue
        # id = short alias: part after last '/', e.g. mistralai/mistral-large-4-1t-a52b -> mistral-large-4-1t-a52b
        short_id = full_alias.split("/")[-1]
        models.append({"alias": short_id, "full_alias": full_alias, "name": name, "endpoint": endpoint})
    return models


def python_code_for(model_id: str) -> str:
    return (
        "import base64\n"
        "from pathlib import Path\n"
        "import requests\n\n"
        f'invoke_url = "{ENDPOINT}"\n'
        "stream = False\n\n"
        "\ndef media_data_url(kind, index, mime_types):\n"
        "    for suffix, mime in mime_types.items():\n"
        "        path = Path(f\"{kind}_{index}{suffix}\")\n"
        "        if path.exists():\n"
        "            return f\"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}\"\n"
        "    raise FileNotFoundError(f\"Expected {kind}_{index} with suffix in {list(mime_types)}\")\n\n"
        f'image_data_urls = [media_data_url("image", i, {{".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}}) for i in [1]]\n\n'
        "headers = {\n"
        '    "Authorization": "Bearer $NVIDIA_API_KEY",\n'
        '    "Accept": "text/event-stream" if stream else "application/json",\n'
        "}\n\n"
        "payload = {\n"
        f'  "model": "{model_id}",\n'
        '  "messages": [\n'
        "    {\n"
        "      \"role\": \"user\",\n"
        "      \"content\": [\n"
        "        {\n"
        '          "type": "text",\n'
        '          "text": "Describe the color and shape on the left and on the right."\n'
        "        },\n"
        "        {\n"
        '          "type": "image_url",\n'
        '          "image_url": {\n'
        '            "url": image_data_urls[0]\n'
        "          }\n"
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ],\n"
        '  "max_tokens": 4096,\n'
        '  "stream": stream,\n'
        '  "temperature": 0.5,\n'
        '  "top_p": 1,\n'
        '  "frequency_penalty": 0,\n'
        '  "presence_penalty": 0,\n'
        '  "reasoning_effort": "high"\n'
        "}\n\n"
        "response = requests.post(invoke_url, headers=headers, json=payload, stream=stream)\n"
        "if stream:\n"
        "    for line in response.iter_lines():\n"
        "        if line:\n"
        "            print(line.decode(\"utf-8\"))\n"
        "else:\n"
        "    print(response.json())\n"
    )


def build_xml(models: list[dict[str, str]]) -> str:
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<models>"]
    for m in models:
        alias = m["alias"]
        full_alias = m["full_alias"]
        code = python_code_for(full_alias)
        lines.append(f'  <model id="{alias}">')
        lines.append(f"    <name>{alias}</name>")
        lines.append(f"    <full-model-name>{m['name']}</full-model-name>")
        lines.append(f"    <url>{m['endpoint']}</url>")
        lines.append("    <python-code><![CDATA[")
        for line in code.splitlines():
            lines.append(f"      {line}")
        lines.append("    ]]></python-code>")
        lines.append("  </model>")
    lines.append("</models>")
    return "\n".join(lines) + "\n"


def main() -> int:
    if KB is None:
        print("[gen_models_xml] set paths.kb in settings.json to the model list folder",
              file=sys.stderr)
        return 2
    models = parse_index(INDEX)
    xml = build_xml(models)
    OUT.write_text(xml, encoding="utf-8")
    print(f"[gen_models_xml] wrote {OUT} with {len(models)} model(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
