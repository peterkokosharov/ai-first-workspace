# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Glue: find the core this project runs on (standard library only).

Same file in every project; it holds no project code.  Copied from
``templates/project/tools/`` of the core (docs/procedures/new-project.md).

``find(project_root, environ)`` returns ``Found(path, origin)`` or None.  Search order:

1. ``vendor``  -- ``<project>/vendor/``, an optional copy of the core;
2. ``CORE``    -- the ``CORE`` environment variable;
3. ``settings`` -- ``"core"`` in the project's ``settings.json`` (relative to the project);
4. ``parent``  -- the first folder above the project that holds ``AGENTS.md`` and
   ``tools/secret.py``, walking the path as given (absolute, links NOT resolved), so a
   project reached through ``core/projects/X`` (a junction or symlink to a repo kept
   elsewhere) finds the core;
   On POSIX the current folder is physical, so for a relative path the walk is also made
   under ``$PWD`` when ``$PWD`` is the same folder as the current one;
5. ``parent-real`` -- the same walk on the resolved path: the given path goes through a
   link and the core is above the link's target.

The link's own location wins: a workspace above the link is trusted as the core, even if
the repo behind the link has another one above it.  ``CORE`` must be an absolute path
(a relative one is taken relative to the current folder).

A folder from 1-3 counts only if it holds ``tools/secret.py``.  That target is trusted
code: ``install()`` executes it, so point ``CORE`` and ``"core"`` only at a core you trust.

``install()`` puts the core's ``tools/`` at the end of ``sys.path`` and registers the
core's secret tool as the module ``secret``.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import NamedTuple


class Found(NamedTuple):
    path: Path
    origin: str


def _is_core(path: Path) -> bool:
    return (path / "tools" / "secret.py").is_file()


def find(root: Path, environ=None) -> Found | None:
    """The core reached from the project folder ``root``, or None."""
    given = Path(os.path.abspath(root))   # lexical: links stay as they were typed
    root = given.resolve()
    environ = os.environ if environ is None else environ
    vendor = root / "vendor"
    if _is_core(vendor):
        return Found(vendor, "vendor")
    value = (environ.get("CORE") or "").strip()
    if value and _is_core(Path(value).expanduser()):
        return Found(Path(value).expanduser().resolve(), "CORE")
    try:
        data = json.loads((root / "settings.json").read_text(encoding="utf-8-sig"))
        value = str(data.get("core") or "").strip() if isinstance(data, dict) else ""
    except (OSError, ValueError):
        value = ""
    if value:
        path = (root / Path(value).expanduser()).resolve()
        if _is_core(path):
            return Found(path, "settings")
    starts = [("parent", given)]
    pwd = _pwd_path(given, environ)
    if pwd is not None:
        starts.append(("parent", pwd))
    starts.append(("parent-real", root))
    for origin, start in starts:
        for parent in start.parents:
            if (parent / "AGENTS.md").is_file() and _is_core(parent):
                return Found(parent.resolve(), origin)
    return None


def _pwd_path(given: Path, environ) -> Path | None:
    """``given`` rebuilt under ``$PWD`` (POSIX getcwd() is physical), or None."""
    pwd = (environ.get("PWD") or "").strip()
    try:
        cwd = Path(os.getcwd())
        relative = given.relative_to(cwd)
        if not pwd or not os.path.isabs(pwd) or Path(pwd).resolve() != cwd.resolve():
            return None
    except (OSError, ValueError):
        return None
    return Path(os.path.abspath(pwd)) / relative


def install(root: Path | None = None, environ=None) -> Found:
    """Make the core's tools importable; raise ImportError if no core is found."""
    root = Path(os.path.abspath(__file__)).parents[1] if root is None else Path(root)
    found = find(root, environ)
    if found is None:
        raise ImportError(
            "no core found: put it in <project>/vendor, set CORE, set \"core\" in "
            "settings.json, or keep the project under the core's projects/ folder")
    tools = str(found.path / "tools")
    if tools not in sys.path:
        sys.path.append(tools)
    loaded = sys.modules.get("secret")
    if getattr(loaded, "__core_path__", None) != str(found.path):
        spec = importlib.util.spec_from_file_location("secret", found.path / "tools" / "secret.py")
        module = importlib.util.module_from_spec(spec)
        module.__core_path__ = str(found.path)
        sys.modules["secret"] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop("secret", None)
            raise
    return found
