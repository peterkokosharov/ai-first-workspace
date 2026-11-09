#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Start opencode with the API keys from the OS secret store (standard library only).

For every provider in ``opencode_config.PROVIDERS`` (NVIDIA, Gemini, DeepSeek, Groq,
Mistral, OpenRouter) the launcher reads the key through ``tools/secret.py`` (Windows
Credential Manager, KWallet, GNOME Keyring, ...) and puts it into an environment
variable (``NVIDIA_API_KEY``, ``GEMINI_API_KEY``, ...) of the opencode child process
only. The key is never written to disk and never printed; your own shell does not
get the variables. A variable that is already set is left as it is. A provider without
a stored key is skipped (opencode's own free models need no key).

Works the same on Windows and Linux. All arguments are passed on to opencode. Ctrl+C
goes to opencode only; the launcher waits for it to finish.

Note: the keys are in opencode's environment, so every program opencode starts (shell
commands, tools of an agent) can read them too. An agent must never print environment
variables (``env``, ``set``, ``printenv``, ``echo $..._API_KEY``).

Windows: if only an npm shim ``opencode.cmd`` / ``.bat`` is found, cmd.exe re-parses
the arguments, so arguments with ``& | ^ % < > "`` are refused (use ``opencode.exe`` or
leave those characters out). A real ``opencode.exe`` next to the shim or on PATH is
preferred.

Usage:
    python3 tools/run_opencode.py                       # opencode TUI in this folder
    python3 tools/run_opencode.py run -m nvidia/<model> 'hi'
    python3 tools/run_opencode.py --only nvidia,gemini  # read only these keys
    py tools/run_opencode.py                            # Windows
"""

from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Callable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
import opencode_config  # noqa: E402  (shared helpers next to this file)

EXIT_NOT_FOUND = 127


def child_env(base: Mapping[str, str], providers: list[str],
              get_secret: Callable[[str], str] = opencode_config.get_secret,
              log=None) -> dict[str, str]:
    """Return a copy of ``base`` plus one key variable per provider with a stored key."""
    log = sys.stderr if log is None else log
    env = dict(base)
    for pid in providers:
        spec = opencode_config.PROVIDERS[pid]
        var = spec["env"]
        if env.get(var):
            print(f"run_opencode: {var} already set, kept", file=log)
            continue
        try:
            env[var] = get_secret(spec["key_path"])
        except opencode_config.ConfigError as exc:
            if exc.exit_code == 1:
                continue  # no key stored for this provider: fine
            print(f"run_opencode: {pid}: {exc}", file=log)
            continue
        print(f"run_opencode: {var} set from the OS secret store (value not shown)", file=log)
    return env


#: Characters cmd.exe interprets even inside quotes when it runs a .cmd/.bat file.
CMD_UNSAFE = set('&|^%<>"')


def is_batch(path: str) -> bool:
    """True for a Windows batch file (``.cmd`` / ``.bat``), which cmd.exe runs."""
    return Path(path).suffix.lower() in (".cmd", ".bat")


def find_opencode(which: Callable[[str], str | None] = shutil.which) -> str | None:
    """Path of the opencode program.

    On Windows ``which`` may return the npm shim ``opencode.cmd``; a real
    ``opencode.exe`` in the same folder or on PATH is preferred, because cmd.exe
    re-parses the arguments of a batch file.
    """
    found = which("opencode")
    if found and is_batch(found):
        sibling = Path(found).with_name("opencode.exe")
        if sibling.is_file():
            return str(sibling)
        exe = which("opencode.exe")
        if exe and not is_batch(exe):
            return exe
    return found


def unsafe_for_batch(args: list[str]) -> list[str]:
    """Arguments that cmd.exe would re-interpret when passed to a .cmd/.bat file."""
    return [a for a in args if CMD_UNSAFE.intersection(a)]


@contextlib.contextmanager
def sigint_to_child_only():
    """While the child runs, Ctrl+C does not stop the launcher; the child gets it.

    A no-op handler (not ``SIG_IGN``) is used: on POSIX an ignored signal stays ignored
    in the child after exec, a Python handler is reset to the default there.
    """
    try:
        previous = signal.signal(signal.SIGINT, lambda signum, frame: None)
    except ValueError:  # not in the main thread
        yield
        return
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


def parse_only(args: list[str]) -> tuple[list[str] | None, str | None]:
    """Take a leading ``--only X`` / ``--only=X`` off ``args`` (in place).

    Returns (providers or None when absent, error message or None).
    """
    if not args:
        return None, None
    first = args[0]
    if first == "--only":
        if len(args) < 2 or args[1].startswith("-"):
            return None, "--only needs a value, e.g. --only nvidia,gemini"
        args.pop(0)
        value = args.pop(0)
    elif first.startswith("--only="):
        value = args.pop(0)[len("--only="):]
    else:
        return None, None
    wanted = [p.strip() for p in value.split(",") if p.strip()]
    if not wanted:
        return None, "--only needs a value, e.g. --only nvidia,gemini"
    unknown = [p for p in wanted if p not in opencode_config.PROVIDERS]
    if unknown:
        return None, (f"unknown provider(s): {', '.join(unknown)}; known: "
                      f"{', '.join(sorted(opencode_config.PROVIDERS))}")
    return wanted, None


def main(argv: list[str] | None = None,
         run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
         which: Callable[[str], str | None] = shutil.which,
         get_secret: Callable[[str], str] = opencode_config.get_secret) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    wanted, error = parse_only(args)
    if error:
        print(f"run_opencode: {error}", file=sys.stderr)
        return 2
    providers = wanted or sorted(opencode_config.PROVIDERS)

    exe = find_opencode(which)
    if not exe:
        print("run_opencode: opencode not found on PATH. Install it from https://opencode.ai",
              file=sys.stderr)
        return EXIT_NOT_FOUND
    if is_batch(exe):
        bad = unsafe_for_batch(args)
        if bad:
            print(f"run_opencode: {exe} is a batch file; cmd.exe would re-interpret "
                  f"{len(bad)} argument(s) containing one of & | ^ % < > \". Leave those "
                  "characters out or install opencode.exe.", file=sys.stderr)
            return 2

    opencode_config.warn_plaintext_keys(opencode_config.config_file())
    env = child_env(os.environ, providers, get_secret)
    try:
        with sigint_to_child_only():
            return run([exe, *args], env=env).returncode
    except KeyboardInterrupt:
        return 130
    except OSError as exc:
        print(f"run_opencode: cannot start {exe}: {exc.strerror}", file=sys.stderr)
        return EXIT_NOT_FOUND


if __name__ == "__main__":
    raise SystemExit(main())
