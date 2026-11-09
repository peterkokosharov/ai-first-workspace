#!/usr/bin/env bash
# Copyright (c) 2026 Peter Kokosharov
# SPDX-License-Identifier: MIT
# Author: Peter Kokosharov <peter.kokosharov@gmail.com>
# =============================================================================
# bootstrap.sh — One-command quick start for a new machine.
#
# Usage:
#   cd /path/to/project
#   bash tools/bootstrap.sh
#
# What it does:
#   1. Verifies we are inside the project root
#   2. Initializes the inventory database (schema + seed)
#   3. Runs auto-discovery (OS, git, bash, Python, inventory db)
#   4. Reminds you to set up secrets (tools/secret.py setup)
#   5. Runs the full test suite
#   6. Prints the next step
#
# Requires: Python 3, git, bash
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "=== Bootstrap: Portable Workspace ==="
echo

# --- 1. Check we are in project root -----------------------------------------

if [[ ! -f "AGENTS.md" ]]; then
    echo "ERROR: AGENTS.md not found. Run this script from the project root."
    exit 1
fi

echo "[1/5] Initializing inventory database..."
python3 tools/inventory.py init

echo
echo "[2/5] Running auto-discovery..."
python3 tools/autodiscovery.py

echo
echo "[3/5] Secret setup"
echo "  Run: python3 tools/secret.py setup"
echo "  Then: python3 tools/secret.py --backend auto set <key_path>"
echo "  Example: python3 tools/secret.py --backend auto set nvidia/personal/api_key"

echo
echo "[4/5] Running test suite..."
python3 -m unittest discover -s tools/tests -t . -v

echo
echo "[5/5] Next step:"
echo "  Start an agent session, for example:"
echo "    opencode run -m nemotron-ultra --format json 'hi'"
echo "  Or test a model directly:"
echo "    python3 tools/ping_direct.py nvidia nemotron-ultra 'hi'"
echo
echo "Done. The workspace is ready."