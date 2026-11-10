#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Build one self-contained folder: the core plus a single project.

A project runs on the core (see docs/procedures/new-project.md).  Handing a project
over therefore means handing over the runtime as well: this tool copies the core
and the chosen project into one folder, and the project works from there without
the original workspace.

Usage:
    python3 tools/bundle.py NAME [--out DIR] [--force] [--no-test]

What is copied, and what never is:

* the core -- without its git history, `out/`, `projects/`, `data/inventory.db`
  and `settings.json` (the last two are local: one holds the inventory, the other
  the key names and paths of this machine);
* the project -- with its own `.git`, because the history belongs to it;
* nothing else.  A bundle never carries a secret.

Exit codes: 0 ok, 1 refused or failed.

Standard library only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

EXIT_OK = 0
EXIT_FAIL = 1

CORE_SKIP = {
    ".git",
    ".tmp",
    "out",
    "projects",
    "__pycache__",
    "settings.json",
}
PROJECT_SKIP = {".tmp", "__pycache__", "settings.json"}
# Files that are local to a machine and must never leave it.
CORE_SKIP_FILES = ("data/inventory.db", "settings.json")
TEST_COMMAND = [sys.executable, "-m", "unittest", "discover", "-s", "tools/tests", "-t", "."]
# Ask the bundled project which core it reaches; inside a bundle the answer is "parent".
PROBE_COMMAND = [
    sys.executable, "-c",
    "import pathlib, sys; sys.path.insert(0, 'tools'); import core; "
    "found = core.find(pathlib.Path('.').resolve(), {}); "
    "print(found.origin if found else 'none')",
]
# The core's .gitignore ignores `/projects`, which would hide the delivered project
# from the recipient's first `git add -A`.  A bundle gets its own list instead.
BUNDLE_GITIGNORE = """\
# Temporary files
.tmp/

# Python cache
__pycache__/
*.pyc
*.pyo

# Local files: recreated on the machine that runs this bundle
data/inventory.db
settings.json
settings.json.bak-*

# Test output
out/
"""


def _ignore_core(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in CORE_SKIP or name.startswith("settings.json.bak-") or name.endswith(".pyc")
    }


def _ignore_project(_directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in PROJECT_SKIP or name.endswith(".pyc")}


def _remove_tree(path: Path) -> None:
    """Delete a tree, resetting permissions first (git objects are read-only)."""
    path = Path(path)
    for item in sorted(path.rglob("*"), reverse=True):
        mode = 0o700 if item.is_dir() else 0o600
        try:
            item.chmod(mode)
        except OSError:
            pass
    try:
        path.chmod(0o700)
    except OSError:
        pass
    shutil.rmtree(path)


def _inside(child: Path, parent: Path) -> bool:
    """True when ``child`` is ``parent`` or lies below it (lexically)."""
    try:
        Path(child).relative_to(Path(parent))
    except ValueError:
        return False
    return True


def _check_name(name: str) -> str:
    """A project name is one folder name, nothing else."""
    if (not name or name.strip() != name or name in {".", ".."}
            or "/" in name or "\\" in name or ":" in name):
        raise ValueError(f"project name must be one folder name under projects/; got: {name!r}")
    return name


def _check_out(root: Path, target: Path) -> None:
    """Refuse a target that the copy would run into."""
    if target == root:
        raise ValueError(f"--out must not be the workspace root itself: {target}")
    if _inside(target, root / "projects"):
        raise ValueError(f"--out must not be inside projects/: {target}")
    if _inside(target, root) and not _inside(target, root / "out"):
        raise ValueError(f"--out must be outside {root} or under its out/: {target}")


def build(root: Path, name: str, out: Path, *, force: bool = False,
          run_tests: bool = True) -> tuple[Path, subprocess.CompletedProcess | None]:
    """Copy core + project into ``out/name``; return the folder and the test run."""
    root = Path(root).resolve()
    name = _check_name(name)
    project = root / "projects" / name
    if not project.is_dir():
        raise FileNotFoundError(f"no project folder: {project}")

    target = (Path(out).resolve() / name)
    _check_out(root, target)
    if target.exists():
        if not force:
            raise FileExistsError(f"{target} exists; pass --force to replace it")
        _remove_tree(target)

    target.mkdir(parents=True)
    shutil.copytree(root, target, dirs_exist_ok=True, ignore=_ignore_core)
    for relative in CORE_SKIP_FILES:
        stale = target / relative
        if stale.exists():
            stale.unlink()
    shutil.copytree(project, target / "projects" / name, ignore=_ignore_project)
    (target / ".gitignore").write_text(BUNDLE_GITIGNORE, encoding="utf-8")

    bundled = target / "projects" / name
    env = {key: value for key, value in os.environ.items() if key != "CORE"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"  # keep the bundle free of __pycache__
    if (bundled / "tools" / "core.py").is_file():
        probe = subprocess.run(PROBE_COMMAND, cwd=bundled, capture_output=True,
                               text=True, env=env)
        origin = (probe.stdout or "").strip()
        if probe.returncode != 0 or origin != "parent":
            raise ValueError(
                f"the bundled project does not reach the bundled core (got {origin!r}): "
                f"{(probe.stderr or '').strip()}"
            )

    result = None
    if run_tests:
        result = subprocess.run(TEST_COMMAND, cwd=bundled, capture_output=True,
                                text=True, env=env)
    return target, result


def check(target: Path) -> list[str]:
    """Return the problems that make a bundle unshippable."""
    problems = []
    if (target / "data" / "inventory.db").exists():
        problems.append("data/inventory.db is in the bundle")
    if (target / "settings.json").exists():
        problems.append("settings.json is in the bundle")
    for settings in sorted((target / "projects").glob("*/settings.json")):
        problems.append(f"{settings.relative_to(target)} is in the bundle")
    if (target / ".git").exists():
        problems.append("the core's git history is in the bundle")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="copy the core and one project into one folder")
    parser.add_argument("name", help="folder name under projects/")
    parser.add_argument("--out", default=None,
                        help="where to build (default: out/bundles in the workspace root)")
    parser.add_argument("--force", action="store_true", help="replace an existing bundle")
    parser.add_argument("--no-test", action="store_true", help="do not run the project's tests")
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    out = Path(args.out) if args.out else root / "out" / "bundles"
    try:
        target, result = build(root, args.name, out, force=args.force,
                               run_tests=not args.no_test)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAIL

    problems = check(target)
    if problems:
        for problem in problems:
            print(f"error: {problem}", file=sys.stderr)
        return EXIT_FAIL

    files = sum(1 for path in target.rglob("*") if path.is_file())
    print(f"bundle:  {target}")
    print(f"files:   {files}")
    print(f"project: {target / 'projects' / args.name}")
    if result is None:
        print("tests:   not run (--no-test)")
        return EXIT_OK
    lines = [line for line in ((result.stdout or "") + (result.stderr or "")).splitlines()
             if line.strip()]
    summary = next((line for line in lines if line.startswith("Ran ")), "")
    status = "OK" if result.returncode == 0 else "FAILED"
    print(f"tests:   {status}" + (f" -- {summary}" if summary else ""))
    if result.returncode != 0:
        print((result.stdout or "") + (result.stderr or ""), file=sys.stderr)
        return EXIT_FAIL
    print(f"start:   cd {target / 'projects' / args.name}")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
