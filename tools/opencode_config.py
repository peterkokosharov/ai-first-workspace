# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Shared helpers for the setup and ping tools (standard library only).

* ``config_file()`` finds OpenCode's global config file for this OS.
* ``write_json()`` writes a config file safely: it backs up the old file as
  ``<name>.bak-YYYYMMDD-HHMMSS`` first and supports a dry run.
* ``get_secret()`` reads a key through ``tools/secret.py --backend auto``, which picks
  the native store of the OS (Windows Credential Manager, macOS Keychain, GNOME
  Keyring / libsecret ``secret-tool``, KWallet, TDE DCOP).

Nothing here needs administrator rights or changes anything outside the user's home.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
SECRET_TOOL = ROOT / "tools" / "secret.py"


class ConfigError(Exception):
    """A secret or config step failed; the message is safe to print."""

    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code


def is_tde_session(env: Mapping[str, str]) -> bool:
    """True inside a Trinity Desktop (TDE) session, e.g. on Q4OS."""
    desktop = (env.get("XDG_CURRENT_DESKTOP", "") + " " + env.get("DESKTOP_SESSION", "")).lower()
    return bool(env.get("TDE_FULL_SESSION")) or "trinity" in desktop or "tde" in desktop.split()


def config_dir(env: Mapping[str, str] | None = None, platform: str | None = None,
               home: Path | None = None) -> Path:
    """Return OpenCode's global config directory.

    Order: ``$XDG_CONFIG_HOME/opencode`` if set; ``~/.configtde/opencode`` only in a
    TDE session where that folder exists; otherwise ``~/.config/opencode``.

    Assumption (from OpenCode's documentation, not tested live on Windows): OpenCode
    uses ``~/.config/opencode`` on every OS, including Windows
    (``%USERPROFILE%\\.config\\opencode``), not ``%APPDATA%``.
    """
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    home = Path.home() if home is None else home
    xdg = env.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "opencode"
    if platform.startswith("linux") and is_tde_session(env):
        tde = home / ".configtde" / "opencode"
        if tde.parent.is_dir():
            return tde
    return home / ".config" / "opencode"


def config_file(env: Mapping[str, str] | None = None, platform: str | None = None,
                home: Path | None = None) -> Path:
    """Return the config file: ``$OPENCODE_CONFIG`` if set, else an existing
    ``opencode.jsonc``/``opencode.json`` in ``config_dir()``, else ``opencode.json``."""
    env = os.environ if env is None else env
    if env.get("OPENCODE_CONFIG"):
        return Path(env["OPENCODE_CONFIG"])
    folder = config_dir(env, platform, home)
    for name in ("opencode.jsonc", "opencode.json"):
        if (folder / name).is_file():
            return folder / name
    return folder / "opencode.json"


def backup(path: Path, now: float | None = None) -> Path | None:
    """Copy ``path`` to ``path.bak-YYYYMMDD-HHMMSS``; return the copy (None if no file)."""
    if not path.is_file():
        return None
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
    target = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, target)
    return target


def load_json(path: Path, default: dict) -> dict:
    if not path.is_file():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read {path}: {exc.strerror}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"cannot parse {path} (comments in .jsonc are not supported): {exc}") from exc


def write_json(path: Path, data: dict, dry_run: bool = False) -> Path | None:
    """Write ``data`` to ``path``. Back up an existing file first.

    With ``dry_run`` nothing is written; the planned change is printed instead.
    Returns the backup path (or None).
    """
    if dry_run:
        print(f"[dry-run] would back up {path} (if it exists) and write it with "
              f"{len(json.dumps(data))} bytes; top-level keys: {', '.join(sorted(data))}")
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        saved = backup(path)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot write {path}: {exc.strerror}") from exc
    if saved:
        print(f"backup: {saved}")
    return saved


def get_secret(key_path: str, timeout: int = 15) -> str:
    """Read one secret via ``tools/secret.py --backend auto get`` (never printed)."""
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(SECRET_TOOL), "--backend", "auto", "get", key_path],
            capture_output=True, text=True, timeout=timeout,
        )
    except (subprocess.SubprocessError, OSError) as exc:
        raise ConfigError(f"cannot run {SECRET_TOOL.name}: {exc}") from exc
    if result.returncode == 1:
        raise ConfigError(
            f"key '{key_path}' not found in the OS secret store. Set it first: "
            f"python tools/secret.py set {key_path}", 1)
    if result.returncode != 0:
        raise ConfigError(f"secret.py get failed (exit {result.returncode}): {result.stderr.strip()}")
    value = result.stdout.strip()
    if not value:
        raise ConfigError(f"key '{key_path}' is empty in the OS secret store")
    return value
