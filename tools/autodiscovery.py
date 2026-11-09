#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Auto-discovery for a new machine.

Checks the operating system, hardware, Python, git and bash, and the local
inventory database.  If data/inventory.db is missing or empty, it tells the
user how to initialise it.  Read-only by default.

``--save`` also writes what it found:
* the full paths of python, git, bash, node, opencode and docker into the ``tools``
  section of settings.json (created from settings.json.example if missing; the old
  file is first copied byte for byte to ``settings.json.bak-<time>``; other keys and
  values that were not found are left as they are);
* this machine's row (host name, OS, CPU type, Python, user, RAM) into the
  ``machines`` table of the inventory database (INVENTORY_DB if set).

Standard library only: no venv, no pip.

Exit codes: 0 ok, 1 minimum not met, 2 inventory missing, 3 inventory empty.
"""

from __future__ import annotations

import argparse
import ctypes
import getpass
import json
import os
import platform
import shutil
import sqlite3
import sys
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
import workspace_settings  # noqa: E402  (shared helper next to this file)
import opencode_config  # noqa: E402  (backup and atomic write helpers)
import inventory  # noqa: E402  (schema migration of the machines table)

EXIT_OK = 0
EXIT_MINIMUM_NOT_MET = 1
EXIT_DB_MISSING = 2
EXIT_DB_EMPTY = 3

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
# INVENTORY_DB overrides the location, as in tools/inventory.py.
INVENTORY_DB = Path(os.environ.get("INVENTORY_DB", str(DATA / "inventory.db")))
SCHEMA = DATA / "schema.sql"
SEED = DATA / "seed.sql"
SECRET_TOOL = ROOT / "tools" / "secret.py"
INVENTORY_TOOL = ROOT / "tools" / "inventory.py"
SETTINGS = ROOT / "settings.json"
SETTINGS_EXAMPLE = ROOT / "settings.json.example"  # used when settings.json is absent


class MEMORYSTATUSEX(ctypes.Structure):
    """Win32 MEMORYSTATUSEX (sysinfoapi.h): two DWORDs, then seven DWORDLONGs."""

    _fields_ = [
        ("dwLength", ctypes.c_uint32),
        ("dwMemoryLoad", ctypes.c_uint32),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


def _windows_ram_mb(kernel32=None) -> int | None:
    """Total physical RAM in MB via GlobalMemoryStatusEx; None if the call fails."""
    if kernel32 is None:
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    mem = MEMORYSTATUSEX()
    mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if not kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
        return None
    if not mem.ullTotalPhys:
        return None
    return mem.ullTotalPhys // (1024 * 1024)


def _ram_mb() -> int | None:
    """Return total RAM in megabytes, or None if it cannot be determined."""
    system = platform.system()
    try:
        if system == "Linux":
            with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb // 1024
        elif system == "Darwin":
            import subprocess

            out = subprocess.check_output(
                ["sysctl", "-n", "hw.memsize"], text=True
            )
            return int(out.strip()) // (1024 * 1024)
        elif system == "Windows":
            return _windows_ram_mb()
    except (OSError, ValueError, AttributeError, ImportError):
        pass
    return None


def check_os() -> str:
    return f"{platform.system()} {platform.release()} ({platform.version()})"


def check_processor() -> str:
    return platform.processor() or platform.machine() or "unknown"


def check_ram() -> str:
    mb = _ram_mb()
    if mb is None:
        return "unknown"
    return f"{mb} MB"


PY_LAUNCHER = "py" if sys.platform == "win32" else "python3"


def check_python() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def check_git() -> bool:
    return shutil.which("git") is not None


def is_wsl_stub(path: str) -> bool:
    """True for Windows' own ``System32\\bash.exe`` (starts WSL, not Git Bash)."""
    parts = [p.lower() for p in Path(path.replace("\\", "/")).parts]
    return parts[-1:] == ["bash.exe"] and "system32" in parts


def git_bash_candidates() -> list[str]:
    """Usual Git for Windows install places of bash.exe."""
    return [
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        os.path.expandvars(r"%PROGRAMFILES%\Git\bin\bash.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Git\bin\bash.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\bash.exe"),
    ]


