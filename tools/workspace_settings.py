# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Read the local ``settings.json`` (standard library only).

``settings.json`` is local and not in git; ``settings.json.example`` is its committed
template and is read when ``settings.json`` is missing. Sections:

* ``tools``: program -> command or full path (python, git, bash, node, opencode,
  merman, docker). Empty = find the program on PATH. ``autodiscovery.py --save``
  fills in the paths it found.
* ``git``: ``remote_url``, ``remote_user`` (read by docs/procedures/github-deploy.md)
  and ``token_key``, the inventory name of the GitHub token this repo uses (the
  token itself is kept by git's credential helper, not by tools/secret.py).
* ``runtime``: older name of ``tools``; still read. A non-empty ``tools`` value wins.

Nothing here writes a file.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SETTINGS = ROOT / "settings.json"
SETTINGS_EXAMPLE = ROOT / "settings.json.example"

#: Program name used when neither ``tools`` nor ``runtime`` names one.
DEFAULT_COMMANDS = {
    "opencode": "opencode",
    "merman": "npx -y @mermaid-js/mermaid-cli",
    "git": "git",
    "bash": "bash",
    "python": "auto",
    "node": "node",
    "docker": "docker",
    "npm": "npm",
    "docker-compose": "docker-compose",
}


def load(path: Path | None = None) -> dict:
    """Return the whole settings file as a dict ({} if missing or invalid).

    Default: ``settings.json``, else ``settings.json.example``.
    """
    if path is None:
        path = SETTINGS if SETTINGS.is_file() else SETTINGS_EXAMPLE
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _section(data: dict, name: str) -> dict:
    value = data.get(name)
    return value if isinstance(value, dict) else {}


def configured_tool(name: str, data: dict | None = None) -> str:
    """The command or path set for ``name`` (``tools`` first, then ``runtime``);
    "" when nothing is set (= find it on PATH)."""
    data = load() if data is None else data
    for section in ("tools", "runtime"):
        value = _section(data, section).get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def tool_command(name: str, data: dict | None = None) -> str:
    """``configured_tool`` or the default program name."""
    return configured_tool(name, data) or DEFAULT_COMMANDS.get(name, name)


def all_commands(data: dict | None = None) -> dict:
    """Every known program -> command (defaults, then ``runtime``, then ``tools``)."""
    data = load() if data is None else data
    names = list(DEFAULT_COMMANDS)
    for section in ("runtime", "tools"):
        names += [n for n in _section(data, section) if n not in names]
    return {name: tool_command(name, data) for name in names}


def git_settings(data: dict | None = None) -> dict:
    """``git`` section with the three known keys always present (strings)."""
    data = load() if data is None else data
    git = _section(data, "git")
    return {key: str(git.get(key) or "") for key in ("remote_url", "remote_user", "token_key")}
