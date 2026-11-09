# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Shared helpers for the setup and ping tools (standard library only).

* ``config_file()`` finds OpenCode's global config file for this OS.
* ``write_json()`` writes a config file safely (atomic replace): it first copies the
  old file byte for byte to ``<name>.bak-YYYYMMDD-HHMMSS-ffffff`` (mode 600 on POSIX)
  and supports a dry run.
* ``get_secret()`` reads a key through ``tools/secret.py --backend auto``, which picks
  the native store of the OS (Windows Credential Manager, macOS Keychain, GNOME
  Keyring / libsecret ``secret-tool``, KWallet, TDE DCOP).
* ``PROVIDERS`` / ``merge_provider()`` describe and write provider entries in the
  ``providers`` schema of https://opencode.ai/config.json. No key is ever written to
  the config: each entry names the environment variable that holds its key
  (``"env": ["NVIDIA_API_KEY"]``) and ``tools/run_opencode.py`` sets that variable for
  the opencode process only.
* ``find_plaintext_keys()`` / ``warn_plaintext_keys()`` report literal keys left in an
  old config, its backups or a project ``./opencode.json(c)`` (locations only, never
  values).
* ``clean_legacy()`` removes what older versions of the setup tools wrote (one
  ``providers.<model-alias>`` entry per NVIDIA model with a literal ``apiKey``) and
  redacts any other literal key before the config is written again.

Nothing here needs administrator rights or changes anything outside the user's home.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
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

    https://opencode.ai/docs/config (read 2026-11-09) names only
    ``~/.config/opencode/opencode.json(c)`` for the global config and gives no separate
    Windows path, so on Windows we use ``%USERPROFILE%\\.config\\opencode``. UNVERIFIED:
    not tested with a real opencode install on Windows. ``XDG_CONFIG_HOME`` and
    ``OPENCODE_CONFIG`` are not documented on that page either (kept as overrides).
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


REDACTED = "<removed: plaintext key; keep keys in the OS secret store>"


def backup(path: Path, now: float | None = None) -> Path | None:
    """Copy ``path`` byte for byte to ``path.bak-YYYYMMDD-HHMMSS-ffffff``; return the
    copy (None if there is no file).

    The copy is exact (a key not yet in the OS store is never lost) and is created with
    mode ``600`` on POSIX; on Windows the folder's default permissions apply. An
    existing backup is never overwritten: a counter is added if the name is taken.
    """
    if not path.is_file():
        return None
    data = path.read_bytes()
    now = time.time() if now is None else now
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now)) + f"-{int(now % 1 * 1e6):06d}"
    base = f"{path.name}.bak-{stamp}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    for count in range(1000):
        target = path.with_name(base if count == 0 else f"{base}-{count}")
        try:
            fd = os.open(target, flags, 0o600)
        except FileExistsError:
            continue
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
        except BaseException:
            try:
                target.unlink()
            except OSError:
                pass
            raise
        return target
    raise OSError(f"no free backup name for {path}")


