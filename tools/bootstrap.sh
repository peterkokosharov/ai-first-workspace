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
#   1. Verifies we are inside the project root; turns on the secret-check git
#      hook (git config core.hooksPath .githooks) if this folder is a git repo
#   2. Initializes the inventory database (schema + seed)
#   3. Runs auto-discovery (OS, git, bash, Python, inventory db)
#   4. Reminds you to set up secrets (tools/secret.py setup)
#   5. Runs the full test suite
#   6. Prints the next step
#
# Requires: Python 3 (python3, python or the Windows py launcher), git, bash
# (Git Bash on Windows).
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

# Python: python3 on Linux; python or the py launcher on Windows (Git Bash).
PY=""
for candidate in python3 python "py -3"; do
    if $candidate -c "import sys; sys.exit(sys.version_info < (3, 10))" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done
if [[ -z "$PY" ]]; then
    echo "ERROR: Python 3.10+ not found (tried python3, python, py -3)."
    exit 1
fi

# Secret-check hook: only inside a git repo; setting the same value again is harmless.
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    if [[ "$(git config --get core.hooksPath || true)" != ".githooks" ]]; then
        git config core.hooksPath .githooks
        echo "[0/5] Secret check turned on (git config core.hooksPath .githooks)."
    else
        echo "[0/5] Secret check already on (core.hooksPath = .githooks)."
    fi
else
    echo "[0/5] Not a git repo: secret-check hook not turned on (no git, nothing to commit)."
fi
echo

echo "[1/5] Initializing inventory database..."
$PY tools/inventory.py init

echo
echo "[2/5] Running auto-discovery..."
$PY tools/autodiscovery.py

echo
echo "[3/5] Secret setup"
echo "  Run: $PY tools/secret.py setup"
echo "  Then: $PY tools/secret.py --backend auto set <key_path>"
echo "  Example: $PY tools/secret.py --backend auto set nvidia/personal/api_key"

echo
echo "[4/5] Running test suite..."
$PY -m unittest discover -s tools/tests -t . -v

echo
echo "[5/5] Next step:"
echo "  Start opencode (its free models need no key):"
echo "    opencode"
echo "  With your stored keys (NVIDIA etc.), after $PY tools/setup_nvidia.py:"
echo "    $PY tools/run_opencode.py"
echo "  Or test a model directly:"
echo "    $PY tools/ping_direct.py nvidia nemotron-ultra 'hi'"
echo
echo "Done. The workspace is ready."