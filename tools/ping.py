#!/usr/bin/env python3
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
"""Ping a model via OpenCode and verify it against the inventory database.

Usage:
    python3 tools/ping.py <model_alias> [--message "hi"]

The script:
1. Looks up the model alias in data/inventory.db (models table).
2. Checks OpenCode's model catalog for the provider to determine the tier.
3. Pings the model via `opencode run -m <provider>/<model> --format json <message>`.
4. Reports OK if the model answers, NOT OK on HTTP error / non-200 / no response.

Standard library only: no venv, no pip.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INVENTORY_DB = DATA / "inventory.db"

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_ERROR = 2


class PingError(Exception):
    def __init__(self, message: str, exit_code: int = EXIT_ERROR):
        super().__init__(message)
        self.exit_code = exit_code


# -------------------------------------------------------------------------------------- db


def _connect() -> sqlite3.Connection:
    if not INVENTORY_DB.is_file():
        raise PingError(
            f"inventory database not found: {INVENTORY_DB}. "
            f"Run: python3 tools/inventory.py init",
            EXIT_NOT_FOUND,
        )
    conn = sqlite3.connect(str(INVENTORY_DB))
    conn.row_factory = sqlite3.Row
    return conn


def lookup_model(alias: str) -> dict | None:
    """Look up a model by alias in the inventory database."""
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT m.id, m.alias, m.model_id, m.provider_id, m.key_id,
                   m.status, m.notes,
                   p.name AS provider_name, p.kind AS provider_kind
            FROM models m
            JOIN providers p ON m.provider_id = p.id
            WHERE m.alias = ?
            """,
            (alias,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# -------------------------------------------------------------------------------------- opencode tier


def opencode_models_for_provider(provider_name: str) -> tuple[list[str], str | None]:
    """Return the list of models OpenCode knows for a provider, or an error."""
    try:
        result = subprocess.run(
            ["opencode", "models", provider_name],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        return [], "opencode not found on PATH"
    except subprocess.SubprocessError as exc:
        return [], f"opencode models failed: {exc}"

    if result.returncode != 0:
        return [], f"opencode models exited {result.returncode}: {result.stderr.strip()}"

    models = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return models, None


def check_tier(model_ref: str, provider_name: str) -> tuple[bool, str]:
    """Check whether ``model_ref`` is listed in OpenCode's catalog for the provider."""
    models, err = opencode_models_for_provider(provider_name)
    if err:
        return False, f"tier check skipped: {err}"
    if model_ref in models:
        return True, f"available in OpenCode catalog for {provider_name}"
    return False, f"{model_ref} not listed in OpenCode catalog for {provider_name}"


# -------------------------------------------------------------------------------------- ping


def ping_model(model_ref: str, message: str) -> tuple[int, str, str]:
    """Run ``opencode run -m <ref> --format json <message>``.

    Returns (exit_code, stdout, stderr).
    """
    try:
        result = subprocess.run(
            ["opencode", "run", "-m", model_ref, "--format", "json", message],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return EXIT_ERROR, "", "opencode run timed out"
    except FileNotFoundError:
        return EXIT_ERROR, "", "opencode not found on PATH"
    except subprocess.SubprocessError as exc:
        return EXIT_ERROR, "", f"opencode run failed: {exc}"


def parse_response(stdout: str) -> tuple[bool, str | None, str | None]:
    """Parse JSON-lines output from opencode run.

    Returns (got_text_response, response_text_or_none, error_message_or_none).
    """
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get("type") == "text":
            part = obj.get("part") or {}
            text = part.get("text")
            if text:
                return True, text, None
        if obj.get("type") == "error":
            err = obj.get("error") or {}
            msg = err.get("data", {}).get("message") or err.get("message") or str(err)
            return False, None, msg
    return False, None, None


# -------------------------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="ping.py",
        description="Ping a model via OpenCode and verify against inventory.",
    )
    parser.add_argument("model", help="model alias from data/inventory.db")
    parser.add_argument(
        "--message",
        default="hi",
        help="message to send to the model (default: hi)",
    )
    args = parser.parse_args(argv)

    # 1. Look up in inventory
    try:
        model = lookup_model(args.model)
    except PingError as exc:
        print(f"ping.py: {exc}")
        return exc.exit_code

    if not model:
        print(f"ping.py: model '{args.model}' not found in inventory")
        return EXIT_NOT_FOUND

    print(f"model : {model['alias']}")
    print(f"id    : {model['id']}")
    print(f"ref   : {model['model']}")
    print(f"provider: {model['provider_name']} ({model['provider_kind']})")
    print(f"status: {model['status']}")
    if model["notes"]:
        print(f"notes : {model['notes']}")

    # 2. OpenCode tier check
    model_for_tier = model["model"]
    model_for_run = model["model"]
    prefix = model["provider_name"] + "/"
    if not model_for_run.startswith(prefix):
        model_for_run = prefix + model_for_run
    tier_ok, tier_msg = check_tier(model_for_tier, model["provider_name"])
    print(f"tier  : {tier_msg}")
    if not tier_ok and "skipped" not in tier_msg:
        # Not fatal — the model might still be pingable directly
        print("      (continuing anyway)")

    # 3. Ping
    print(f"ping  : {model_for_run} -- {args.message!r}")
    rc, stdout, stderr = ping_model(model_for_run, args.message)

    if rc != 0:
        print(f"result: NOT OK (opencode run exited {rc})")
        if stderr.strip():
            print(f"      stderr: {stderr.strip()}")
        return EXIT_ERROR

    # 4. Parse response
    got_text, text, err_msg = parse_response(stdout)
    if got_text:
        print(f"response: {text}")
        print("result: OK")
        return EXIT_OK

    if err_msg:
        print(f"result: NOT OK (server error: {err_msg})")
    else:
        print("result: NOT OK (no text response from model)")
        if stdout.strip():
            print(f"      stdout: {stdout.strip()[:200]}")
    if stderr.strip():
        print(f"      stderr: {stderr.strip()[:200]}")
    return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