def _atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` to ``path`` atomically (temp file in the same folder, then
    ``os.replace``). An existing file keeps its permission bits."""
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            try:
                shutil.copymode(path, tmp)
            except OSError:
                pass
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


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
    """Write ``data`` to ``path`` atomically. Back up an existing file first.

    With ``dry_run`` nothing is written; the planned change is printed instead.
    Returns the backup path (or None). If the backup holds literal keys, a warning
    says so (locations only) and asks to delete it once the keys are in the store.
    """
    if dry_run:
        print(f"[dry-run] would back up {path} (if it exists) and write it with "
              f"{len(json.dumps(data))} bytes; top-level keys: {', '.join(sorted(data))}")
        return None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        saved = backup(path)
        _atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    except OSError as exc:
        raise ConfigError(f"cannot write {path}: {exc.strerror or exc}") from exc
    if saved:
        print(f"backup: {saved}")
        try:
            places = find_plaintext_keys(json.loads(saved.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            places = []
        if places:
            perms = ("readable only by you" if os.name == "posix"
                     else "with the folder's default Windows permissions")
            print(f"  warning: this backup is an exact copy of the old file and holds "
                  f"{len(places)} plaintext key(s) at {', '.join(places)} ({perms}). "
                  "Delete it by hand once the keys are in the OS secret store.")
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


# ---------------------------------------------------------------------------
# Providers (schema: "providers" in https://opencode.ai/config.json, read 2026-11-09;
# the older "provider" key is marked deprecated there)
# ---------------------------------------------------------------------------

#: Runtime package for an OpenAI-compatible endpoint (custom-provider example in
#: https://opencode.ai/docs/providers).
OPENAI_COMPATIBLE = "@opencode/ai/providers/openai-compatible"

#: Provider id -> display name, key path in the OS store, environment variable the
#: launcher sets, OpenAI-compatible base URL. ``base_url`` None = opencode has a native
#: provider and only needs the variable (docs: "Provide OPENROUTER_API_KEY to the
#: OpenCode server"). Base URLs other than NVIDIA come from the vendors' own docs and
#: were not re-checked here.
PROVIDERS: dict[str, dict] = {
    "nvidia": {"name": "NVIDIA", "key_path": "nvidia/personal/api_key",
               "env": "NVIDIA_API_KEY", "base_url": "https://integrate.api.nvidia.com/v1"},
    "gemini": {"name": "Gemini", "key_path": "gemini/personal/api_key",
               "env": "GEMINI_API_KEY",
               "base_url": "https://generativelanguage.googleapis.com/v1beta/openai"},
    "deepseek": {"name": "DeepSeek", "key_path": "deepseek/personal/api_key",
                 "env": "DEEPSEEK_API_KEY", "base_url": "https://api.deepseek.com/v1"},
    "groq": {"name": "Groq", "key_path": "groq/personal/api_key",
             "env": "GROQ_API_KEY", "base_url": "https://api.groq.com/openai/v1"},
    "mistral": {"name": "Mistral", "key_path": "mistral/personal/api_key",
                "env": "MISTRAL_API_KEY", "base_url": "https://api.mistral.ai/v1"},
    "openrouter": {"name": "OpenRouter", "key_path": "openrouter/personal/api_key",
                   "env": "OPENROUTER_API_KEY", "base_url": None},
}

#: Settings that older versions of the setup tools wrote: ``apiBase`` is not in the
#: schema, and ``apiKey`` must never hold a literal key.
_STALE_SETTINGS = ("apiKey", "apiBase")


def merge_provider(config: dict, provider_id: str, models: Mapping[str, dict]) -> dict:
    """Add or update ``config["providers"][provider_id]``; return that entry.

    The entry gets ``name``, ``env`` (the variable NAME, never the key), ``package`` and
    ``settings.baseURL``; ``models`` are merged in (models already there are kept).
    ``apiKey`` / old ``apiBase`` settings of this entry are removed.
    """
    spec = PROVIDERS[provider_id]
    if spec["base_url"] is None:
        raise ValueError(f"{provider_id} is a native opencode provider; nothing to write")
    providers = config.setdefault("providers", {})
    entry = providers.setdefault(provider_id, {})
    entry["name"] = entry.get("name") or spec["name"]
    others = [n for n in entry.get("env", []) if n != spec["env"]]
    entry["env"] = [spec["env"], *others]
    entry["package"] = OPENAI_COMPATIBLE
    settings = entry.setdefault("settings", {})
    for stale in _STALE_SETTINGS:
        settings.pop(stale, None)
    settings["baseURL"] = spec["base_url"]
    entry.setdefault("models", {}).update(models)
    return entry


#: Endpoint the old setup_nvidia.py wrote as ``settings.apiBase`` of every per-model entry.
LEGACY_NVIDIA_API_BASE = "https://integrate.api.nvidia.com"


def clean_legacy(config: dict, legacy_aliases=()) -> list[str]:
    """Remove legacy entries and literal keys from ``config`` in place.

    * ``providers.<id>`` with ``id`` not in ``PROVIDERS`` is removed when ``id`` is one
      of ``legacy_aliases`` (the model aliases the old setup_nvidia.py used as provider
      ids) or its ``settings.apiBase`` points at the NVIDIA endpoint: the old tools
      wrote such entries with the real key in ``settings.apiKey``.
    * In ``providers.<id>`` with ``id`` in ``PROVIDERS`` a literal ``settings.apiKey`` is
      removed (old setup_providers.py shape); the variable named in ``env`` replaces it.
    * Any other literal key anywhere in ``config`` is replaced by ``REDACTED``.

    Returns one line per change (locations only, never values).
    """
    notes: list[str] = []
    aliases = set(legacy_aliases)
    providers = config.get("providers")
    if isinstance(providers, dict):
        for pid in list(providers):
            entry = providers[pid]
            settings = entry.get("settings") if isinstance(entry, dict) else None
            settings = settings if isinstance(settings, dict) else {}
            if pid in PROVIDERS:
                if _is_literal(settings.get("apiKey")):
                    del settings["apiKey"]
                    notes.append(f"providers.{pid}.settings.apiKey (plaintext key) removed")
                    rest = [v for k, v in entry.items() if k != "settings" and v]
                    if PROVIDERS[pid]["base_url"] is None and not settings and not rest:
                        del providers[pid]  # native provider: the entry held only the key
                continue
            api_base = settings.get("apiBase")
            old_nvidia = isinstance(api_base, str) and api_base.startswith(LEGACY_NVIDIA_API_BASE)
            if pid in aliases or old_nvidia:
                has_key = bool(find_plaintext_keys(entry))
                del providers[pid]
                notes.append(f"providers.{pid} (legacy per-model entry"
                             f"{', held a plaintext key' if has_key else ''}) removed")
    for place in find_plaintext_keys(config):
        notes.append(f"{place} (plaintext key) redacted")
    _redact(config)
    return notes


def report_cleaned(notes: list[str], dry_run: bool = False, out=None) -> None:
    """Print what ``clean_legacy`` changed (never a value)."""
    out = sys.stdout if out is None else out
    verb = "would clean" if dry_run else "cleaned"
    for note in notes:
        print(f"{verb}: {note}", file=out)
    if notes:
        print("  Keys belong only in the OS secret store; tools/run_opencode.py passes them "
              "to opencode.", file=out)


def _is_key_name(name: str) -> bool:
    return name.replace("_", "").replace("-", "").lower() == "apikey"


def _is_literal(value: object) -> bool:
    if not isinstance(value, str):
        return False
    text = value.strip()
    return bool(text) and text != REDACTED and not text.startswith(("{env:", "${"))


def find_plaintext_keys(data: object, prefix: str = "") -> list[str]:
    """Return the dotted locations of literal API keys in ``data`` (never the values).

    Literal = a key named ``apiKey`` / ``api_key`` holding a non-empty string that is
    not an ``{env:...}`` or ``${...}`` reference.
    """
    found: list[str] = []
    if isinstance(data, dict):
        for name, value in data.items():
            where = f"{prefix}.{name}" if prefix else str(name)
            if _is_key_name(str(name)) and _is_literal(value):
                found.append(where)
            else:
                found.extend(find_plaintext_keys(value, where))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            found.extend(find_plaintext_keys(value, f"{prefix}[{index}]"))
    return found


def _redact(data: object) -> None:
    if isinstance(data, dict):
        for name, value in data.items():
            if _is_key_name(str(name)) and _is_literal(value):
                data[name] = REDACTED
            else:
                _redact(value)
    elif isinstance(data, list):
        for value in data:
            _redact(value)


def warn_plaintext_keys(path: Path, out=None, project_dir: Path | None = None) -> int:
    """Warn about literal keys in ``path``, its ``.bak-*`` copies and a project-level
    ``opencode.json`` / ``opencode.jsonc`` in ``project_dir`` (default: the current
    directory). Values are never shown. Returns the number of places found.
    """
    out = sys.stderr if out is None else out
    files = [path, *sorted(path.parent.glob(path.name + ".bak-*"))] if path.parent.is_dir() else []
    project_dir = Path.cwd() if project_dir is None else project_dir
    for name in ("opencode.json", "opencode.jsonc"):
        candidate = project_dir / name
        try:
            same = any(candidate.resolve() == f.resolve() for f in files)
        except OSError:
            same = False
        if candidate.is_file() and not same:
            files.append(candidate)
    total = 0
    for file in files:
        try:
            places = find_plaintext_keys(json.loads(file.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
        if places:
            total += len(places)
            print(f"warning: {file} holds {len(places)} plaintext API key(s) at "
                  f"{', '.join(places)} (values not shown).", file=out)
    if total:
        print("  Keys belong only in the OS secret store. Delete those entries or old "
              ".bak-* files by hand; start opencode with tools/run_opencode.py.", file=out)
    return total
