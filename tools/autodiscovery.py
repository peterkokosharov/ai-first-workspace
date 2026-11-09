#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Auto-discovery for a new machine.

Checks the operating system, hardware, Python, git and bash, and the local
inventory database.  If data/inventory.db is missing or empty, it tells the
user how to initialise it.

Standard library only: no venv, no pip.

Exit codes: 0 ok, 1 minimum not met, 2 inventory missing, 3 inventory empty.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import shutil
import sqlite3
import sys
from pathlib import Path

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


def check_bash() -> bool:
    if shutil.which("bash") is not None:
        return True
    # Windows Git Bash candidates
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
        os.path.expandvars(r"%PROGRAMFILES%\Git\bin\bash.exe"),
        os.path.expandvars(r"%PROGRAMFILES(X86)%\Git\bin\bash.exe"),
    ):
        if Path(candidate).is_file():
            return True
    return False


def load_settings() -> dict:
    """Load runtime paths from settings.json, else settings.json.example (empty dict if
    both are missing/invalid)."""
    source = SETTINGS if SETTINGS.is_file() else SETTINGS_EXAMPLE
    try:
        text = source.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    runtime = data.get("runtime")
    if not isinstance(runtime, dict):
        return {}
    return runtime


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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="autodiscovery.py",
        description="Discover the local environment for the portable workspace.",
    )
    parser.add_argument(
        "--no-secret-probe", action="store_true",
        help="skip the secret-store check (it writes, reads and deletes a random probe "
             "entry in the OS store)",
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
        return shutil.which(bash_name) is not None

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

    def check_secret_store() -> bool:
        """Check whether any native secret store is usable via tools/secret.py.

        Runs ``secret.py probe`` and reports True if at least one backend answers ok.
        Does not print secret values.
        """
        import subprocess
        import sys as _sys

        try:
            result = subprocess.run(
                [_sys.executable, str(SECRET_TOOL), "probe"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (subprocess.SubprocessError, OSError):
            return False
        return result.returncode == 0

    print("=== Portable workspace auto-discovery ===")
    print(f"OS:        {check_os()}")
    print(f"Processor: {check_processor()}")
    print(f"RAM:       {check_ram()}")
    print(f"Python:    {check_python()}  ({python_name}: {'yes' if python_path() else 'no'})")
    print(f"git:       {'yes' if git_path() else 'no'}  ({git_name})")
    print(f"bash:      {'yes' if bash_path() else 'no'}  ({bash_name})")
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
    else:
        print(f"secret store:        {'ok' if check_secret_store() else 'no usable store'}")

    db_exists, db_has_tables = check_inventory_db()
    print(f"data/inventory.db:   {'exists' if db_exists else 'MISSING'}")
    if db_exists and not db_has_tables:
        print("  -> database exists but has no tables (empty).")
        print(f"     Run: {PY_LAUNCHER} {INVENTORY_TOOL} init")
    elif not db_exists:
        print("  -> database missing.")
        print(f"     Run: {PY_LAUNCHER} {INVENTORY_TOOL} init")

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
