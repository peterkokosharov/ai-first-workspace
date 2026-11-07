#!/usr/bin/env python3
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
INVENTORY_DB = DATA / "inventory.db"
SCHEMA = DATA / "schema.sql"
SEED = DATA / "seed.sql"
SECRET_TOOL = ROOT / "tools" / "secret.py"
INVENTORY_TOOL = ROOT / "tools" / "inventory.py"


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

            class MEMORYSTATUS(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("dwTotalPhys", ctypes.c_ulonglong),
                    ("dwAvailPhys", ctypes.c_ulonglong),
                    ("dwTotalPageFile", ctypes.c_ulonglong),
                    ("dwAvailPageFile", ctypes.c_ulonglong),
                    ("dwTotalVirtual", ctypes.c_ulonglong),
                    ("dwAvailVirtual", ctypes.c_ulonglong),
                    ("dwExtendedTotal", ctypes.c_ulonglong),
                    ("dwExtendedAvail", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUS()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            return mem.dwTotalPhys // (1024 * 1024)
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
    parser.parse_args(argv)

    print("=== Portable workspace auto-discovery ===")
    print(f"OS:        {check_os()}")
    print(f"Processor: {check_processor()}")
    print(f"RAM:       {check_ram()}")
    print(f"Python:    {check_python()}")
    print(f"git:       {'yes' if check_git() else 'no'}")
    print(f"bash:      {'yes' if check_bash() else 'no'}")

    missing_minimum = []
    if not check_git():
        missing_minimum.append("git")
    if not check_bash():
        missing_minimum.append("bash (Git Bash on Windows)")

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

    db_exists, db_has_tables = check_inventory_db()
    print(f"data/inventory.db:   {'exists' if db_exists else 'MISSING'}")
    if db_exists and not db_has_tables:
        print("  -> database exists but has no tables (empty).")
        print(f"     Run: python3 {INVENTORY_TOOL} init")
    elif not db_exists:
        print("  -> database missing.")
        print(f"     Run: python3 {INVENTORY_TOOL} init")

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
