#!/usr/bin/env bash
# =============================================================================
# build-deb.sh — Build / fetch .deb package for kikolib (stdlib keystore lib)
#
# kikolib is vendored in lib/kikolib/ (it comes from ~/kiko/packages/kikolib).
# It is NOT built from this repo directly — instead we copy the pre-built
# .deb from ~/kiko/packages/ if it exists.
#
# Usage:
#   cd deb/kikolib
#   ./build-deb.sh
#
# Produces: ../python3-kikolib_0.1.0-1_all.deb
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# --- Where to look for a pre-built kikolib deb ------------------------------

KIKO_PACKAGES_DIR="${HOME}/kiko/packages"
KIKO_DEB="${KIKO_PACKAGES_DIR}/python3-kikolib_0.1.0-1_all.deb"
DEB_DEST="${PROJECT_ROOT}/deb/kikolib/python3-kikolib_0.1.0-1_all.deb"

echo "=== kikolib .deb provider ==="
echo "Project root: ${PROJECT_ROOT}"
echo "Looking for pre-built kikolib deb at: ${KIKO_DEB}"
echo

# --- Main --------------------------------------------------------------------

if [[ -f "${KIKO_DEB}" ]]; then
    echo "✓ Found pre-built kikolib deb:"
    ls -lh "${KIKO_DEB}"
    echo
    echo "Copying to ${DEB_DEST} ..."
    cp "${KIKO_DEB}" "${DEB_DEST}"
    echo "✓ Copied: ${DEB_DEST}"
    echo
    echo "Install on target machine:"
    echo "  sudo dpkg -i ${DEB_DEST}"
    echo "  sudo apt-get install -f   # pull missing dependencies"
else
    echo "WARNING: No pre-built kikolib deb found at ${KIKO_DEB}"
    echo
    echo "To build kikolib deb manually from source:"
    echo "  cd ~/kiko/packages/kikolib/"
    echo "  ./create-kikolib-deb.sh"
    echo "  # then copy the resulting .deb here:"
    echo "  cp ~/kiko/packages/python3-kikolib_0.1.0-1_all.deb ${DEB_DEST}"
    echo
    echo "Leaving deb/kikolib/ empty (only build script present)."
    exit 0
fi