def find_bash(name: str = "bash", which=shutil.which, candidates=None) -> str | None:
    """Path of a usable bash, or None.

    ``name`` may be a full path (settings.json ``tools.bash``). The WSL stub
    ``C:\\Windows\\System32\\bash.exe`` is skipped; then Git Bash is looked for in
    its usual install places.
    """
    found = name if Path(name).is_file() else which(name)
    if found and not is_wsl_stub(found):
        return found
    for candidate in (git_bash_candidates() if candidates is None else candidates):
        if Path(candidate).is_file() and not is_wsl_stub(candidate):
            return candidate
    return None


def check_bash(name: str = "bash") -> bool:
    return find_bash(name) is not None


def load_settings() -> dict:
    """Program -> command for every known program: settings.json (else
    settings.json.example) ``tools``, then the older ``runtime`` section, then the
    default name. See tools/workspace_settings.py."""
    source = SETTINGS if SETTINGS.is_file() else SETTINGS_EXAMPLE
    return workspace_settings.all_commands(workspace_settings.load(source))


def check_opencode(name: str = "opencode") -> bool:
    return shutil.which(name) is not None


def check_merman(name: str = "npx -y @mermaid-js/mermaid-cli") -> bool:
    # npx is a shell runner; check the first token (npx) on PATH.
    first = name.split()[0] if name else "npx"
    return shutil.which(first) is not None


def check_inventory_db() -> tuple[bool, bool]:
    """Return (exists, has_tables)."""
    if not INVENTORY_DB.is_file():
        return False, False
    try:
        conn = sqlite3.connect(str(INVENTORY_DB))
        try:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            return True, len(tables) > 0
        finally:
            conn.close()
    except sqlite3.Error:
        return True, False


def resolve_tools(commands: dict, which=shutil.which) -> dict:
    """Full paths for the programs of settings.json ``tools`` that were found.

    ``commands`` is ``load_settings()``. Programs not found are left out (their
    settings stay as they are); merman is a command line, not one program, and is
    not resolved. Paths are made absolute but symlinks are kept (a snap
    ``/snap/bin/node`` must stay that, not become ``/usr/bin/snap``).
    """
    found: dict[str, str] = {}
    python = commands.get("python", "auto")
    found["python"] = (sys.executable if python in ("", "auto")
                       else (python if Path(python).is_file() else which(python) or ""))
    found["bash"] = find_bash(commands.get("bash", "bash"), which) or ""
    for name in ("git", "node", "opencode", "docker"):
        command = commands.get(name, name)
        found[name] = command if Path(command).is_file() else (which(command) or "")
    return {name: os.path.abspath(path) for name, path in found.items() if path}


def save_settings(paths: dict, settings: Path | None = None,
                  example: Path | None = None) -> Path | None:
    """Write ``paths`` into the ``tools`` section of settings.json.

    Only ``tools.<name>`` for the names in ``paths`` changes; every other key stays.
    A missing settings.json starts from settings.json.example. The old file is
    backed up byte for byte first; the write is atomic. Returns the backup (or None).
    """
    settings = SETTINGS if settings is None else settings
    example = SETTINGS_EXAMPLE if example is None else example
    source = settings if settings.is_file() else example
    data = workspace_settings.load(source) if source.is_file() else {}
    if settings.is_file() and not data:
        text = settings.read_text(encoding="utf-8-sig").strip()
        try:
            valid = not text or isinstance(json.loads(text), dict)
        except ValueError:
            valid = False
        if not valid:
            raise ValueError(f"{settings} is not a JSON object; fix it by hand first")
    tools = data.get("tools")
    if not isinstance(tools, dict):
        tools = {}
        data["tools"] = tools
    tools.update(paths)
    saved = opencode_config.backup(settings)
    opencode_config._atomic_write_text(
        settings, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return saved


def machine_info() -> dict:
    """This machine's row for the inventory ``machines`` table."""
    try:
        user = getpass.getuser()
    except (OSError, KeyError, ImportError):
        user = None
    return {
        "name": platform.node() or "unknown",
        "os": f"{platform.system()} {platform.release()}".strip(),
        "arch": platform.machine() or None,
        "python": check_python(),
        "user_name": user,
        "ram_mb": _ram_mb(),
    }


def save_machine(info: dict, db: Path | None = None) -> str:
    """Insert or update this machine's row (by name); role, status and notes of an
    existing row are kept. Returns "added" or "updated"."""
    db = INVENTORY_DB if db is None else db
    conn = sqlite3.connect(str(db))
    try:
        inventory.migrate(conn)
        known = conn.execute("SELECT 1 FROM machines WHERE name = ?",
                             (info["name"],)).fetchone()
        conn.execute(
            "INSERT INTO machines (name, os, arch, python, user_name, ram_mb, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, datetime('now')) "
            "ON CONFLICT(name) DO UPDATE SET os = excluded.os, arch = excluded.arch, "
            "python = excluded.python, user_name = excluded.user_name, "
            "ram_mb = excluded.ram_mb, updated_at = excluded.updated_at",
            (info["name"], info["os"], info["arch"], info["python"], info["user_name"],
             info["ram_mb"]),
        )
        conn.commit()
    finally:
        conn.close()
    return "updated" if known else "added"


def check_secret_store(write: bool = False, run=None) -> tuple[bool, str]:
    """Check whether a native secret store is usable via tools/secret.py.

    Default (read-only): runs ``secret.py setup``, which only detects the available
    backends, and reports the one ``auto`` would use. Nothing in the store is read,
    written or deleted.

    ``write=True``: runs ``secret.py probe``, which writes, reads back and deletes a
    random probe entry. Only on explicit request (``--probe-write``).

    Returns (ok, detail). Never prints secret values.
    """
    import subprocess

    run = subprocess.run if run is None else run
    command = "probe" if write else "setup"
    try:
        result = run([sys.executable, "-I", str(SECRET_TOOL), command],
                     capture_output=True, text=True, timeout=20)
    except (subprocess.SubprocessError, OSError):
        return False, ""
    if result.returncode != 0:
        return False, ""
    if write:
        return True, "probe ok"
    for line in (result.stdout or "").splitlines():
        if line.startswith("auto would use:"):
            chosen = line.partition(":")[2].strip()
            return (chosen not in ("", "none")), chosen
    return False, ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autodiscovery.py",
        description="Discover the local environment for the portable workspace.",
    )
    parser.add_argument(
        "--no-secret-probe", action="store_true",
        help="skip the secret-store check entirely",
    )
    parser.add_argument(
        "--probe-write", action="store_true",
        help="test the secret store by writing, reading and deleting a random probe "
             "entry (default: read-only check of which store is available)",
    )
    parser.add_argument(
        "--save", action="store_true",
        help="write the found program paths into settings.json (tools section, backup "
             "first) and this machine into the inventory database",
    )
    args = parser.parse_args(argv)

    runtime = load_settings()
    opencode_name = runtime.get("opencode", "opencode")
    merman_name = runtime.get("merman", "npx -y @mermaid-js/mermaid-cli")
    git_name = runtime.get("git", "git")
    bash_name = runtime.get("bash", "bash")
    python_name = runtime.get("python", "auto")
    if python_name in ("", "auto"):
        # "auto": the interpreter running this script (python3 on Linux, py/python on Windows).
        python_name = sys.executable
    node_name = runtime.get("node", "node")
    docker_name = runtime.get("docker", "docker")
    npm_name = runtime.get("npm", "npm")
    docker_compose_name = runtime.get("docker-compose", "docker-compose")

    def git_path() -> bool:
        return shutil.which(git_name) is not None

    def bash_path() -> bool:
        return find_bash(bash_name) is not None

    def python_path() -> bool:
        return shutil.which(python_name) is not None

    def node_path() -> bool:
        return shutil.which(node_name) is not None

    def docker_path() -> bool:
        return shutil.which(docker_name) is not None

    def npm_path() -> bool:
        return shutil.which(npm_name) is not None

    def docker_compose_path() -> bool:
        return shutil.which(docker_compose_name) is not None

    print("=== Portable workspace auto-discovery ===")
    print(f"OS:        {check_os()}")
    print(f"Processor: {check_processor()}")
    print(f"RAM:       {check_ram()}")
    print(f"Python:    {check_python()}  ({python_name}: {'yes' if python_path() else 'no'})")
    print(f"git:       {'yes' if git_path() else 'no'}  ({git_name})")
    print(f"bash:      {'yes' if bash_path() else 'no'}  ({find_bash(bash_name) or bash_name})")
    print(f"opencode:  {'yes' if check_opencode(opencode_name) else 'no'}  ({opencode_name})")
    print(f"merman:    {'yes' if check_merman(merman_name) else 'no'}  ({merman_name})")
    print(f"node:      {'yes' if node_path() else 'no'}  ({node_name})")
    print(f"docker:    {'yes' if docker_path() else 'no'}  ({docker_name})")
    print(f"npm:       {'yes' if npm_path() else 'no'}  ({npm_name})")
    print(f"docker-compose: {'yes' if docker_compose_path() else 'no'}  ({docker_compose_name})")

    missing_minimum = []
    if not git_path():
        missing_minimum.append(f"git ({git_name})")
    if not bash_path():
        missing_minimum.append(f"bash ({bash_name})")
    if not python_path():
        missing_minimum.append(f"python ({python_name})")

    print()
    if missing_minimum:
        print("MINIMUM NOT MET:")
        for item in missing_minimum:
            print(f"  - missing: {item}")
        print("Install the missing pieces before continuing.")
    else:
        print("Minimum met: git bash + Python stdlib are present.")

    print()
    print(f"tools/secret.py:     {'present' if SECRET_TOOL.is_file() else 'MISSING'}")
    print(f"tools/inventory.py:  {'present' if INVENTORY_TOOL.is_file() else 'MISSING'}")
    if args.no_secret_probe:
        print("secret store:        not checked (--no-secret-probe)")
    elif args.probe_write:
        ok, _ = check_secret_store(write=True)
        print(f"secret store:        {'ok (write/read/delete probe)' if ok else 'no usable store'}")
    else:
        ok, detail = check_secret_store()
        print(f"secret store:        {f'available: {detail} (read-only check)' if ok else 'no usable store'}")

    db_exists, db_has_tables = check_inventory_db()
    print(f"inventory db:        {'exists' if db_exists else 'MISSING'}  ({INVENTORY_DB})")
    if db_exists and not db_has_tables:
        print("  -> database exists but has no tables (empty).")
        print(f"     Run: {PY_LAUNCHER} {INVENTORY_TOOL} init")
    elif not db_exists:
        print("  -> database missing.")
        print(f"     Run: {PY_LAUNCHER} {INVENTORY_TOOL} init")

    if args.save:
        print()
        try:
            saved = save_settings(resolve_tools(runtime))
            print(f"saved: tool paths -> {SETTINGS}")
            if saved:
                print(f"  backup: {saved}")
        except (OSError, ValueError) as exc:
            print(f"not saved: {SETTINGS}: {exc}")
        if db_exists and db_has_tables:
            try:
                state = save_machine(machine_info())
                print(f"saved: this machine {state} in {INVENTORY_DB}")
            except sqlite3.Error as exc:
                print(f"not saved: machine row in {INVENTORY_DB}: {exc}")
        else:
            print("not saved: machine row (create the inventory first, then run --save again)")

    print()
    print("Notes:")
    print("  - GitHub token and email are OPTIONAL. You can work without them.")
    print("  - Secret values live in the OS native store or --backend file only.")
    print("  - 'auto' never falls back to plaintext; use --backend file explicitly.")

    problem = False
    if missing_minimum:
        problem = True
    if not SECRET_TOOL.is_file():
        problem = True
    if not INVENTORY_TOOL.is_file():
        problem = True
    if not db_exists:
        problem = True
        return EXIT_DB_MISSING
    if db_exists and not db_has_tables:
        problem = True
        return EXIT_DB_EMPTY
    if problem:
        return EXIT_MINIMUM_NOT_MET
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
